# Authoring an umbrella rule

Rules are server-side data in the Harness project. During a repository scan the
skill creates a missing catalog rule and continues. It does not update an existing
rule. Creating or editing a rule because the user asked for that rule, outside a
scan, still waits for confirmation in chat.

## When to create, update or drop

Work through this in order and stop at the first match:

1. **An existing rule covers the failure mode.** Map the finding to it. Do
   not create anything.
2. **An existing rule covers the failure mode but misses this language or
   library.** Propose an **update** that adds one `prompt.do` bullet. Same
   confirmation as a create.
3. **No rule covers it, and the failure mode is in `failure-modes.md`.**
   Propose a **create** using that entry's identity, category, severity and
   faults.
4. **No rule covers it, and the failure mode is not in `failure-modes.md`.**
   Propose a create only if you can name an allowlisted fault and a concrete
   probe signal. Otherwise drop the finding.

Two rules overlap when they share a category, have overlapping faults and
describe the same failure. Overlap means update, not create.

## Hard constraints (the server enforces these)

| Field | Constraint |
|---|---|
| `identity` | `^code-[a-z0-9-]{3,60}$`. Names a failure mode: `code-outbound-call-without-timeout`, never `code-payments-http-client` |
| `spec.dataSource` | `["SourceCode"]` |
| `spec.faults` | Non-empty; every entry on the allowlist in `failure-modes.md` |
| `spec.prompt` | `do` and `outcome` are non-empty lists; `dont` is optional. Each list has at most 10 entries of at most 500 characters |
| `severity` | `Critical`, `High`, `Medium` or `Low` |
| `category` | `Availability`, `Performance`, `Dependency`, `Resilience` or `Config` |
| Count | At most 30 custom `SourceCode` rules per project |

`spec.isSystem` is always false for these rules; the server ignores any other value.

## Soft constraints (the skill enforces these)

- **Generic.** No repo, service, file, team or company names anywhere in the
  rule. Library names belong only in `prompt.do` bullets.
- **Severity reflects blast radius.** `Critical` is reserved for failures that
  take a whole service down on a single dependency fault. Most code rules are
  `High` or `Medium`.
- **`prompt.do`**: three to six bullets, each a concrete code signal.
- **`prompt.dont`**: the mitigations that make a signal a non-finding. Always
  include "test, example, vendor, generated and CLI code".
- **`prompt.outcome`**: a list with one sentence holding the hypothesis, the
  fault and the probe signal (the field is `[]string`; a bare string is rejected).

## Example

```json
{
  "identity": "code-outbound-call-without-timeout",
  "name": "Outbound call without timeout",
  "description": "A serving path calls a network dependency with no client or per-call timeout, so a slow dependency exhausts caller threads, goroutines or connections.",
  "severity": "High",
  "category": "Dependency",
  "tags": ["code-scan", "timeouts"],
  "spec": {
    "dataSource": ["SourceCode"],
    "faults": ["pod-network-latency", "pod-http-latency"],
    "prompt": {
      "do": [
        "Go: http.Client{} or http.DefaultClient used without Timeout, and the request context has no deadline",
        "Go: grpc.Dial/NewClient call sites whose RPCs use a context without deadline",
        "Java: RestTemplate, WebClient, OkHttpClient or Apache HttpClient built without connect and read timeouts",
        "Python: requests/httpx calls without timeout=",
        "Node: fetch/axios/got calls without timeout or AbortSignal"
      ],
      "dont": [
        "Clients created by a shared factory that sets timeouts",
        "Destinations covered by a mesh timeout in repo config",
        "Test, example, vendor, generated and CLI code"
      ],
      "outcome": ["With pod-network-latency on the dependency, caller p99 latency stays bounded by its timeout and in-flight requests do not grow without bound."]
    }
  }
}
```

## Confirmation message format

Use this only when the user asked to add or edit a rule on its own. A repository
scan creates a missing catalog rule without showing it.

```
Proposed rule: <identity> (<create|update>)
  Name:      <name>
  Severity:  <severity>   Category: <category>
  Faults:    <faults>
  Do:        <bullets>
  Don't:     <bullets>
  Outcome:   <outcome>
  Needed by: <N> findings in <modules>
Create this rule? (yes / no / edit)
```

On "no", drop the findings that need the rule. On "edit", apply the change
and show the message again.
