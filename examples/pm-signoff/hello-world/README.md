# PM_Signoff Hello World

A minimal Node.js hello world application with Harness resource definitions for the **PM_Signoff** project.

## What's included

| Path | Purpose |
|------|---------|
| `app/` | Node.js HTTP server (`Hello, World!` + `/health`) |
| `manifests/` | Kubernetes Deployment and Service |
| `harness/pipeline-ci.yaml` | CI-only pipeline — no connectors required |
| `harness/pipeline-cicd.yaml` | Full build, test, push, and K8s deploy pipeline |
| `harness/service.yaml` | Kubernetes service definition |
| `harness/environment.yaml` | Dev environment |
| `harness/infrastructure.yaml` | Kubernetes infrastructure |
| `scripts/deploy-to-harness.sh` | Push resources to Harness via API |

## Run locally

```bash
cd app
npm test
npm start
curl http://localhost:3000/
curl http://localhost:3000/health
```

## Deploy to Harness (PM_Signoff)

### Prerequisites

1. A Harness project named **PM_Signoff** (create it in the UI or via MCP if it does not exist).
2. Know your **org identifier** (defaults to `default` if unsure).
3. Harness API credentials:
   - `HARNESS_API_KEY`
   - `HARNESS_ACCOUNT_ID`

### Quick start — CI only (no connectors)

This creates a pipeline that runs on Harness Cloud and prints `Hello, World from PM_Signoff!`:

```bash
export HARNESS_API_KEY="your-api-key"
export HARNESS_ACCOUNT_ID="your-account-id"
export HARNESS_ORG="your-org"          # optional, default: default
export HARNESS_PROJECT="PM_Signoff"    # optional, default: PM_Signoff

chmod +x scripts/deploy-to-harness.sh
./scripts/deploy-to-harness.sh ci
```

Then run the **Hello World CI** pipeline from the Harness UI or via MCP:

```
harness_execute(
  resource_type="pipeline",
  org_id="<org>",
  project_id="PM_Signoff",
  resource_id="hello_world_ci",
  action="run"
)
```

### Full CI/CD (connectors required)

Before deploying the full stack, create these connectors in **PM_Signoff**:

| Connector identifier | Type | Used for |
|---------------------|------|----------|
| `github_connector` | GitHub | Source code and K8s manifests |
| `dockerhub_connector` | Docker Registry | Container image push |
| `kubernetes_connector` | Kubernetes | Dev cluster deployment |

Then deploy all resources:

```bash
./scripts/deploy-to-harness.sh all
```

Update `harness/service.yaml` if your Git repo or image path differs from the defaults (`harness-skills` repo, `harness/pm-signoff-hello-world` image).

### Using Harness MCP in Cursor

Authenticate the Harness MCP server in Cursor, then ask the agent to:

1. Verify the project: `harness_list(resource_type="project")`
2. Create the CI pipeline: `harness_create(resource_type="pipeline", org_id="...", project_id="PM_Signoff", body="<pipeline-ci.yaml contents>")`
3. Run it: `harness_execute(resource_type="pipeline", resource_id="hello_world_ci", action="run")`

## Resource identifiers

| Resource | Identifier |
|----------|------------|
| CI pipeline | `hello_world_ci` |
| CI/CD pipeline | `hello_world_cicd` |
| Service | `hello_world_service` |
| Environment | `hello_world_dev` |
| Infrastructure | `hello_world_k8s_dev` |

## Customize org

All YAML files use `orgIdentifier: default` and `projectIdentifier: PM_Signoff`. Override at deploy time with `HARNESS_ORG`, or edit the YAML files directly.
