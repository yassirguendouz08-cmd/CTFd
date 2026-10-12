# Version-matched upstream source archive is unpacked into the build context.
# Generated API files are included in the official source release.
FROM golang:1.26.3@sha256:313faae491b410a35402c05d35e7518ae99103d957308e940e1ae2cfa0aac29b AS builder
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN git apply disable-telemetry.patch
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-s -w -X github.com/ctfer-io/chall-manager/cmd/chall-manager.Version=v0.6.6" -o /out/chall-manager ./cmd/chall-manager

FROM pulumi/pulumi-go:3.237.0@sha256:d5bbc516cf6df7078a8ffe7e593bfccb6cb02ea4049738e3934587dd9ae9f1dc
COPY --from=builder /out/chall-manager /chall-manager
COPY gen /gen
ENV PULUMI_SKIP_UPDATE_CHECK=true \
    OTEL_SDK_DISABLED=true \
    OTEL_TRACES_EXPORTER=none \
    OTEL_METRICS_EXPORTER=none \
    OTEL_LOGS_EXPORTER=none
ENTRYPOINT ["/chall-manager"]
