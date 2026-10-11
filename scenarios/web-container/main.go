package main

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"strconv"

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
			Ports: docker.ContainerPortArray{docker.ContainerPortArgs{
				Internal: pulumi.Int(port), Ip: pulumi.String("127.0.0.1"), Protocol: pulumi.String("tcp"),
			}},
			Rm: pulumi.Bool(true),
		}, opts...)
		if err != nil {
			return err
		}
		resp.Flags = pulumi.StringArray{pulumi.String(flag)}.ToStringArrayOutput()
		resp.ConnectionInfo = container.Ports.ApplyT(func(ports []docker.ContainerPort) (string, error) {
			if len(ports) == 0 || ports[0].External == nil {
				return "", fmt.Errorf("missing published port")
			}
			return fmt.Sprintf("Private test instance: http://127.0.0.1:%d/ on the VPS. Forward this port through SSH to open it on your computer.", *ports[0].External), nil
		}).(pulumi.StringOutput)
		return nil
	})
}
