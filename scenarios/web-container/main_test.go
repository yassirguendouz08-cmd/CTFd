package main

import (
	"errors"
	"fmt"
	"os"
	"strings"
	"sync"
	"testing"
	"time"
)

type dockerPortBinding = struct {
	PublicPort  int    `json:"PublicPort"`
	PrivatePort int    `json:"PrivatePort"`
	Type        string `json:"Type"`
}

func containerSnapshot(identity string, ports ...int) dockerPortSnapshot {
	snapshot := dockerPortSnapshot{}
	if identity != "" {
		snapshot.Labels = map[string]string{portIdentityLabel: identity}
	}
	for _, port := range ports {
		snapshot.Ports = append(snapshot.Ports, dockerPortBinding{PublicPort: port, Type: "tcp"})
	}
	return snapshot
}

func TestAccountFlags(t *testing.T) {
	seed := strings.Repeat("ab", 32)
	first, err := instanceFlag(seed, "account-1")
	if err != nil {
		t.Fatal(err)
	}
	again, _ := instanceFlag(seed, "account-1")
	other, _ := instanceFlag(seed, "account-2")
	changedSeed, _ := instanceFlag(strings.Repeat("cd", 32), "account-1")
	if first != again || first == other || first == changedSeed {
		t.Fatal("incorrect flag isolation")
	}
	for _, seed := range []string{"", "abc", strings.Repeat("00", 8)} {
		if _, err := instanceFlag(seed, "account-1"); err == nil {
			t.Fatal("weak or invalid seed accepted")
		}
	}
	if _, err := instanceFlag(seed, ""); err == nil {
		t.Fatal("empty identity accepted")
	}
}

func TestPublishedPort(t *testing.T) {
	port, err := publishedPort(strings.NewReader(`{"NetworkSettings":{"Ports":{"8080/tcp":[{"HostIp":"127.0.0.1","HostPort":"32771"}]}}}`), 8080)
	if err != nil || port != 32771 {
		t.Fatal("cannot read the allocated host port", port, err)
	}
	for _, body := range []string{`{}`, `{"NetworkSettings":{"Ports":{"8080/tcp":[{"HostIp":"0.0.0.0","HostPort":"32771"}]}}}`, `{"NetworkSettings":{"Ports":{"8080/tcp":[{"HostIp":"127.0.0.1","HostPort":"0"}]}}}`} {
		if _, err := publishedPort(strings.NewReader(body), 8080); err == nil {
			t.Fatal("invalid binding accepted")
		}
	}
}

func TestPublicRoutingIsExplicit(t *testing.T) {
	if bind, err := publicBinding(""); err != nil || bind != "127.0.0.1" {
		t.Fatal("private launch must remain the default", bind, err)
	}
	for _, host := range []string{"targets.example.test", "192.0.2.10", "2001:db8::10"} {
		if bind, err := publicBinding(host); err != nil || bind != "0.0.0.0" {
			t.Fatal("valid explicit worker host rejected", host, err)
		}
	}
	for _, host := range []string{"localhost", "127.0.0.1", "0.0.0.0", "10.0.0.1", "192.168.1.1", "169.254.1.1", "fc00::1", "https://example.test", "user@example.test", "example.test/path", "example.test:80", "bad..example.test", "-bad.example.test", "bad-.example.test", "bad_name.example.test"} {
		if _, err := publicBinding(host); err == nil {
			t.Fatal("invalid public host accepted", host)
		}
	}
	if connectionInfo("targets.example.test", 32771) != "http://targets.example.test:32771/" {
		t.Fatal("incorrect player endpoint")
	}
	if connectionInfo("2001:db8::10", 32771) != "http://[2001:db8::10]:32771/" {
		t.Fatal("incorrect IPv6 endpoint")
	}
	if _, err := publishedPortOn(strings.NewReader(`{"NetworkSettings":{"Ports":{"8080/tcp":[{"HostIp":"0.0.0.0","HostPort":"32771"}]}}}`), 8080, "0.0.0.0"); err != nil {
		t.Fatal("public gateway binding rejected", err)
	}
}

func TestPortRangeValidation(t *testing.T) {
	for _, test := range []struct {
		min, max string
		valid    bool
	}{{"20000", "20127", true}, {"1024", "65535", false}, {"20127", "20000", false}, {"abc", "20127", false}, {"20000", "24096", false}} {
		_, _, err := parsePortRange(test.min, test.max)
		if (err == nil) != test.valid {
			t.Fatalf("unexpected range validation for %s-%s: %v", test.min, test.max, err)
		}
	}
}

func TestConcurrentPortReservationsAreUniqueAndPersistent(t *testing.T) {
	path := t.TempDir() + "/ports.json"
	const count = 64
	ports := make(chan int, count)
	errors := make(chan error, count)
	var workers sync.WaitGroup
	for i := 0; i < count; i++ {
		workers.Add(1)
		go func(i int) {
			defer workers.Done()
			identity := fmt.Sprintf("identity-%d", i)
			selected := 0
			err := withPortLedger(path, func(ledger *portLedger) error {
				if ledger.Leases == nil {
					ledger.Leases = map[string]portLease{}
				}
				port, err := availablePort(ledger, nil, 20000, 20063, identity, nil, func(int) bool { return true })
				if err != nil {
					return err
				}
				selected = port
				ledger.Leases[identity] = portLease{Port: port, Identity: identity, State: "pending", CreatedAt: time.Now()}
				return nil
			})
			if err != nil {
				errors <- err
				return
			}
			ports <- selected
		}(i)
	}
	workers.Wait()
	close(ports)
	close(errors)
	for err := range errors {
		t.Fatal(err)
	}
	seen := map[int]bool{}
	for port := range ports {
		if seen[port] {
			t.Fatalf("duplicate active port reservation %d", port)
		}
		seen[port] = true
	}
	if len(seen) != count {
		t.Fatalf("reserved %d ports, want %d", len(seen), count)
	}
	if err := withPortLedger(path, func(ledger *portLedger) error {
		if len(ledger.Leases) != count {
			return fmt.Errorf("restart lost reservations: got %d", len(ledger.Leases))
		}
		return nil
	}); err != nil {
		t.Fatal(err)
	}
}

func TestPortCollisionRetriesWithinRangeAndExhaustion(t *testing.T) {
	ledger := &portLedger{Version: 1, Leases: map[string]portLease{"other": {Identity: "other", Port: 20000, State: "active"}}}
	containers := []dockerPortSnapshot{{Ports: []struct {
		PublicPort  int    `json:"PublicPort"`
		PrivatePort int    `json:"PrivatePort"`
		Type        string `json:"Type"`
	}{{PublicPort: 20001, Type: "tcp"}}}}
	port, err := availablePort(ledger, containers, 20000, 20003, "new", nil, func(candidate int) bool { return candidate == 20003 })
	if err != nil || port != 20003 {
		t.Fatalf("allocator did not retry occupied ports, got port=%d err=%v", port, err)
	}
	if _, err := availablePort(ledger, containers, 20000, 20001, "exhausted", nil, func(int) bool { return false }); err == nil {
		t.Fatal("allocator should fail closed on exhausted range")
	}
}

func TestCleanupWaitsForConfirmedContainerRemoval(t *testing.T) {
	path := t.TempDir() + "/ports.json"
	identity := "manager-identity"
	if err := withPortLedger(path, func(ledger *portLedger) error {
		ledger.Leases[identity] = portLease{Port: 20000, Identity: identity, State: "active", CreatedAt: time.Now()}
		return nil
	}); err != nil {
		t.Fatal(err)
	}
	running := []dockerPortSnapshot{{Labels: map[string]string{portIdentityLabel: identity}, Ports: []struct {
		PublicPort  int    `json:"PublicPort"`
		PrivatePort int    `json:"PrivatePort"`
		Type        string `json:"Type"`
	}{{PublicPort: 20000, Type: "tcp"}}}}
	if err := deletePublicPortLease(path, identity, 20000, running, time.Now(), func(int) bool { return false }); err == nil {
		t.Fatal("must not release a port while its container is present")
	}
	if err := deletePublicPortLease(path, identity, 20000, nil, time.Now(), func(int) bool { return true }); err != nil {
		t.Fatal(err)
	}
	if err := withPortLedger(path, func(ledger *portLedger) error {
		if _, ok := ledger.Leases[identity]; ok {
			return fmt.Errorf("confirmed removal did not release reservation")
		}
		return nil
	}); err != nil {
		t.Fatal(err)
	}
}

func TestJanitorAndAbandonedReservationRecovery(t *testing.T) {
	now := time.Now()
	identity := "expired-instance"
	ledger := &portLedger{Version: 1, Leases: map[string]portLease{
		identity:  {Identity: identity, Port: 20000, State: "active", CreatedAt: now.Add(-time.Hour)},
		"pending": {Identity: "pending", Port: 20001, State: "pending", CreatedAt: now},
	}}
	active := []dockerPortSnapshot{{Labels: map[string]string{portIdentityLabel: identity}, Ports: []struct {
		PublicPort  int    `json:"PublicPort"`
		PrivatePort int    `json:"PrivatePort"`
		Type        string `json:"Type"`
	}{{PublicPort: 20000, Type: "tcp"}}}}
	reconcilePortLedger(ledger, active, now, func(int) bool { return false })
	if _, ok := ledger.Leases[identity]; !ok {
		t.Fatal("active container lease was incorrectly released")
	}
	if _, ok := ledger.Leases["pending"]; !ok {
		t.Fatal("pending start was released before its grace period")
	}
	reconcilePortLedger(ledger, nil, now.Add(time.Second), func(int) bool { return true })
	if _, ok := ledger.Leases[identity]; ok {
		t.Fatal("removed instance reservation was not recovered")
	}
	reconcilePortLedger(ledger, nil, now.Add(pendingPortTTL+time.Second), func(int) bool { return true })
	if _, ok := ledger.Leases["pending"]; ok {
		t.Fatal("abandoned pending reservation was not recovered")
	}
}

func TestPortAllocationBoundaries(t *testing.T) {
	ledger := &portLedger{Version: 1, Leases: map[string]portLease{}}
	for _, test := range []struct {
		name string
		free int
		want int
	}{
		{"last port", 20002, 20002},
		{"first port", 20000, 20000},
	} {
		t.Run(test.name, func(t *testing.T) {
			port, err := availablePort(ledger, nil, 20000, 20002, "new", nil, func(candidate int) bool { return candidate == test.free })
			if err != nil || port != test.want {
				t.Fatalf("got port=%d err=%v, want %d", port, err, test.want)
			}
		})
	}
	port, err := availablePort(ledger, nil, 20000, 20000, "new", nil, func(int) bool { return true })
	if err != nil || port != 20000 {
		t.Fatalf("single-port range not allocated: port=%d err=%v", port, err)
	}
	ledger.Leases["held"] = portLease{Port: 20001, Identity: "held", State: "active"}
	port, err = availablePort(ledger, nil, 20000, 20002, "held", nil, func(int) bool { return false })
	if err != nil || port != 20001 {
		t.Fatalf("existing reservation not reused: port=%d err=%v", port, err)
	}
	ledger.Leases["held"] = portLease{Port: 30000, Identity: "held", State: "active"}
	if _, err := availablePort(ledger, nil, 20000, 20002, "held", nil, func(int) bool { return true }); err == nil {
		t.Fatal("reservation outside the configured range was reused")
	}
}

func TestReservationInputValidation(t *testing.T) {
	if _, err := reservePublicPort(t.TempDir()+"/ports.json", "", 20000, 20001, nil, time.Now()); err == nil {
		t.Fatal("empty identity reserved a public port")
	}
	for _, test := range []struct{ min, max string }{
		{"1023", "20000"}, {"20000", "65536"}, {"20000", "20001.5"},
		{"20000", "24096"},
	} {
		if _, _, err := parsePortRange(test.min, test.max); err == nil {
			t.Fatalf("invalid range %s-%s accepted", test.min, test.max)
		}
	}
}

func TestLedgerCorruptionFailsClosedAndStaysIntact(t *testing.T) {
	path := t.TempDir() + "/ports.json"
	if err := os.WriteFile(path, []byte("{not json"), 0600); err != nil {
		t.Fatal(err)
	}
	if err := withPortLedger(path, func(*portLedger) error { return nil }); err == nil {
		t.Fatal("corrupt ledger was accepted")
	}
	data, err := os.ReadFile(path)
	if err != nil || string(data) != "{not json" {
		t.Fatalf("corrupt ledger was overwritten: %q %v", data, err)
	}
	clean := t.TempDir() + "/ports.json"
	if err := withPortLedger(clean, func(*portLedger) error { return errors.New("boom") }); err == nil {
		t.Fatal("failed ledger update reported success")
	}
	if _, err := os.Stat(clean); !os.IsNotExist(err) {
		t.Fatal("failed ledger update published a partial file")
	}
}

func TestLeaseIdentityMismatchIsRejected(t *testing.T) {
	path := t.TempDir() + "/ports.json"
	if err := withPortLedger(path, func(ledger *portLedger) error {
		ledger.Leases["id"] = portLease{Port: 20000, Identity: "id", State: "pending"}
		return nil
	}); err != nil {
		t.Fatal(err)
	}
	if err := markPublicPortActive(path, "id", 20001); err == nil {
		t.Fatal("activated a lease for the wrong port")
	}
	if err := deletePublicPortLease(path, "id", 20001, nil, time.Now(), func(int) bool { return true }); err == nil {
		t.Fatal("deleted a lease for the wrong port")
	}
	if err := deletePublicPortLease(path, "missing", 20000, nil, time.Now(), func(int) bool { return true }); err != nil {
		t.Fatal("cleanup of an absent lease must be idempotent:", err)
	}
	if err := deletePublicPortLease(path, "id", 20000, nil, time.Now(), func(int) bool { return true }); err != nil {
		t.Fatal(err)
	}
	if err := deletePublicPortLease(path, "id", 20000, nil, time.Now(), func(int) bool { return true }); err != nil {
		t.Fatal("repeated cleanup must be idempotent:", err)
	}
}

func TestReconcileNeverReleasesAnotherInstancesPort(t *testing.T) {
	now := time.Now()
	ledger := &portLedger{Version: 1, Leases: map[string]portLease{
		"gone": {Port: 20000, Identity: "gone", State: "active", CreatedAt: now.Add(-time.Hour)},
	}}
	foreign := containerSnapshot("foreign", 20000)
	reconcilePortLedger(ledger, []dockerPortSnapshot{foreign}, now, func(int) bool { return true })
	if _, ok := ledger.Leases["gone"]; !ok {
		t.Fatal("released a lease whose port is published by another container")
	}
	if port, err := availablePort(ledger, []dockerPortSnapshot{foreign}, 20000, 20000, "new", nil, func(int) bool { return true }); err == nil {
		t.Fatalf("handed out a port published by another container: %d", port)
	}
}

func TestMalformedContainerMetadataIsIgnored(t *testing.T) {
	if containerUsesPort([]dockerPortSnapshot{{Ports: []dockerPortBinding{{PublicPort: 20000, Type: "udp"}}}}, 20000) {
		t.Fatal("a UDP binding was treated as the TCP host port")
	}
	if containerUsesPort([]dockerPortSnapshot{{Ports: []dockerPortBinding{{PublicPort: 0, Type: "tcp"}}}}, 20000) {
		t.Fatal("an unpublished port was treated as a host binding")
	}
	if containersForIdentity([]dockerPortSnapshot{{Labels: map[string]string{portIdentityLabel: ""}}}, "id") {
		t.Fatal("an empty identity label matched an instance")
	}
}

func TestBindConflictDetection(t *testing.T) {
	cases := []struct {
		message string
		port    int
		want    bool
	}{
		{"Error response from daemon: driver failed programming external connectivity on endpoint gateway: Bind for 0.0.0.0:20003 failed: port is already allocated", 20003, true},
		{"failed to bind host port for 0.0.0.0:20003:172.18.0.2:8080/tcp: address already in use", 20003, true},
		{"Bind for 0.0.0.0:20004 failed: port is already allocated", 20003, false},
		{"Bind for 0.0.0.0:20003 failed: port is already allocated", 2000, false},
		{"Bind for 0.0.0.0:2000 failed: port is already allocated", 2000, true},
		{"failed to bind host port for 0.0.0.0:2000/tcp: address already in use", 2000, true},
		{"container failed to become healthy: timeout", 20003, false},
		{"pull access denied for cyberdune/instance-gateway", 20003, false},
	}
	for _, test := range cases {
		if got := isPortBindConflict(errors.New(test.message), test.port); got != test.want {
			t.Fatalf("bind conflict detection for %q returned %v, want %v", test.message, got, test.want)
		}
	}
	if isPortBindConflict(nil, 20003) {
		t.Fatal("nil error classified as a bind conflict")
	}
}

func TestBindConflictRetriesOnAnotherPort(t *testing.T) {
	available := []int{20001, 20002}
	skip := map[int]bool{}
	var started, released []int
	port, err := reserveAndStart(20000, skip,
		func(candidate int) error {
			started = append(started, candidate)
			if candidate != 20002 {
				return fmt.Errorf("Bind for 0.0.0.0:%d failed: port is already allocated", candidate)
			}
			return nil
		},
		func() (int, error) {
			if !skip[20000] || (len(started) > 1 && !skip[20001]) {
				t.Fatalf("a failed port was re-offered: skip=%v started=%v", skip, started)
			}
			next := available[0]
			available = available[1:]
			return next, nil
		},
		func(candidate int) error {
			released = append(released, candidate)
			return nil
		},
	)
	if err != nil || port != 20002 {
		t.Fatalf("retry did not reach a free port: port=%d err=%v", port, err)
	}
	if fmt.Sprint(started) != "[20000 20001 20002]" || fmt.Sprint(released) != "[20000 20001]" {
		t.Fatalf("unexpected retry sequence: started=%v released=%v", started, released)
	}
}

func TestBindConflictRetryLimitsAndFailures(t *testing.T) {
	conflict := func(candidate int) error {
		return fmt.Errorf("Bind for 0.0.0.0:%d failed: port is already allocated", candidate)
	}
	var started, released int
	_, err := reserveAndStart(20000, map[int]bool{}, func(candidate int) error { started++; return conflict(candidate) },
		func() (int, error) { return 20000 + started, nil },
		func(int) error { released++; return nil },
	)
	if err == nil || started != maxPortAttempts || released != maxPortAttempts {
		t.Fatalf("retry limit not enforced: err=%v started=%d released=%d", err, started, released)
	}

	started, released = 0, 0
	_, err = reserveAndStart(20000, map[int]bool{}, func(int) error { started++; return errors.New("image pull failed") },
		func() (int, error) { t.Fatal("non-bind error must not reallocate"); return 0, nil },
		func(int) error { released++; return nil },
	)
	if err == nil || started != 1 || released != 0 {
		t.Fatalf("non-bind error retried: err=%v started=%d released=%d", err, started, released)
	}

	_, err = reserveAndStart(20000, map[int]bool{}, conflict,
		func() (int, error) { t.Fatal("reservation must be kept when it cannot be released"); return 0, nil },
		func(int) error { return errors.New("container still present") },
	)
	if err == nil || !strings.Contains(err.Error(), "reservation is kept") {
		t.Fatalf("unsafe release was not reported: %v", err)
	}

	_, err = reserveAndStart(20000, map[int]bool{}, conflict,
		func() (int, error) { return 0, errors.New("range exhausted") },
		func(int) error { return nil },
	)
	if err == nil || !strings.Contains(err.Error(), "range exhausted") {
		t.Fatalf("reallocation failure was not propagated: %v", err)
	}
}

func TestGatewayContainerNameIsStable(t *testing.T) {
	name := gatewayContainerName("identity-a")
	if name != gatewayContainerName("identity-a") || name == gatewayContainerName("identity-b") {
		t.Fatal("gateway container name is not stable per instance")
	}
	if len(name) > 63 || strings.ContainsAny(name, "_/ ") {
		t.Fatalf("gateway container name is not a safe Docker name: %q", name)
	}
}

func TestFailedPortIsNotReoffered(t *testing.T) {
	ledger := &portLedger{Version: 1, Leases: map[string]portLease{}}
	skip := map[int]bool{}
	port, err := availablePort(ledger, nil, 20000, 20002, "id", skip, func(int) bool { return true })
	if err != nil {
		t.Fatal(err)
	}
	skip[port] = true
	next, err := availablePort(ledger, nil, 20000, 20002, "id", skip, func(int) bool { return true })
	if err != nil || next == port {
		t.Fatalf("failed port was re-offered: %d -> %d (%v)", port, next, err)
	}
	skip[next] = true
	for candidate := 20000; candidate <= 20002; candidate++ {
		skip[candidate] = true
	}
	if _, err := availablePort(ledger, nil, 20000, 20002, "id", skip, func(int) bool { return true }); err == nil {
		t.Fatal("exhausted range after exclusions was reused")
	}
}
