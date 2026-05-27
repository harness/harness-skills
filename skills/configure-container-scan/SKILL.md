---
name: configure-container-scan
description: >-
  Add container image scanning steps to existing Harness pipelines using Harness STO scanners.
  Supports Harness SCA (default), Aqua Trivy, Grype, Snyk, Prisma Cloud, Anchore, Black Duck, and Wiz.
  Supports Docker Hub, ECR, GCR, and other Third-Party registries as well as Harness and Local registries.
  Can insert the scan step into an existing CI stage or create a dedicated SecurityTests stage.
  Use when asked to add container scanning, configure image scanning, set up SCA for Docker images, scan container
  images for vulnerabilities, or add container security checks to a pipeline.
  Trigger phrases: add container scan, scan docker image, configure image scanning, set up SCA, add vulnerability scan
  for container, scan container before deploy, add Trivy scan, add Grype scan, add Snyk container scan.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Configure Container Scan

Add a container image scanning step to an existing Harness pipeline using the native `HarnessSCA` STO scanner.

## Instructions

### Step 1: Establish Scope and Pipeline Context

Ask for org, project, and pipeline identifier if not already known. This skill only works with existing pipelines.

```
Call MCP tool: harness_get
Parameters:
  resource_type: "pipeline"
  resource_id: "<pipeline_identifier>"
  org_id: "<organization>"
  project_id: "<project>"
```

### Step 2: Analyze Pipeline Structure

Parse the pipeline YAML to identify:
- All stages and their types (`CI`, `SecurityTests`, `Deployment`, `Approval`)
- Whether a `SecurityTests` stage already exists
- Existing steps in each stage

Present the structure to the user:

```
Pipeline: <name>

Stage 1: <stage_name> (type: <stage_type>)
  - Step 1: <step_name> (type: <step_type>)
  ...
```

**Ask the user where they want the scanner step added:**

Present the available insertion points:
- Any existing `CI` stage (scanner step is added directly into that stage's `execution.steps`)
- Any existing `SecurityTests` stage (scanner step is added into that stage's `execution.steps`)
- A new `SecurityTests` stage (appended to the pipeline if no suitable stage exists or user prefers isolation)

**Recommendation guidance:**
- Adding into an existing `CI` stage — simpler, no extra infrastructure needed, scan runs as part of the build
- Adding a new `SecurityTests` stage — isolated, runs independently, useful when scanning images built elsewhere or from a registry

If the user doesn't specify, default to adding inside the existing `CI` stage if one exists.

### Step 3: Recommend Scanner Type

Present the available container image scanners supported in Harness STO:

**Available Container Scanners:**
- **Harness SCA** (default — native Harness container scanner, zero config)
- **Aqua Trivy** (open-source, broad OS and library coverage)
- **Grype** (open-source by Anchore, fast and accurate)
- **Snyk** (commercial, developer-friendly with fix advice)
- **Prisma Cloud** (commercial, enterprise runtime + image scanning)
- **Anchore Enterprise** (commercial, policy-based enforcement)
- **Black Duck** (commercial, license compliance + vulnerabilities)
- **Wiz** (commercial, cloud-native security)

**Default recommendation:** Use **Harness SCA** — native, no additional credentials required, and integrates directly with Harness STO results.

Ask the user which scanner they prefer. If they don't specify, use Harness SCA as the default.

**Step type mapping and scanner product auth requirements:**

| Scanner | `type` field | Product auth needed? | Auth fields |
|---------|-------------|----------------------|-------------|
| Harness SCA | `HarnessSCA` | No | — |
| Aqua Trivy | `AquaTrivy` | No | — |
| Grype | `Grype` | No | — |
| Snyk | `Snyk` | Yes | `access_token` (Snyk API token) |
| Prisma Cloud | `PrismaCloud` | Yes | `access_id` (Access Key), `access_token` (Secret Key) |
| Anchore Enterprise | `AnchoreEnterprise` | Yes | `access_id` (username), `access_token` (password/API key) |
| Black Duck | `BlackDuck` | Yes | `access_token` (Hub API token) |
| Wiz | `Wiz` | Yes | `access_id` (Client ID), `access_token` (Client Secret) |

**If the user picks a commercial scanner (Snyk, Prisma Cloud, Anchore Enterprise, Black Duck, Wiz):**

1. Inform the user that this scanner requires product-level authentication credentials
2. Ask for the required secret references from the table above — these must already exist as Harness secrets
3. Format them as `<+secrets.getValue("project.<secret_identifier>")>`
4. These go into the `auth` block of the step spec — separate from the registry image credentials

Example prompt to user:
> "Snyk requires an API token. Please provide the Harness secret identifier for your Snyk API token (e.g., `snyk_api_token`). I'll reference it as `<+secrets.getValue("project.snyk_api_token")>`."

If the secret doesn't exist yet, suggest creating it first via `/create-secret` before proceeding.

### Step 4: Collect Container Image Details (skip for Prisma Cloud / Wiz — they pull from registry via connector)

Ask the user which registry type their image is in, then collect the fields for that type:

---

**Option A — Harness Registry**

The image is stored in the Harness internal container registry.

| Field | Required | Description |
|-------|----------|-------------|
| Registry | Yes | Harness registry connector ref (e.g., `account.account-level-test`) |
| Image Path | Yes | e.g., `harness/todolist-sample` — maps to `image_path` in YAML |

YAML:
```yaml
      image:
        type: harness
        registry: <harness_registry_connector_ref>
        image_path: <image_path>
```

---

**Option B — Third-Party Registry** (Docker Hub, ECR, GCR, ACR, JFrog, etc.)

| Field | Required | Description |
|-------|----------|-------------|
| Type | Yes | Registry protocol — almost always `docker_v2` |
| Domain | No | Defaults to `docker.io`. For ECR: `123456789.dkr.ecr.us-east-1.amazonaws.com`, for GCR: `gcr.io` |
| Name | Yes | Image name, e.g., `harness/todolist-sample` or `myorg/myapp` |
| Tag / Digest | Yes | e.g., `latest`, `123`, or `sha256:1234567890abcdef...` |
| Access Id | No | Secret ref for private registry username/access key, e.g., `<+secrets.getValue("project.access_id")>` |
| Access Token | No | Secret ref for private registry password/token, e.g., `<+secrets.getValue("project.access_token")>` |

YAML:
```yaml
      image:
        type: docker_v2
        domain: <domain>              # omit if Docker Hub (docker.io)
        name: <image_name>
        tag: <tag>
        access_id: <+secrets.getValue("project.access_id")>     # omit if public image
        access_token: <+secrets.getValue("project.access_token")>  # omit if public image
```

---

**Option C — Local (image built in this stage)**

The image was built earlier in the same pipeline stage and is available locally on the build node.

| Field | Required | Description |
|-------|----------|-------------|
| Name | Yes | Image name, e.g., `harness/todolist-sample` |
| Tag / Digest | Yes | e.g., `latest`, `123`, or `sha256:1234567890abcdef...` |
| Domain | No | Defaults to `docker.io` |

YAML:
```yaml
      image:
        type: local_image
        name: <image_name>
        tag: <tag>
        domain: <domain>   # omit if not needed
```

---

**Default:** Third-Party → Docker Hub (`docker_v2`, domain `docker.io`) with `latest` tag if the user doesn't specify.

### Step 4: Collect Infrastructure Details (if needed)

**Only required when adding a new `SecurityTests` stage.** If inserting into an existing CI or SecurityTests stage, skip this step — the stage already has infrastructure.

If a new `SecurityTests` stage is being created and infrastructure is not yet defined, ask for:
- **Delegate connector** (e.g., `account.stoqadelegate`)
- **Namespace** (e.g., `harness-delegate`)

### Step 5: Generate the Scanner Step YAML

Use the step `type` from the scanner mapping in Step 3. Examples below.

**For Harness SCA (default scanner):**

```yaml
- step:
    type: HarnessSCA
    name: Container_Scan
    identifier: Container_Scan
    spec:
      mode: orchestration
      config: default
      target:
        type: container
        detection: auto
      advanced:
        log:
          level: info
      resources:
        limits:
          memory: 2G
          cpu: 1000m
      privileged: true
      image:
        <use the image block from Step 4 based on registry type>
```

Use the `image` block generated in Step 4 (Harness / Third-Party / Local). The rest of the step spec is identical regardless of registry type.

**For Aqua Trivy (open-source):**

```yaml
- step:
    type: AquaTrivy
    name: Aqua_Trivy_Scan
    identifier: Aqua_Trivy_Scan
    spec:
      mode: orchestration
      config: default
      target:
        type: container
        detection: auto
      advanced:
        log:
          level: info
      privileged: true
      image:
        type: docker_v2
        name: <image_name>
        tag: <tag>
```

**For Grype (open-source):**

```yaml
- step:
    type: Grype
    name: Grype_Scan
    identifier: Grype_Scan
    spec:
      mode: orchestration
      config: default
      target:
        type: container
        detection: auto
      advanced:
        log:
          level: info
      privileged: true
      image:
        type: docker_v2
        name: <image_name>
        tag: <tag>
```

**For commercial scanners — add an `auth` block with scanner product credentials:**

```yaml
- step:
    type: Snyk                       # or PrismaCloud, AnchoreEnterprise, BlackDuck, Wiz
    name: Snyk_Container_Scan
    identifier: Snyk_Container_Scan
    spec:
      mode: orchestration
      config: default
      target:
        type: container
        detection: auto
      auth:
        access_id: <+secrets.getValue("project.snyk_access_id")>     # omit if scanner only needs token
        access_token: <+secrets.getValue("project.snyk_api_token")>
      advanced:
        log:
          level: info
      privileged: true
      image:
        type: docker_v2
        name: <image_name>
        tag: <tag>
```

Use the `auth` field names from the scanner product auth table in Step 3. Only include `access_id` if the scanner requires it (Snyk only needs `access_token`; Prisma Cloud, Anchore, and Wiz need both).

### Step 6: Build the Updated Pipeline YAML

**Scenario A — Adding to an existing `CI` stage:**

Insert the step into `spec.execution.steps` of the chosen CI stage. The stage already has its own infrastructure and `cloneCodebase: true`. No changes needed to the stage itself — just append the step:

```yaml
- step:
    type: HarnessSCA
    name: Container_Scan
    identifier: Container_Scan
    spec:
      mode: orchestration
      config: default
      target:
        type: container
        detection: auto
      advanced:
        log:
          level: info
      resources:
        limits:
          memory: 2G
          cpu: 1000m
      privileged: true
      image:
        type: docker_v2
        name: <image_name>
        tag: <tag>
```

**Scenario B — Adding to an existing `SecurityTests` stage:**

Insert the step into `spec.execution.steps` of the existing stage. Ensure the stage has:
- `cloneCodebase: false`
- `privileged: true` on the step

**Scenario C — No suitable stage exists, creating a new `SecurityTests` stage:**

Append a new stage to the pipeline:

```yaml
- stage:
    name: Container Scan
    identifier: Container_Scan_Stage
    type: SecurityTests
    spec:
      cloneCodebase: false
      infrastructure:
        type: KubernetesDirect
        spec:
          connectorRef: <delegate_connector>
          namespace: <namespace>
          automountServiceAccountToken: true
          nodeSelector: {}
          os: Linux
      execution:
        steps:
          - step:
              type: HarnessSCA
              name: Container_Scan
              identifier: Container_Scan
              spec:
                mode: orchestration
                config: default
                target:
                  type: container
                  detection: auto
                advanced:
                  log:
                    level: info
                resources:
                  limits:
                    memory: 2G
                    cpu: 1000m
                privileged: true
                image:
                  type: docker_v2
                  name: <image_name>
                  tag: <tag>
```

### Step 7: Update Pipeline via MCP

```
Call MCP tool: harness_update
Parameters:
  resource_type: "pipeline"
  resource_id: "<pipeline_identifier>"
  org_id: "<organization>"
  project_id: "<project>"
  body: { yamlPipeline: "<updated pipeline YAML string>" }
```

### Step 8: Provide Summary and Next Steps

```
## Container Scan Configured

**Pipeline:** <pipeline_name>
**Scanner:** <scanner_name> (<scanner_type>)
**Stage:** <stage_name> (SecurityTests)
**Image:** <image_name>:<tag>
**Registry:** <registry_type>

**Pipeline URL:** https://app.harness.io/ng/account/<account_id>/module/sto/orgs/<org_id>/projects/<project_id>/pipelines/<pipeline_id>/pipeline-studio/

### Next Steps
1. Run the pipeline to verify the scan step executes successfully
2. View scan results in the Security Tests tab of the execution
3. Set failure thresholds using `failOnSeverity` (CRITICAL, HIGH, MEDIUM, LOW) in the step's Advanced tab
4. Configure exemptions for false positives via `/security-report` skill
5. Enforce pipeline gates on severity via `/create-policy` skill
```

## Examples

### Scan a public Docker Hub image

```
/create-container-scan
Add a container scan to my pipeline for the image johnkday/nodegoat:latest
```

### Scan a private ECR image

```
/create-container-scan
Add container scanning to my deploy pipeline. The image is in ECR:
123456789.dkr.ecr.us-east-1.amazonaws.com/my-service:v2.1.0
Use our ECR credentials stored in secrets.
```

### Add scan before deployment

```
/create-container-scan
I want to scan my Docker image myorg/api-server:latest before it gets deployed.
Add it to the existing SecurityTests stage in my backend-deploy pipeline.
```

## Performance Notes

- Only works with **existing pipelines** — do not offer to create a new standalone pipeline
- Always ask the user which scanner they want — present the full list; default to **Harness SCA** if not specified
- `HarnessSCA` (and all other scanners) can be added to **CI stages** (inline with build) or **SecurityTests stages** (isolated) — ask the user, default to CI stage if one exists
- For commercial scanners (Snyk, Prisma Cloud, Anchore, Black Duck, Wiz), always ask for scanner product credentials (`auth.access_id` / `auth.access_token`) before generating YAML — these are different from registry credentials
- If required secrets don't exist yet, prompt the user to create them via `/create-secret` before proceeding
- `auth` block sits at the step `spec` level, separate from `image` credentials
- Always set `privileged: true` on the `HarnessSCA` step — it is required for container scanning
- Only ask for delegate infrastructure when creating a **new** `SecurityTests` stage — existing stages already have infrastructure
- Only set `cloneCodebase: false` on `SecurityTests` stages — CI stages already manage their own codebase setting
- Default to `mode: orchestration` and `config: default` unless the user specifies otherwise
- Set resource limits of `memory: 2G` and `cpu: 1000m` to avoid OOM failures during scan
- For ECR images, domain must include the full registry URL, not just the region

## Troubleshooting

### Pipeline Not Found
- Verify `org_id` and `project_id` are correct
- Confirm the pipeline exists with `harness_list` (resource_type: "pipeline")

### Scan Step Fails with Permission Error
- Ensure `privileged: true` is set on the step spec
- Verify the delegate has Docker socket access in the namespace

### Image Pull Failure
- For private registries, ensure `image.access_id` and `image.access_token` reference valid secrets
- For ECR, confirm the delegate has the correct IAM role to pull images
- For Docker Hub, check rate limits; supply credentials to avoid anonymous pull limits

### Scanner Authentication Failure (commercial scanners)
- Verify `auth.access_token` (and `auth.access_id` where required) reference valid Harness secrets
- Confirm the secret identifiers match exactly — check with `harness_get(resource_type="secret")`
- For Snyk: only `access_token` is needed (API token), not `access_id`
- For Prisma Cloud / Wiz / Anchore: both `access_id` and `access_token` are required
- If secrets don't exist, create them first via `/create-secret` then re-run the skill

### No Results in Security Tests Tab
- Confirm STO module is enabled for the account
- Check the execution logs for scanner errors
- Verify the image name and tag are correct and the image exists in the registry

### Pipeline Update Validation Errors
- Verify YAML indentation (2 spaces throughout)
- Ensure step `identifier` matches pattern `^[a-zA-Z_][0-9a-zA-Z_]{0,127}$`
- Confirm the `SecurityTests` stage has a valid `infrastructure` block with a working delegate connector
