# Chaos-provable failure modes

Seed knowledge for proposing umbrella rules. Each failure mode lists:

- **Code signal**: the inventory fact kinds that suggest the failure mode.
- **Mitigations**: what makes the signal a non-finding.
- **Faults**: allowlisted chaos faults that prove the risk. A rule must reference
  at least one of these and nothing outside the allowlist below.
- **Probe signal**: what an experiment observes when the risk is real.

A finding is only worth reporting when a chaos experiment can turn it into a
pass/fail result. If you cannot name the fault and the probe signal, it is
not a finding.

## Fault allowlist

The server rejects any fault outside this list.

```
pod-delete pod-cpu-hog pod-memory-hog
pod-network-latency pod-network-loss pod-network-corruption pod-network-duplication
pod-dns-error pod-dns-spoof
pod-http-latency pod-http-status-code pod-http-modify-body pod-http-modify-header pod-http-reset-peer
pod-io-stress pod-autoscaler
node-drain node-cpu-hog node-memory-hog node-io-stress node-restart node-taint
container-kill disk-fill
jvm-cpu-hog jvm-memory-hog jvm-method-latency
```

## 1. Outbound call without timeout

| | |
|---|---|
| Suggested identity | `code-outbound-call-without-timeout` |
| Category / severity | `Dependency` / `High` |
| Code signal | `outbound_client` facts with `timeout: none` (Go `http.Client{}` or `http.DefaultClient`, `grpc.Dial` without deadline, Java `RestTemplate`/`WebClient`/`OkHttp` without timeouts, Python `requests.*` without `timeout=`, Node `fetch`/`axios` without `timeout`/`signal`) |
| Mitigations | Client built by a shared factory that sets timeouts; context deadline at the call site; mesh timeout for the destination in repo config |
| Faults | `pod-network-latency`, `pod-http-latency` |
| Probe signal | Caller p99 latency and in-flight request count grow without bound; request threads/goroutines pile up |

## 2. Retry without backoff or limit

| | |
|---|---|
| Suggested identity | `code-retry-without-backoff` |
| Category / severity | `Resilience` / `High` |
| Code signal | `retry_construct` facts: loops that re-issue a call on error with no sleep, constant sleep, or no attempt cap |
| Mitigations | Resilience library with exponential backoff and jitter (`resilience4j`, `tenacity`, `cenkalti/backoff`, `p-retry`, `failsafe`) |
| Faults | `pod-http-status-code`, `pod-network-loss` |
| Probe signal | Request rate to the dependency multiplies while it returns 5xx; caller error rate does not recover after the fault ends |

## 3. Synchronous dependency without fallback

| | |
|---|---|
| Suggested identity | `code-sync-dependency-without-fallback` |
| Category / severity | `Availability` / `High` |
| Code signal | Serving handler makes an `outbound_client` call and returns its error directly; no circuit breaker, cache or default value in the call path |
| Mitigations | Circuit breaker (`resilience4j`, `hystrix`, `gobreaker`, `pybreaker`, `opossum`); cached or degraded response path |
| Faults | `pod-http-status-code`, `pod-delete` (on the dependency), `pod-network-loss` |
| Probe signal | Caller endpoint error rate tracks dependency error rate one-to-one |

## 4. Missing graceful shutdown

| | |
|---|---|
| Suggested identity | `code-missing-graceful-shutdown` |
| Category / severity | `Availability` / `Medium` |
| Code signal | `serving_entrypoint` fact with no `signal_handler` fact in the same module (Go `ListenAndServe` without `Shutdown` on `SIGTERM`, Node `listen` without `SIGTERM` handler, Python server without signal handling, Spring without `server.shutdown=graceful`) |
| Mitigations | Framework default graceful shutdown that the repo config enables |
| Faults | `pod-delete`, `container-kill` |
| Probe signal | 5xx or connection resets on in-flight requests during pod termination |

## 5. Misconfigured health checks

| | |
|---|---|
| Suggested identity | `code-health-check-masks-dependency-state` |
| Category / severity | `Availability` / `Medium` |
| Code signal | `health_endpoint` fact whose handler always returns OK, or a liveness handler that calls downstream dependencies |
| Mitigations | Separate readiness and liveness handlers; readiness reflects only critical dependencies |
| Faults | `pod-http-status-code` (on the dependency), `pod-network-loss` |
| Probe signal | Pod stays Ready while requests fail (always-OK), or restart storm when a dependency is down (liveness calls dependency) |

## 6. Stale connections or DNS

| | |
|---|---|
| Suggested identity | `code-stale-connection-or-dns` |
| Category / severity | `Dependency` / `Medium` |
| Code signal | Long-lived client or pool created once with no idle timeout, max lifetime or keep-alive; resolved address cached at startup; JVM `networkaddress.cache.ttl=-1` |
| Mitigations | Pool `maxLifetime`/`idleTimeout`; client-side load balancing that re-resolves |
| Faults | `pod-dns-error`, `pod-delete` (on the dependency), `pod-network-loss` |
| Probe signal | Errors persist after the dependency pod is replaced, until the caller restarts |

## 7. Unbounded resource usage

| | |
|---|---|
| Suggested identity | `code-unbounded-resource-usage` |
| Category / severity | `Performance` / `High` |
| Code signal | `pool_or_queue` facts with no bound (unbounded channel or queue, unbounded thread/goroutine spawn per request, cache without max size or TTL, full request body read without limit) |
| Mitigations | Explicit size limit, semaphore, worker pool, `http.MaxBytesReader`, cache eviction policy |
| Faults | `pod-memory-hog`, `pod-cpu-hog`, `jvm-memory-hog`, `pod-network-latency` (to back up the queue) |
| Probe signal | Memory grows until OOMKill; latency collapses under load instead of shedding |

## 8. Local state or single-instance assumption

| | |
|---|---|
| Suggested identity | `code-local-state-assumption` |
| Category / severity | `Availability` / `Medium` |
| Code signal | `local_state` facts: writes to local disk outside a temp dir, in-memory session or job state, in-process scheduler or leader logic without a distributed lock |
| Mitigations | External store (Redis, DB, object store); leader election; idempotent jobs |
| Faults | `pod-delete`, `disk-fill`, `node-drain` |
| Probe signal | Lost sessions or jobs after pod deletion; write errors under `disk-fill` |

## JVM specifics

For JVM services, also consider `jvm-method-latency` (prove a missing timeout
on a specific method) and `jvm-memory-hog` (prove unbounded heap use). Add
them to a rule's `faults` only when the rule covers JVM code.
