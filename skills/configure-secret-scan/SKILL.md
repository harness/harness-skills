---
name: configure-secret-scan
description: >-
  Add secret detection scanning steps to existing Harness pipelines using STO security scanners.
  Detects exposed credentials, API keys, tokens, and sensitive data in code repositories.
  Supports Gitleaks (default, open-source, built-in), Harness Code, Semgrep, Snyk, SonarQube,
  Checkmarx, Fossa, Aqua Trivy, and Wiz. Only works with existing pipelines that have a codebase
  connector configured. Use when asked to add secret scanning, detect exposed secrets, find leaked
  API keys, configure secret detection, or scan code for credentials.
  Trigger phrases: add secret scan, detect secrets, find leaked credentials, configure secret detection,
  scan for exposed API keys, add Gitleaks, secret scanning pipeline.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Configure Secret Scan

Add secret detection scanning steps to existing Harness pipelines using Harness STO. Scans code repositories for exposed credentials, API keys, tokens, and other sensitive information.

## Instructions

### Step 1: Establish Scope and Pipeline Context

Ask the user for the organization, project, and pipeline identifier if not already known. This skill only works with existing pipelines.

```
Call MCP tool: harness_get
Parameters:
  resource_type: "pipeline"
  resource_id: "<pipeline_identifier>"
  org_id: "<organization>"
  project_id: "<project>"
```

### Step 2: Extract Repository Connector from Pipeline

Parse the pipeline YAML to automatically identify the repository connector.

- For v0 pipelines: Check `pipeline.properties.ci.codebase.connectorRef`
- For v1 pipelines: Check the codebase connector in the pipeline configuration

If no connector is found, inform the user the pipeline has no codebase configuration and cannot proceed with secret scanning.

### Step 3: Analyze Pipeline Structure

Parse the pipeline YAML to identify all stages, steps, and any existing secret scanning steps.

Present the structure to the user:

```
Pipeline: <name>

Stage 1: <stage_name> (type: <stage_type>)
  - Step 1: <step_name> (type: <step_type>)
  ...
```

Ask where to insert the secret scan step — before or after which step, or at the end of which stage. Recommend adding it **early in the CI stage**, before build steps, so secrets are caught before any artifacts are produced.

### Step 4: Recommend Scanner Type

Present the available secret detection scanners supported in Harness STO:

**Dedicated secret scanners:**
- **Gitleaks** (default — open-source, no paid license, built-in scanner available)

**Scanners that also detect secrets as a side effect** (findings appear under the "Secret" issue type alongside SAST/SCA results):
- Harness Code (native)
- Aqua Trivy (open-source)
- Checkmarx (commercial)
- Checkmarx One (commercial)
- Fossa (commercial)
- Semgrep (open-source core / commercial)
- Snyk (commercial)
- SonarQube (commercial)
- Wiz (commercial)

**Default recommendation:** Use **Gitleaks with the Built-in Scanner** — open-source, zero config, no license required, and purpose-built for secret detection.

Ask the user which scanner they prefer. If they don't specify, use Gitleaks as the default.

**Scanner product auth requirements:**

| Scanner | `type` field | Product auth needed? | Auth fields |
|---------|-------------|----------------------|-------------|
| Gitleaks | `Gitleaks` | No | — |
| Harness Code | `HarnessSAST` | No | — |
| Aqua Trivy | `AquaTrivy` | No | — |
| Semgrep (OSS) | `Semgrep` | No | — |
| Semgrep (commercial) | `Semgrep` | Yes | `access_token` (Semgrep API token) |
| Snyk | `Snyk` | Yes | `access_token` (Snyk API token) |
| SonarQube | `SonarQube` | Yes | `access_id` (host URL), `access_token` (user token) |
| Checkmarx | `Checkmarx` | Yes | `access_id` (username), `access_token` (password) |
| Checkmarx One | `CheckmarxOne` | Yes | `access_id` (client ID), `access_token` (client secret) |
| Fossa | `Fossa` | Yes | `access_token` (FOSSA API key) |
| Wiz | `Wiz` | Yes | `access_id` (client ID), `access_token` (client secret) |

**If the user picks a commercial scanner:**
1. Inform the user that scanner product credentials are required
2. Ask for the secret references from the table above — secrets must already exist in Harness
3. Format as `<+secrets.getValue("project.<secret_identifier>")>`
4. If secrets don't exist, prompt the user to create them via `/create-secret` first

### Step 5: Generate Scanner Step Configuration

**For Gitleaks (default — Built-in Scanner):**

```yaml
- step:
    type: Gitleaks
    name: Gitleaks_Secret_Scan
    identifier: Gitleaks_Secret_Scan
    spec:
      mode: orchestration
      config: default
      target:
        type: repository
        detection: auto
      advanced:
        log:
          level: info
```

**For Harness Code (also detects secrets):**

```yaml
- step:
    type: HarnessSAST
    name: Harness_Code_Scan
    identifier: Harness_Code_Scan
    spec:
      mode: orchestration
      config: sast_sca
      target:
        type: repository
        detection: auto
      advanced:
        log:
          level: info
```

**For Semgrep (OSS, no auth):**

```yaml
- step:
    type: Semgrep
    name: Semgrep_Secret_Scan
    identifier: Semgrep_Secret_Scan
    spec:
      mode: orchestration
      config: default
      target:
        type: repository
        detection: auto
      advanced:
        log:
          level: info
```

**For commercial scanners — add `auth` block with scanner product credentials:**

```yaml
- step:
    type: Snyk                        # or SonarQube, Checkmarx, CheckmarxOne, Fossa, Wiz
    name: Snyk_Secret_Scan
    identifier: Snyk_Secret_Scan
    spec:
      mode: orchestration
      config: default
      target:
        type: repository
        detection: auto
      auth:
        access_id: <+secrets.getValue("project.scanner_access_id")>   # omit if not required
        access_token: <+secrets.getValue("project.scanner_token")>
      advanced:
        log:
          level: info
```

Use the `auth` field names from the scanner table in Step 4. Only include `access_id` for scanners that require it.

### Step 6: Insert Step into Pipeline YAML

Insert the generated step at the location chosen in Step 3. Ensure proper indentation and structure.

**Key rules:**
- Secret scan steps must be in CI stages (`type: CI`) with `cloneCodebase: true` — source code must be available
- Place secret scanning **early** — before build steps, so secrets are caught before artifacts are produced
- Do not add to Deployment or Approval stages
- Add to `spec.execution.steps` of the chosen stage

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
## Secret Scanner Configured

**Pipeline:** <pipeline_name>
**Scanner:** <scanner_name> (<scanner_type>)
**Location:** Stage "<stage_name>", <position description>
**Connector:** <connector_name>

**Pipeline URL:** https://app.harness.io/ng/account/<account_id>/module/sto/orgs/<org_id>/projects/<project_id>/pipelines/<pipeline_id>/pipeline-studio/

**Note:** Secret detection findings appear under the "Secret" issue type in the Security Tests tab.

### Next Steps
1. Run the pipeline to verify the scanner step executes successfully
2. View secret detection results in the Security Tests tab under the "Secret" issue type
3. Remediate found secrets — rotate any exposed credentials immediately
4. Configure exemptions for false positives via `/security-report` skill
5. Enforce pipeline gates on detected secrets via `/create-policy` skill
```

## Examples

### Add Gitleaks to existing CI pipeline

```
/configure-secret-scan
Add secret scanning to my backend-api pipeline in the platform project
```

### Use Semgrep for secret detection

```
/configure-secret-scan
I already use Semgrep for SAST — configure it to also detect secrets in my CI pipeline
```

### Add secret scan early in pipeline

```
/configure-secret-scan
Add Gitleaks before the build step in my payment-service pipeline so we catch leaked keys before building
```

## Performance Notes

- Only works with **existing pipelines** — do not offer to create new pipelines
- Automatically extract the repo connector from the pipeline; do not ask the user for it
- Place the secret scan step **before build steps** — catching secrets early prevents them from being baked into artifacts
- Default to **Gitleaks** unless the user specifies another scanner or already has one configured
- For commercial scanners, always ask for `auth` credentials before generating YAML — missing auth causes runtime failures
- If required secrets don't exist, prompt the user to create them via `/create-secret` before proceeding
- `cloneCodebase: true` is required on the CI stage — secret scanners need access to source code

## Troubleshooting

### Pipeline Not Found
- Verify `org_id` and `project_id` are correct
- Confirm the pipeline exists with `harness_list` (resource_type: "pipeline")
- This skill only works with existing pipelines

### Connector Not Found in Pipeline
- Verify the pipeline has a codebase configuration with a connector reference
- Check `pipeline.properties.ci.codebase.connectorRef` for v0 pipelines
- The pipeline must have a Git connector configured to enable secret scanning

### Scanner Step Fails
- Verify `cloneCodebase: true` is set on the CI stage — secret scanners need source code access
- Check that the Git connector has proper authentication configured
- Review execution logs via `harness_diagnose` for specific scanner errors

### Scanner Authentication Failure (commercial scanners)
- Verify `auth.access_token` (and `auth.access_id` where required) reference valid Harness secrets
- Confirm secret identifiers match exactly — check with `harness_get(resource_type="secret")`
- For Snyk and Semgrep: only `access_token` is needed
- For SonarQube, Checkmarx One, Wiz, Fossa: both `access_id` and `access_token` are required
- If secrets don't exist, create them first via `/create-secret`

### No Secret Results After Scan
- Verify STO module is enabled for the account
- Check scan output logs for errors or warnings
- Confirm the scanner's target configuration points to the correct repository
- Note: absence of results means no secrets were found — this is the desired outcome
