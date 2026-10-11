# Build natively on the worker, cross-compile for the AMD64 manager runtime.
FROM --platform=$BUILDPLATFORM golang:1.26.2-bookworm AS builder
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY main.go main_test.go Pulumi.yaml ./
RUN go test ./...
ARG SCENARIO_ARCH=amd64
RUN CGO_ENABLED=0 GOOS=linux GOARCH=${SCENARIO_ARCH} go build -trimpath -o /out/main . \
    && cp Pulumi.yaml /out/Pulumi.yaml
FROM scratch AS artifact
COPY --from=builder /out/ /
