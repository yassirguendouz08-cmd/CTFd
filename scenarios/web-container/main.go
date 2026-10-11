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
		if err == nil && port > 0 && port <= 65535 && binding.HostIp == "127.0.0.1" {
			return port, nil
		}
	}
	return 0, fmt.Errorf("Docker did not publish the requested loopback port")
}

func inspectPublishedPort(id string, internal int) (int, error) {
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
	return publishedPort(io.LimitReader(response.Body, 1024*1024), internal)
}

func inspectTargetAddress(id string) (string, error) {
	transport := &http.Transport{DialContext: func(ctx context.Context, _, _ string) (net.Conn, error) {
		return (&net.Dialer{}).DialContext(ctx, "unix", "/var/run/docker.sock")
	}}
	defer transport.CloseIdleConnections()
	client := &http.Client{Transport: transport, Timeout: 10 * time.Second}
	response, err := client.Get("http://docker/containers/" + url.PathEscape(id) + "/json")
	if err != nil { return "", err }
	defer response.Body.Close()
	if response.StatusCode != http.StatusOK { return "", fmt.Errorf("Docker inspection returned %d", response.StatusCode) }
	var inspection struct { NetworkSettings struct { Networks map[string]struct { IPAddress string } } }
	if err := json.NewDecoder(io.LimitReader(response.Body, 1024*1024)).Decode(&inspection); err != nil { return "", err }
	for _, network := range inspection.NetworkSettings.Networks {
		if ip := net.ParseIP(network.IPAddress); ip != nil && ip.To4() != nil && ip.IsPrivate() { return ip.String(), nil }
	}
	return "", fmt.Errorf("target has no private network address")
}

func main() {
	sdk.Run(func(req *sdk.Request, resp *sdk.Response, opts ...pulumi.ResourceOption) error {
		image := req.Config.Additional["image"]
		if image == "" {
			return fmt.Errorf("Additional image is required")
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
			NetworksAdvanced: docker.ContainerNetworksAdvancedArray{docker.ContainerNetworksAdvancedArgs{
				Name: network.Name,
			}},
			Rm: pulumi.Bool(true),
		}, opts...)
		if err != nil {
			return err
		}
		// Only the TCP gateway has an ingress network. The target keeps its internal network.
		ingress, err := docker.NewNetwork(req.Ctx, "gateway-network", &docker.NetworkArgs{}, opts...)
		if err != nil { return err }
		address := container.ID().ApplyT(func(id pulumi.ID) (string, error) { return inspectTargetAddress(string(id)) }).(pulumi.StringOutput)
		gateway, err := docker.NewContainer(req.Ctx, "gateway", &docker.ContainerArgs{
			Image: pulumi.String("cyberdune/instance-gateway:v1"),
			Command: pulumi.StringArray{pulumi.String("TCP-LISTEN:8080,fork,reuseaddr"), address.ApplyT(func(ip string) string { return fmt.Sprintf("TCP:%s:%d", ip, port) }).(pulumi.StringOutput)},
			Memory: pulumi.Int(32), MemorySwap: pulumi.Int(32),
			CpuPeriod: pulumi.Int(100000), CpuQuota: pulumi.Int(25000),
			ReadOnly: pulumi.Bool(true),
			Capabilities: &docker.ContainerCapabilitiesArgs{Drops: pulumi.StringArray{pulumi.String("ALL")}},
			SecurityOpts: pulumi.StringArray{pulumi.String("no-new-privileges:true")},
			Sysctls: pulumi.StringMap{"net.ipv4.ip_forward": pulumi.String("0")},
			NetworksAdvanced: docker.ContainerNetworksAdvancedArray{
				docker.ContainerNetworksAdvancedArgs{Name: network.Name},
				docker.ContainerNetworksAdvancedArgs{Name: ingress.Name},
			},
			Ports: docker.ContainerPortArray{docker.ContainerPortArgs{Internal: pulumi.Int(8080), External: pulumi.Int(0), Ip: pulumi.String("127.0.0.1"), Protocol: pulumi.String("tcp")}},
			Rm: pulumi.Bool(true),
		}, opts...)
		if err != nil { return err }
		resp.Flags = pulumi.StringArray{pulumi.String(flag)}.ToStringArrayOutput()
		// Read the actual binding from Docker; provider Ports can retain input-only values.
		resp.ConnectionInfo = gateway.ID().ApplyT(func(id pulumi.ID) (string, error) {
			published, err := inspectPublishedPort(string(id), 8080)
			if err != nil {
				return "", err
			}
			return fmt.Sprintf("Private test instance: http://127.0.0.1:%d/ on the VPS. Forward this port through SSH to open it on your computer.", published), nil
		}).(pulumi.StringOutput)
		return nil
	})
}
