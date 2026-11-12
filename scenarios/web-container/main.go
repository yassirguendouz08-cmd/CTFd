package main

import (
	"context"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/url"
	"strconv"
	"strings"
	"time"

	"github.com/ctfer-io/chall-manager/sdk"
	"github.com/pulumi/pulumi-docker/sdk/v4/go/docker"
	"github.com/pulumi/pulumi/sdk/v3/go/pulumi"
)

func instanceFlag(seed, identity string) (string, error) {
	key, err := hex.DecodeString(seed)
	if err != nil || len(key) < 32 || identity == "" {
		return "", fmt.Errorf("flag_seed must contain at least 32 random bytes as hex, and identity must be set")
	}
	mac := hmac.New(sha256.New, key)
	mac.Write([]byte(identity))
	return "CYBERDUNE{" + hex.EncodeToString(mac.Sum(nil))[:32] + "}", nil
}

func publishedPort(reader io.Reader, internal int) (int, error) {
	return publishedPortOn(reader, internal, "127.0.0.1")
}

func publishedPortOn(reader io.Reader, internal int, bind string) (int, error) {
	var inspection struct {
		NetworkSettings struct {
			Ports map[string][]struct {
				HostIp   string
				HostPort string
			}
		}
	}
	if err := json.NewDecoder(reader).Decode(&inspection); err != nil {
		return 0, err
	}
	for _, binding := range inspection.NetworkSettings.Ports[fmt.Sprintf("%d/tcp", internal)] {
		port, err := strconv.Atoi(binding.HostPort)
		if err == nil && port > 0 && port <= 65535 && binding.HostIp == bind {
			return port, nil
		}
	}
	return 0, fmt.Errorf("Docker did not publish the requested loopback port")
}

func inspectPublishedPort(id string, internal int, bind string) (int, error) {
	transport := &http.Transport{DialContext: func(ctx context.Context, _, _ string) (net.Conn, error) {
		return (&net.Dialer{}).DialContext(ctx, "unix", "/var/run/docker.sock")
	}}
	defer transport.CloseIdleConnections()
	client := &http.Client{Transport: transport, Timeout: 10 * time.Second}
	response, err := client.Get("http://docker/containers/" + url.PathEscape(id) + "/json")
	if err != nil {
		return 0, err
	}
	defer response.Body.Close()
	if response.StatusCode != http.StatusOK {
		return 0, fmt.Errorf("Docker inspection returned %d", response.StatusCode)
	}
	return publishedPortOn(io.LimitReader(response.Body, 1024*1024), internal, bind)
}

func publicBinding(host string) (string, error) {
	if host == "" {
		return "127.0.0.1", nil
	}
	if ip := net.ParseIP(host); ip != nil {
		if !ip.IsGlobalUnicast() || ip.IsLoopback() || ip.IsPrivate() || ip.IsLinkLocalUnicast() {
			return "", fmt.Errorf("public_host must be a reachable worker hostname or IP")
		}
	} else if !validPublicHostname(host) {
		return "", fmt.Errorf("public_host must contain a valid worker hostname, without scheme, path or port")
	}
	return "0.0.0.0", nil
}

func validPublicHostname(host string) bool {
	if len(host) > 253 || host == "localhost" || strings.HasSuffix(host, ".") {
		return false
	}
	labels := strings.Split(host, ".")
	if len(labels) < 2 {
		return false
	}
	for _, label := range labels {
		if len(label) == 0 || len(label) > 63 || label[0] == '-' || label[len(label)-1] == '-' {
			return false
		}
		for _, char := range label {
			if !((char >= 'a' && char <= 'z') || (char >= 'A' && char <= 'Z') ||
				(char >= '0' && char <= '9') || char == '-') {
				return false
			}
		}
	}
	return true
}

const defaultEdgeNetwork = "ctfd_instance_edge"

// edgeHostname returns the public HTTPS hostname for an instance. chall-manager
// identities are hex labels, so they are already DNS-safe.
func edgeHostname(identity, edgeHost string) (string, error) {
	if !validPublicHostname(edgeHost) {
		return "", fmt.Errorf("edge_host must be a valid public hostname without scheme, port or path")
	}
	if len(identity) == 0 || len(identity) > 63 || identity[0] == '-' || identity[len(identity)-1] == '-' {
		return "", fmt.Errorf("instance identity is not a valid DNS label")
	}
	for _, char := range identity {
		if !((char >= 'a' && char <= 'z') || (char >= '0' && char <= '9') || char == '-') {
			return "", fmt.Errorf("instance identity is not a valid DNS label")
		}
	}
	return identity + "." + edgeHost, nil
}

func validEdgeNetwork(name string) bool {
	if len(name) == 0 || len(name) > 128 {
		return false
	}
	for _, char := range name {
		if !((char >= 'a' && char <= 'z') || (char >= 'A' && char <= 'Z') ||
			(char >= '0' && char <= '9') || char == '-' || char == '_' || char == '.') {
			return false
		}
	}
	return true
}

// edgeRoutingLabels let the shared Traefik edge find this gateway without a
// published host port. TLS terminates at the host Nginx in front of Traefik.
func edgeRoutingLabels(hostname, network, identity string) map[string]string {
	name := "cyberdune-" + identity
	return map[string]string{
		"traefik.enable":                                              "true",
		"traefik.docker.network":                                      network,
		"traefik.http.routers." + name + ".rule":                      "Host(`" + hostname + "`)",
		"traefik.http.routers." + name + ".entrypoints":               "web",
		"traefik.http.routers." + name + ".service":                   name,
		"traefik.http.services." + name + ".loadbalancer.server.port": "8080",
	}
}

func dockerLabels(values map[string]string) docker.ContainerLabelArray {
	labels := docker.ContainerLabelArray{}
	for key, value := range values {
		labels = append(labels, docker.ContainerLabelArgs{Label: pulumi.String(key), Value: pulumi.String(value)})
	}
	return labels
}

func connectionInfo(host string, published int) string {
	if host != "" {
		return "http://" + net.JoinHostPort(host, strconv.Itoa(published)) + "/"
	}
	return fmt.Sprintf("Private test instance: http://127.0.0.1:%d/ on the VPS. Forward this port through SSH to open it on your computer.", published)
}

func inspectTargetAddress(id string) (string, error) {
	transport := &http.Transport{DialContext: func(ctx context.Context, _, _ string) (net.Conn, error) {
		return (&net.Dialer{}).DialContext(ctx, "unix", "/var/run/docker.sock")
	}}
	defer transport.CloseIdleConnections()
	client := &http.Client{Transport: transport, Timeout: 10 * time.Second}
	response, err := client.Get("http://docker/containers/" + url.PathEscape(id) + "/json")
	if err != nil {
		return "", err
	}
	defer response.Body.Close()
	if response.StatusCode != http.StatusOK {
		return "", fmt.Errorf("Docker inspection returned %d", response.StatusCode)
	}
	var inspection struct {
		NetworkSettings struct {
			Networks map[string]struct{ IPAddress string }
		}
	}
	if err := json.NewDecoder(io.LimitReader(response.Body, 1024*1024)).Decode(&inspection); err != nil {
		return "", err
	}
	for _, network := range inspection.NetworkSettings.Networks {
		if ip := net.ParseIP(network.IPAddress); ip != nil && ip.To4() != nil && ip.IsPrivate() {
			return ip.String(), nil
		}
	}
	return "", fmt.Errorf("target has no private network address")
}

func main() {
	sdk.Run(func(req *sdk.Request, resp *sdk.Response, opts ...pulumi.ResourceOption) error {
		image := req.Config.Additional["image"]
		if image == "" {
			return fmt.Errorf("Additional image is required")
		}
		publicHost := req.Config.Additional["public_host"]
		bind, err := publicBinding(publicHost)
		if err != nil {
			return err
		}
		edgeHost := strings.TrimSpace(req.Config.Additional["edge_host"])
		edgeNetwork := strings.TrimSpace(req.Config.Additional["edge_network"])
		if edgeNetwork == "" {
			edgeNetwork = defaultEdgeNetwork
		}
		var edgeName string
		if edgeHost != "" {
			if publicHost != "" {
				return fmt.Errorf("edge_host and public_host are mutually exclusive")
			}
			if !validEdgeNetwork(edgeNetwork) {
				return fmt.Errorf("edge_network is not a valid Docker network name")
			}
			edgeName, err = edgeHostname(req.Config.Identity, edgeHost)
			if err != nil {
				return err
			}
		}
		flag, err := instanceFlag(req.Config.Additional["flag_seed"], req.Config.Identity)
		if err != nil {
			return err
		}
		port := 8080
		if value := req.Config.Additional["port"]; value != "" {
			port, err = strconv.Atoi(value)
			if err != nil || port < 1 || port > 65535 {
				return fmt.Errorf("invalid internal port")
			}
		}
		hostPort := 0
		minPort, maxPort := 0, 0
		portStateFile := ""
		// chall-manager runs the program in preview when a challenge is created.
		// Reserving here would leak a pending lease for every challenge.
		if publicHost != "" && !req.Ctx.DryRun() {
			minPort, maxPort, err = configuredPortRange(req.Config.Additional)
			if err != nil {
				return err
			}
			portStateFile, err = configuredPortLedger(req.Config.Additional)
			if err != nil {
				return err
			}
			hostPort, err = reservePublicPort(portStateFile, req.Config.Identity, minPort, maxPort, nil, time.Now().UTC())
			if err != nil {
				return err
			}
		}
		// Only the gateway publishes a host port, so only it carries the port label.
		var identityLabels docker.ContainerLabelArray
		if publicHost != "" {
			identityLabels = docker.ContainerLabelArray{
				docker.ContainerLabelArgs{Label: pulumi.String(portIdentityLabel), Value: pulumi.String(req.Config.Identity)},
			}
		}
		// Targets have their own internal network, never the CTFd control network.
		network, err := docker.NewNetwork(req.Ctx, "target-network", &docker.NetworkArgs{
			Internal: pulumi.Bool(true),
		}, opts...)
		if err != nil {
			return err
		}
		container, err := docker.NewContainer(req.Ctx, "target", &docker.ContainerArgs{
			Image:        pulumi.String(image),
			Envs:         pulumi.StringArray{pulumi.String("FLAG=" + flag)},
			Memory:       pulumi.Int(128),
			MemorySwap:   pulumi.Int(128),
			CpuPeriod:    pulumi.Int(100000),
			CpuQuota:     pulumi.Int(50000),
			ReadOnly:     pulumi.Bool(true),
			Capabilities: &docker.ContainerCapabilitiesArgs{Drops: pulumi.StringArray{pulumi.String("ALL")}},
			SecurityOpts: pulumi.StringArray{pulumi.String("no-new-privileges:true")},
			Ulimits: docker.ContainerUlimitArray{docker.ContainerUlimitArgs{
				Name: pulumi.String("nproc"), Soft: pulumi.Int(64), Hard: pulumi.Int(64),
			}},
			Labels: identityLabels,
			NetworksAdvanced: docker.ContainerNetworksAdvancedArray{docker.ContainerNetworksAdvancedArgs{
				Name: network.Name,
			}},
			Rm: pulumi.Bool(true),
		}, opts...)
		if err != nil {
			return err
		}
		// Only the TCP gateway has an ingress network. The target keeps its internal network.
		gatewayNetworks := docker.ContainerNetworksAdvancedArray{
			docker.ContainerNetworksAdvancedArgs{Name: network.Name},
		}
		var gatewayLabels docker.ContainerLabelArray
		if edgeHost != "" {
			// Attach to the existing shared edge network; Traefik reads the labels.
			gatewayNetworks = append(gatewayNetworks, docker.ContainerNetworksAdvancedArgs{Name: pulumi.String(edgeNetwork)})
			gatewayLabels = dockerLabels(edgeRoutingLabels(edgeName, edgeNetwork, req.Config.Identity))
		} else {
			ingress, err := docker.NewNetwork(req.Ctx, "gateway-network", &docker.NetworkArgs{}, opts...)
			if err != nil {
				return err
			}
			gatewayNetworks = append(gatewayNetworks, docker.ContainerNetworksAdvancedArgs{Name: ingress.Name})
			gatewayLabels = identityLabels
		}
		address := container.ID().ApplyT(func(id pulumi.ID) (string, error) { return inspectTargetAddress(string(id)) }).(pulumi.StringOutput)
		// A host process can claim the reserved port after the allocator checked
		// it. Docker's bind error is the only reliable signal, so retry there
		// and never re-offer a port that just failed.
		failedPorts := map[int]bool{}
		var gateway *docker.Container
		startGateway := func(candidate int) error {
			resourceName := "gateway"
			labels := gatewayLabels
			if publicHost != "" {
				resourceName = "gateway-" + strconv.Itoa(candidate)
				labels = docker.ContainerLabelArray{
					docker.ContainerLabelArgs{Label: pulumi.String(portIdentityLabel), Value: pulumi.String(req.Config.Identity)},
					docker.ContainerLabelArgs{Label: pulumi.String(portNumberLabel), Value: pulumi.String(strconv.Itoa(candidate))},
				}
			}
			args := &docker.ContainerArgs{
				Image:   pulumi.String("cyberdune/instance-gateway:v1"),
				Command: pulumi.StringArray{pulumi.String("TCP-LISTEN:8080,fork,reuseaddr"), address.ApplyT(func(ip string) string { return fmt.Sprintf("TCP:%s:%d", ip, port) }).(pulumi.StringOutput)},
				Memory:  pulumi.Int(32), MemorySwap: pulumi.Int(32),
				CpuPeriod: pulumi.Int(100000), CpuQuota: pulumi.Int(25000),
				ReadOnly:     pulumi.Bool(true),
				Capabilities: &docker.ContainerCapabilitiesArgs{Drops: pulumi.StringArray{pulumi.String("ALL")}},
				SecurityOpts: pulumi.StringArray{pulumi.String("no-new-privileges:true")},
				// Ready means that the target accepts TCP connections, not just that Docker started.
				Healthcheck: &docker.ContainerHealthcheckArgs{
					Tests:    pulumi.StringArray{pulumi.String("CMD"), pulumi.String("socat"), pulumi.String("-u"), pulumi.String("OPEN:/dev/null"), address.ApplyT(func(ip string) string { return fmt.Sprintf("TCP:%s:%d,connect-timeout=1", ip, port) }).(pulumi.StringOutput)},
					Interval: pulumi.String("2s"), Timeout: pulumi.String("2s"), Retries: pulumi.Int(30), StartPeriod: pulumi.String("1s"),
				},
				Wait: pulumi.Bool(true), WaitTimeout: pulumi.Int(90),
				Sysctls:          pulumi.StringMap{"net.ipv4.ip_forward": pulumi.String("0")},
				Labels:           labels,
				NetworksAdvanced: gatewayNetworks,
				Rm:               pulumi.Bool(true),
			}
			// Edge mode routes through Traefik, so the gateway publishes no host port.
			if edgeHost == "" {
				args.Ports = docker.ContainerPortArray{docker.ContainerPortArgs{Internal: pulumi.Int(8080), External: pulumi.Int(candidate), Ip: pulumi.String(bind), Protocol: pulumi.String("tcp")}}
			}
			if publicHost != "" || edgeHost != "" {
				args.Name = pulumi.String(gatewayContainerName(req.Config.Identity))
			}
			created, err := docker.NewContainer(req.Ctx, resourceName, args, opts...)
			gateway = created
			return err
		}
		hostPort, err = reserveAndStart(hostPort, failedPorts, startGateway,
			func() (int, error) {
				return reservePublicPort(portStateFile, req.Config.Identity, minPort, maxPort, failedPorts, time.Now().UTC())
			},
			func(candidate int) error {
				return releaseFailedReservation(portStateFile, req.Config.Identity, candidate)
			},
		)
		if err != nil {
			return err
		}
		resp.Flags = pulumi.StringArray{pulumi.String(flag)}.ToStringArrayOutput()
		// Read the actual binding from Docker; provider Ports can retain input-only values.
		resp.ConnectionInfo = gateway.ID().ApplyT(func(id pulumi.ID) (string, error) {
			if edgeHost != "" {
				return "https://" + edgeName + "/", nil
			}
			published, err := inspectPublishedPort(string(id), 8080, bind)
			if err != nil {
				return "", err
			}
			if publicHost != "" {
				if published != hostPort {
					return "", fmt.Errorf("Docker published port %d instead of reserved port %d", published, hostPort)
				}
				if err := markPublicPortActive(portStateFile, req.Config.Identity, hostPort); err != nil {
					return "", err
				}
			}
			return connectionInfo(publicHost, published), nil
		}).(pulumi.StringOutput)
		return nil
	})
}
