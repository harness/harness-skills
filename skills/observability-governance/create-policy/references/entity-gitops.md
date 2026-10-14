# GitOps Application Policies

## Package: `gitopsApplication`
## Root path: `input.gitopsApplication`
## Valid actions: `onsave`, `onsync`

## Input Schema

```
input.gitopsApplication.accountIdentifier
input.gitopsApplication.orgIdentifier
input.gitopsApplication.projectIdentifier
input.gitopsApplication.agentIdentifier
input.gitopsApplication.name
input.gitopsApplication.clusterIdentifier
input.gitopsApplication.repoIdentifier

input.gitopsApplication.app.metadata.name
input.gitopsApplication.app.metadata.namespace
input.gitopsApplication.app.metadata.labels                     # object {"harness.io/serviceRef": "...", "team": "..."}

input.gitopsApplication.app.spec.source.repoURL
input.gitopsApplication.app.spec.source.path
input.gitopsApplication.app.spec.source.targetRevision          # "main", "v1.2.3", etc.

input.gitopsApplication.app.spec.sources[i].repoURL             # multi-source apps
input.gitopsApplication.app.spec.sources[i].targetRevision

input.gitopsApplication.app.spec.destination.server             # "https://kubernetes.default.svc"
input.gitopsApplication.app.spec.destination.namespace

input.gitopsApplication.app.spec.project                        # ArgoCD project, e.g. "default"

input.gitopsApplication.app.spec.syncPolicy.automated.prune     # boolean
input.gitopsApplication.app.spec.syncPolicy.automated.selfHeal  # boolean
input.gitopsApplication.app.spec.syncPolicy.syncOptions[i]      # "CreateNamespace=true", etc.

input.gitopsApplication.app.status.sync.status                  # "Synced", "OutOfSync"
input.gitopsApplication.app.status.health.status                # "Healthy", "Degraded", "Progressing"

input.metadata.type                                              # "gitopsApplication"
input.metadata.action                                            # "onsave", "onsync"
input.metadata.timestamp                                         # Unix epoch seconds
input.metadata.principalIdentifier
input.metadata.principalType                                     # "USER"
```

## Example 1: Block protected namespaces

**Scenario:** Prevent deployments to system namespaces like kube-system, argocd, etc.

```rego
package gitopsApplication

blocked_namespaces := [
    "kube-system",
    "kube-public",
    "kube-node-lease",
    "default",
    "argocd",
    "gitops-system",
    "istio-system",
    "cert-manager",
    "monitoring",
    "logging"
]

is_blocked_namespace(ns) {
    blocked_namespaces[_] == ns
}

deny[msg] {
    ns := input.gitopsApplication.app.spec.destination.namespace
    is_blocked_namespace(ns)
    msg := sprintf("Application '%s' cannot deploy to protected namespace '%s'", [input.gitopsApplication.name, ns])
}

deny[msg] {
    ns := input.gitopsApplication.app.spec.destination.namespace
    startswith(ns, "kube-")
    msg := sprintf("Application '%s' cannot deploy to Kubernetes reserved namespace '%s'", [input.gitopsApplication.name, ns])
}

deny[msg] {
    ns := input.gitopsApplication.app.spec.destination.namespace
    startswith(ns, "openshift-")
    msg := sprintf("Application '%s' cannot deploy to OpenShift reserved namespace '%s'", [input.gitopsApplication.name, ns])
}
```

## Example 2: Require labels

**Scenario:** Applications must have `harness.io/serviceRef` and `harness.io/envRef` labels.

```rego
package gitopsApplication

required_labels := ["harness.io/serviceRef", "harness.io/envRef"]

deny[msg] {
    label := required_labels[_]
    not input.gitopsApplication.app.metadata.labels[label]
    msg := sprintf("Application '%s' is missing required label '%s'", [input.gitopsApplication.name, label])
}

deny[msg] {
    label := required_labels[_]
    input.gitopsApplication.app.metadata.labels[label] == ""
    msg := sprintf("Application '%s' has empty value for required label '%s'", [input.gitopsApplication.name, label])
}
```

## Example 3: Enforce stable target revisions for production

**Scenario:** Apps with names starting with `prod` must use stable branches or semver tags.

```rego
package gitopsApplication

stable_branches := ["master", "main", "release"]

deny[msg] {
    startswith(input.gitopsApplication.app.metadata.name, "prod")
    rev := input.gitopsApplication.app.spec.source.targetRevision
    not is_stable_revision(rev)
    msg := sprintf("Production app '%s' must use a stable target revision, got '%s'", [input.gitopsApplication.name, rev])
}

deny[msg] {
    startswith(input.gitopsApplication.app.metadata.name, "prod")
    source := input.gitopsApplication.app.spec.sources[_]
    rev := source.targetRevision
    not is_stable_revision(rev)
    msg := sprintf("Production app '%s' has source with unstable revision '%s'", [input.gitopsApplication.name, rev])
}

is_stable_revision(rev) {
    stable_branches[_] == rev
}

is_stable_revision(rev) {
    regex.match(`^v?\d+\.\d+\.\d+`, rev)
}
```

## Example 4: Restrict sync during off-hours

**Scenario:** Block sync operations outside business hours (deny 6PM-6AM UTC).

```rego
package gitopsApplication

deny[msg] {
    input.metadata.action == "onsync"
    ts := input.metadata.timestamp
    hour := (ts / 3600) % 24
    hour >= 18
    msg := sprintf("Application '%s' cannot sync after 6 PM UTC", [input.gitopsApplication.name])
}

deny[msg] {
    input.metadata.action == "onsync"
    ts := input.metadata.timestamp
    hour := (ts / 3600) % 24
    hour < 6
    msg := sprintf("Application '%s' cannot sync before 6 AM UTC", [input.gitopsApplication.name])
}
```

## Sample JSON

```json
{
  "gitopsApplication": {
    "accountIdentifier": "your_account_id",
    "orgIdentifier": "your_org_id",
    "projectIdentifier": "your_project_id",
    "agentIdentifier": "account.your_gitops_agent",
    "name": "my-workload-app",
    "app": {
      "metadata": {
        "name": "my-workload-app",
        "namespace": "gitops-agent-namespace",
        "labels": {
          "harness.io/serviceRef": "workload_service",
          "harness.io/envRef": "staging",
          "team": "platform"
        }
      },
      "spec": {
        "source": {
          "repoURL": "https://github.com/your-org/workloads",
          "path": "apps/my-workload",
          "targetRevision": "main"
        },
        "destination": {
          "server": "https://kubernetes.default.svc",
          "namespace": "workload-namespace"
        },
        "project": "default",
        "syncPolicy": {
          "automated": { "prune": true, "selfHeal": true }
        }
      },
      "status": {
        "sync": { "status": "OutOfSync" },
        "health": { "status": "Healthy" }
      }
    }
  },
  "metadata": {
    "type": "gitopsApplication",
    "action": "onsave",
    "timestamp": 1700000000,
    "principalIdentifier": "developer@example.com",
    "principalType": "USER"
  }
}
```
