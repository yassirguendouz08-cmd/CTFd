package main

import (
	"strings"
	"testing"
)

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
