//go:build linux

package main

import (
	"context"
	"crypto/sha256"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"syscall"
	"time"
)

const (
	portIdentityLabel = "com.cyberdune.instance.identity"
	portNumberLabel   = "com.cyberdune.instance.public-port"
	pendingPortTTL    = 30 * time.Minute
)

type portLease struct {
	Port      int       `json:"port"`
	Identity  string    `json:"identity"`
	State     string    `json:"state"`
	CreatedAt time.Time `json:"created_at"`
}

type portLedger struct {
	Version int                  `json:"version"`
	Leases  map[string]portLease `json:"leases"`
}

type dockerPortSnapshot struct {
	Labels map[string]string `json:"Labels"`
	Ports  []struct {
		PublicPort  int    `json:"PublicPort"`
		PrivatePort int    `json:"PrivatePort"`
		Type        string `json:"Type"`
	} `json:"Ports"`
}

func parsePortRange(minText, maxText string) (int, int, error) {
	min, errMin := strconv.Atoi(minText)
	max, errMax := strconv.Atoi(maxText)
	if errMin != nil || errMax != nil || min < 1024 || max > 65535 || min > max || max-min > 4095 {
		return 0, 0, errors.New("public challenge port range must be a valid inclusive range of at most 4096 ports")
	}
	return min, max, nil
}

func configuredPortRange(additional map[string]string) (int, int, error) {
	minText := additional["port_min"]
	if minText == "" {
		minText = os.Getenv("INSTANCE_PORT_MIN")
	}
	maxText := additional["port_max"]
	if maxText == "" {
		maxText = os.Getenv("INSTANCE_PORT_MAX")
	}
	if minText == "" || maxText == "" {
		return 0, 0, errors.New("INSTANCE_PORT_MIN and INSTANCE_PORT_MAX are required for public instances")
	}
	return parsePortRange(minText, maxText)
}

func configuredPortLedger(additional map[string]string) (string, error) {
	path := additional["port_state_file"]
	if path == "" {
		path = os.Getenv("INSTANCE_PORT_STATE_FILE")
	}
	if path == "" {
		path = "/var/lib/chall-manager/cyberdune-port-allocations.json"
	}
	if !filepath.IsAbs(path) || filepath.Clean(path) != path || strings.Contains(path, "..") {
		return "", errors.New("port_state_file must be a clean absolute path in persistent manager storage")
	}
	return path, nil
}

func dockerClient() *http.Client {
	transport := &http.Transport{DialContext: func(ctx context.Context, _, _ string) (net.Conn, error) {
		return (&net.Dialer{}).DialContext(ctx, "unix", "/var/run/docker.sock")
	}}
	return &http.Client{Transport: transport, Timeout: 10 * time.Second}
}

func listDockerContainers() ([]dockerPortSnapshot, error) {
	response, err := dockerClient().Get("http://docker/containers/json?all=1")
	if err != nil {
		return nil, err
	}
	defer response.Body.Close()
	if response.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("Docker container listing returned %d", response.StatusCode)
	}
	var containers []dockerPortSnapshot
	if err := json.NewDecoder(io.LimitReader(response.Body, 4*1024*1024)).Decode(&containers); err != nil {
		return nil, err
	}
	return containers, nil
}

func hostPortFree(port int) bool {
	listener, err := net.Listen("tcp", net.JoinHostPort("0.0.0.0", strconv.Itoa(port)))
	if err != nil {
		return false
	}
	_ = listener.Close()
	return true
}

func containerUsesPort(containers []dockerPortSnapshot, port int) bool {
	for _, container := range containers {
		for _, binding := range container.Ports {
			if binding.Type == "tcp" && binding.PublicPort == port {
				return true
			}
		}
	}
	return false
}

func containersForIdentity(containers []dockerPortSnapshot, identity string) bool {
	for _, container := range containers {
		if container.Labels[portIdentityLabel] == identity {
			return true
		}
	}
	return false
}

func withPortLedger(path string, run func(*portLedger) error) error {
	if err := os.MkdirAll(filepath.Dir(path), 0700); err != nil {
		return err
	}
	lock, err := os.OpenFile(path+".lock", os.O_CREATE|os.O_RDWR, 0600)
	if err != nil {
		return err
	}
	defer lock.Close()
	if err := syscall.Flock(int(lock.Fd()), syscall.LOCK_EX); err != nil {
		return err
	}
	defer syscall.Flock(int(lock.Fd()), syscall.LOCK_UN) //nolint:errcheck

	ledger := portLedger{Version: 1, Leases: map[string]portLease{}}
	data, err := os.ReadFile(path)
	if err != nil && !os.IsNotExist(err) {
		return err
	}
	if err == nil {
		if err := json.Unmarshal(data, &ledger); err != nil {
			return fmt.Errorf("decode public port ledger: %w", err)
		}
		if ledger.Version != 1 || ledger.Leases == nil {
			return errors.New("unsupported public port ledger format")
		}
	}
	if err := run(&ledger); err != nil {
		return err
	}
	data, err = json.Marshal(ledger)
	if err != nil {
		return err
	}
	temporary, err := os.CreateTemp(filepath.Dir(path), ".cyberdune-ports-*.tmp")
	if err != nil {
		return err
	}
	temporaryName := temporary.Name()
	defer os.Remove(temporaryName)
	if err := temporary.Chmod(0600); err != nil {
		_ = temporary.Close()
		return err
	}
	if _, err := temporary.Write(data); err != nil {
		_ = temporary.Close()
		return err
	}
	if err := temporary.Sync(); err != nil {
		_ = temporary.Close()
		return err
	}
	if err := temporary.Close(); err != nil {
		return err
	}
	if err := os.Rename(temporaryName, path); err != nil {
		return err
	}
	directory, err := os.Open(filepath.Dir(path))
	if err == nil {
		_ = directory.Sync()
		_ = directory.Close()
	}
	return nil
}

func reconcilePortLedger(ledger *portLedger, containers []dockerPortSnapshot, now time.Time, isPortFree func(int) bool) {
	for identity, lease := range ledger.Leases {
		if containersForIdentity(containers, identity) || containerUsesPort(containers, lease.Port) || !isPortFree(lease.Port) {
			continue
		}
		// A missing container plus a free host socket proves an active lease was
		// removed. Pending leases need a grace period for slow image pulls/startup.
		if lease.State == "active" || (lease.State == "pending" && now.Sub(lease.CreatedAt) >= pendingPortTTL) {
			delete(ledger.Leases, identity)
		}
	}
}

func availablePort(ledger *portLedger, containers []dockerPortSnapshot, min, max int, identity string, skip map[int]bool, isPortFree func(int) bool) (int, error) {
	if existing, ok := ledger.Leases[identity]; ok {
		if existing.Port < min || existing.Port > max {
			return 0, errors.New("existing instance reservation is outside the configured range")
		}
		if skip[existing.Port] {
			return 0, errors.New("existing instance reservation was reported unavailable")
		}
		return existing.Port, nil
	}
	used := map[int]bool{}
	for _, lease := range ledger.Leases {
		used[lease.Port] = true
	}
	start := min + int(sha256.Sum256([]byte(identity))[0])%((max-min)+1)
	for port := start; port <= max; port++ {
		if !used[port] && !skip[port] && !containerUsesPort(containers, port) && isPortFree(port) {
			return port, nil
		}
	}
	for port := min; port < start; port++ {
		if !used[port] && !skip[port] && !containerUsesPort(containers, port) && isPortFree(port) {
			return port, nil
		}
	}
	return 0, fmt.Errorf("no free host port in configured range %d-%d", min, max)
}

func reservePublicPort(path, identity string, min, max int, skip map[int]bool, now time.Time) (int, error) {
	if identity == "" {
		return 0, errors.New("instance identity is required for a public port reservation")
	}
	containers, err := listDockerContainers()
	if err != nil {
		return 0, fmt.Errorf("cannot safely inspect Docker port usage: %w", err)
	}
	port := 0
	err = withPortLedger(path, func(ledger *portLedger) error {
		reconcilePortLedger(ledger, containers, now, hostPortFree)
		selected, err := availablePort(ledger, containers, min, max, identity, skip, hostPortFree)
		if err != nil {
			return err
		}
		port = selected
		if _, exists := ledger.Leases[identity]; !exists {
			ledger.Leases[identity] = portLease{Port: selected, Identity: identity, State: "pending", CreatedAt: now}
		}
		return nil
	})
	return port, err
}

func markPublicPortActive(path, identity string, port int) error {
	return withPortLedger(path, func(ledger *portLedger) error {
		lease, ok := ledger.Leases[identity]
		if !ok || lease.Port != port {
			return errors.New("public port lease changed before container readiness")
		}
		lease.State = "active"
		ledger.Leases[identity] = lease
		return nil
	})
}

func deletePublicPortLease(path, identity string, port int, containers []dockerPortSnapshot, now time.Time, isPortFree func(int) bool) error {
	return withPortLedger(path, func(ledger *portLedger) error {
		lease, ok := ledger.Leases[identity]
		if !ok {
			return nil
		}
		if lease.Port != port {
			return errors.New("public port lease identity mismatch")
		}
		if containersForIdentity(containers, identity) || containerUsesPort(containers, port) || !isPortFree(port) {
			return errors.New("refusing to release a port while a container or host listener still owns it")
		}
		delete(ledger.Leases, identity)
		return nil
	})
}

const maxPortAttempts = 3

// gatewayContainerName is stable per instance so a failed start can be removed
// before its reservation is retried on another port.
func gatewayContainerName(identity string) string {
	sum := sha256.Sum256([]byte(identity))
	return fmt.Sprintf("cyberdune-%x-gateway", sum[:8])
}

// reserveAndStart starts the gateway on a reserved port and retries on another
// port only when Docker reports that the port itself could not be bound. The
// ledger only coordinates managers, so Docker's bind error is the authoritative
// signal that a host process or foreign container took the port.
func reserveAndStart(port int, skip map[int]bool, start func(int) error, reserve func() (int, error), release func(int) error) (int, error) {
	if skip == nil {
		skip = map[int]bool{}
	}
	for attempt := 1; ; attempt++ {
		err := start(port)
		if err == nil {
			return port, nil
		}
		if !isPortBindConflict(err, port) {
			return 0, err
		}
		skip[port] = true
		if releaseErr := release(port); releaseErr != nil {
			return 0, fmt.Errorf("port %d could not be bound and its reservation is kept: %w", port, releaseErr)
		}
		if attempt >= maxPortAttempts {
			return 0, fmt.Errorf("could not bind a public port after %d attempts: %w", maxPortAttempts, err)
		}
		next, reserveErr := reserve()
		if reserveErr != nil {
			return 0, reserveErr
		}
		port = next
	}
}

func isPortBindConflict(err error, port int) bool {
	if err == nil {
		return false
	}
	message := strings.ToLower(err.Error())
	if !strings.Contains(message, "port is already allocated") && !strings.Contains(message, "address already in use") {
		return false
	}
	return mentionsPort(message, port)
}

// mentionsPort avoids matching a shorter port inside a longer one, e.g. :2000
// in ":20003 failed: port is already allocated".
func mentionsPort(message string, port int) bool {
	needle := ":" + strconv.Itoa(port)
	for offset := 0; offset < len(message); {
		index := strings.Index(message[offset:], needle)
		if index < 0 {
			return false
		}
		end := offset + index + len(needle)
		if end == len(message) || message[end] < '0' || message[end] > '9' {
			return true
		}
		offset = end
	}
	return false
}

func removeContainer(name string) error {
	request, err := http.NewRequest(http.MethodDelete, "http://docker/containers/"+url.PathEscape(name)+"?force=1", nil)
	if err != nil {
		return err
	}
	response, err := dockerClient().Do(request)
	if err != nil {
		return err
	}
	defer response.Body.Close()
	if response.StatusCode == http.StatusNotFound {
		return nil
	}
	if response.StatusCode != http.StatusNoContent && response.StatusCode != http.StatusOK {
		return fmt.Errorf("Docker container removal returned %d", response.StatusCode)
	}
	return nil
}

// releaseFailedReservation drops a reservation only after Docker confirms that
// the failed gateway container is gone. The port may still be used by another
// process or container, which is exactly why the caller retries elsewhere.
func releaseFailedReservation(path, identity string, port int) error {
	if err := removeContainer(gatewayContainerName(identity)); err != nil {
		return fmt.Errorf("cannot remove the failed gateway container: %w", err)
	}
	containers, err := listDockerContainers()
	if err != nil {
		return fmt.Errorf("cannot verify gateway removal: %w", err)
	}
	return withPortLedger(path, func(ledger *portLedger) error {
		lease, ok := ledger.Leases[identity]
		if !ok || lease.Port != port {
			return errors.New("public port lease changed while recovering from a bind conflict")
		}
		for _, container := range containers {
			if container.Labels[portIdentityLabel] == identity && container.Labels[portNumberLabel] == strconv.Itoa(port) {
				return errors.New("refusing to release a port still labelled for this instance")
			}
		}
		delete(ledger.Leases, identity)
		return nil
	})
}
