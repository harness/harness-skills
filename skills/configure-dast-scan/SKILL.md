---
name: configure-dast-scan
description: >-
  Add Dynamic Application Security Testing (DAST) steps to existing Harness pipelines using Harness STO scanners.
  Supports API DAST / Traceable (default), Burp Suite Enterprise, ZAP (OWASP), Nikto, and Nmap.
  Scans running application instances for vulnerabilities including API security issues, injection flaws,
  misconfigurations, and exposed services. Can insert the scan step into an existing CI or SecurityTests stage
  or create a dedicated SecurityTests stage.
  Use when asked to add DAST scanning, configure dynamic application testing, set up API security scanning,
  scan a running application, or add runtime security testing to a pipeline.
  Trigger phrases: add DAST scan, dynamic application security testing, API DAST, configure Traceable,
  scan running app, add Burp Suite scan, add ZAP scan, add Nikto scan, runtime security scan, API security scan.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Configure DAST Scan

Add a Dynamic Application Security Testing (DAST) step to an existing Harness pipeline using Harness STO scanners. DAST scanners test running application instances for security vulnerabilities at runtime.

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

**Ask the user where they want the DAST scanner step added:**

Present the available insertion points:
- Any existing `SecurityTests` stage (scanner step is added into that stage's `execution.steps`)
- Any existing `CI` stage (scanner step is added directly into that stage's `execution.steps`)
- A new `SecurityTests` stage (appended to the pipeline)

**Recommendation guidance:**
- DAST scans run against a **live application instance** — they are best placed **after deployment** so the target is running
- If the pipeline has a Deployment stage, recommend adding a `SecurityTests` stage **after** the deployment stage
- If no deployment stage exists, the user must provide the target URL of an already-running instance
- Adding to an existing `SecurityTests` stage is simplest if one already exists

If the user doesn't specify, default to adding a new `SecurityTests` stage at the end of the pipeline (or after the Deployment stage if one exists).

### Step 3: Recommend Scanner Type

Present the available DAST scanners supported in Harness STO:

**Available DAST Scanners:**
- **API DAST (Traceable)** (default — Harness native API security scanner, formerly called Traceable)
- **Burp Suite Enterprise** (commercial, comprehensive web app DAST with crawl + audit)
- **ZAP** (OWASP Zed Attack Proxy, open-source web app scanner)
- **Nikto** (open-source, web server scanner)
- **Nmap** (open-source, network/port scanner with vulnerability scripts)

**Default recommendation:** Use **API DAST (Traceable)** — the Harness native DAST scanner for API security testing. It connects with your Traceable account to initiate scans against existing scan configurations, and results integrate directly with Harness STO.

Ask the user which scanner they prefer. If they don't specify, use API DAST (Traceable) as the default.

**Step type mapping and scanner auth requirements:**

| Scanner | `type` field | Product auth needed? | Auth fields |
|---------|-------------|----------------------|-------------|
| API DAST (Traceable) | `Traceable` | Yes | `domain` (Traceable platform URL), `access_token` (API token) |
| Burp Suite Enterprise | `BurpEnterprise` | Yes | `domain` (Burp Enterprise URL), `access_token` (API key) |
| ZAP | `Zap` | No | — |
| Nikto | `Nikto` | No | — |
| Nmap | `Nmap` | No | — |

**If the user picks a scanner that requires auth (API DAST, Burp Suite):**

1. Inform the user that scanner product credentials are required
2. Ask for the required secret references from the table above — these must already exist as Harness secrets
3. Format them as `<+secrets.getValue("project.<secret_identifier>")>`
4. These go into the `auth` block of the step spec

Example prompt to user:
> "API DAST (Traceable) requires a platform domain and access token. Please provide:
> 1. Your Traceable platform URL (e.g., `https://api.traceable.ai/`)
> 2. The Harness secret identifier for your Traceable API token (e.g., `traceable_api_token`). I'll reference it as `<+secrets.getValue("project.traceable_api_token")>`."

If the secret doesn't exist yet, suggest creating it first via `/create-secret` before proceeding.

### Step 4: Select Scan Mode (API DAST / Traceable only)

**This step applies only to API DAST (Traceable).** For other scanners (Burp Suite, ZAP, Nikto, Nmap), default to `orchestration` and skip to Step 5.

Present the three available scan modes and ask the user which one they want:

**Available Scan Modes:**

- **Orchestration** (default) — Triggers a new scan run within an existing Traceable Scan. Results are automatically saved in STO. Requires an active runner in Traceable.
- **Extraction** — Retrieves the latest scan results from an existing Traceable Scan and imports them into STO. No new scan is triggered — useful for pulling results from scans run on a schedule or externally.
- **Ingestion** — Reads scan results from a local JSON file and imports them into STO. The user must fetch results separately (e.g., via a Run step with Traceable API call). No Traceable credentials needed in the step itself.

If the user doesn't specify, default to **Orchestration**.

**Fields required per mode:**

| Field | Orchestration | Extraction | Ingestion |
|-------|:---:|:---:|:---:|
| Domain (Traceable URL) | Yes | Yes | No |
| Access Token | Yes | Yes | No |
| Scan Name (Suite ID) | Yes | Yes | No |
| Runner Selection | Optional | No | No |
| Ingestion File path | No | No | Yes |
| Target Name (manual) | No | No | Yes |
| Target Variant (manual) | No | No | Yes |

**For Ingestion mode**, inform the user they need a preceding **Run step** to fetch results from Traceable's API and save them as a JSON file. Example command for the Run step:

```
curl -H "Authorization: Bearer $API_TOKEN" \
  "https://api.traceable.ai/graphql/scans/$SCAN_ID/vulnerabilities" \
  -o /harness/vulnerabilities.json
```

The ingestion file path (e.g., `/harness/vulnerabilities.json`) must be configured as a shared path in the stage.

### Step 5: Collect Target Instance Details

DAST scans require a running application target. Collect different fields based on the scanner:

---

**For API DAST (Traceable):**

Traceable uses its own scan configurations managed in the Traceable platform. Collect based on the scan mode chosen in Step 4:

**Orchestration mode:**

| Field | Required | Description |
|-------|----------|-------------|
| Traceable Domain | Yes | Platform URL, e.g., `https://api.traceable.ai/` or `https://api-staging.traceable.ai/` |
| Access Token | Yes | Traceable API token (Harness secret reference) |
| Scan Name (Suite ID) | Yes | The Traceable Scan ID from the scan URL (e.g., `b35b11b4-3e87-47df-8c2e-a5ceb5ea764c`) |
| Runner Selection | No | `auto` (default) or manual Runner ID — runners must be active in Traceable |

**Extraction mode:**

| Field | Required | Description |
|-------|----------|-------------|
| Traceable Domain | Yes | Platform URL, e.g., `https://api.traceable.ai/` |
| Access Token | Yes | Traceable API token (Harness secret reference) |
| Scan Name (Suite ID) | Yes | The Traceable Scan ID to pull latest results from |

**Ingestion mode:**

| Field | Required | Description |
|-------|----------|-------------|
| Ingestion File | Yes | Path to the JSON results file, e.g., `/harness/vulnerabilities.json` |
| Target Name | Yes | Manual target identifier (e.g., `my-api-service`) |
| Target Variant | Yes | Manual variant label (e.g., `1.0.0` or `staging`) |

---

**For Burp Suite Enterprise:**

| Field | Required | Description |
|-------|----------|-------------|
| Burp Domain | Yes | Burp Enterprise server URL |
| Access Token | Yes | Burp API key (Harness secret reference) |
| Instance Domain | Yes | Target application URL, e.g., `https://myapp.io` |
| Instance Protocol | No | `https` (default) or `http` |
| Instance Port | No | TCP port (e.g., `443`, `8080`) |
| Instance Path | No | Path to append (e.g., `/api/v1`) |
| Scan Configuration | No | Default is `Crawl and audit lightweight`. See Step 5 for options |

---

**For ZAP, Nikto, Nmap (instance scanners):**

| Field | Required | Description |
|-------|----------|-------------|
| Instance Domain | Yes | Target application domain, e.g., `https://myapp.io` |
| Instance Protocol | No | `https` (default) or `http` |
| Instance Port | No | TCP port (e.g., `443`, `8080`, `3000`) |
| Instance Path | No | Path to append (e.g., `/portal/us`) |

---

### Step 6: Generate the Scanner Step YAML

Use the step `type` from the scanner mapping in Step 3.

**For API DAST / Traceable (default — Orchestration mode):**

```yaml
- step:
    type: Traceable
    name: API_DAST_Scan
    identifier: API_DAST_Scan
    spec:
      mode: orchestration
      config: default
      target:
        type: instance
        detection: auto
      auth:
        domain: <traceable_platform_url>
        access_token: <+secrets.getValue("project.traceable_api_token")>
      tool:
        suite_id: <traceable_scan_id>
      advanced:
        log:
          level: info
```

**For API DAST / Traceable (Extraction mode):**

```yaml
- step:
    type: Traceable
    name: API_DAST_Scan
    identifier: API_DAST_Scan
    spec:
      mode: extraction
      config: default
      target:
        type: instance
        detection: auto
      auth:
        domain: <traceable_platform_url>
        access_token: <+secrets.getValue("project.traceable_api_token")>
      tool:
        suite_id: <traceable_scan_id>
      advanced:
        log:
          level: info
```

**For API DAST / Traceable (Orchestration with manual runner):**

```yaml
- step:
    type: Traceable
    name: API_DAST_Scan
    identifier: API_DAST_Scan
    spec:
      mode: orchestration
      config: default
      target:
        type: instance
        detection: auto
      auth:
        domain: <traceable_platform_url>
        access_token: <+secrets.getValue("project.traceable_api_token")>
      tool:
        suite_id: <traceable_scan_id>
        runner_id: <traceable_runner_id>
      advanced:
        log:
          level: info
```

**For API DAST / Traceable (Ingestion mode):**

```yaml
- step:
    type: Traceable
    name: API_DAST_Scan
    identifier: API_DAST_Scan
    spec:
      mode: ingestion
      config: default
      target:
        type: instance
        name: <target_name>
        variant: <target_variant>
      ingestion:
        file: <ingestion_file_path>
      advanced:
        log:
          level: info
```

**For Burp Suite Enterprise (Orchestration mode):**

```yaml
- step:
    type: BurpEnterprise
    name: Burp_Suite_Scan
    identifier: Burp_Suite_Scan
    spec:
      mode: orchestration
      config: default
      target:
        type: instance
        detection: auto
      auth:
        domain: <burp_enterprise_url>
        access_token: <+secrets.getValue("project.burp_api_key")>
      instance:
        domain: <target_app_url>
        protocol: https
        port: <port>
        path: <path>
      advanced:
        log:
          level: info
```

**Burp Suite scan configuration options (for `config` field):**
- `default` (same as Crawl and Audit - Lightweight)
- `Never stop Crawl due to application errors`
- `Never stop audit due to application errors`
- `Minimize false positives`
- `Minimize false negatives`
- `Crawl strategy most complete`
- `Crawl strategy more complete`
- `Crawl strategy fastest`
- `Crawl strategy faster`
- `Crawl limit 60 minutes`
- `Crawl limit 30 minutes`
- `Crawl limit 10 minutes`
- `Crawl and audit lightweight`
- `Crawl and audit fast`
- `Crawl and audit deep`
- `Crawl and audit balanced`
- `Audit coverage thorough`
- `Audit coverage maximum`
- `Audit checks medium active`
- `Audit checks light active`
- `Audit checks critical issues only`
- `Audit checks all except time based detection methods`
- `Audit checks all except java script analysis`

**For ZAP (open-source):**

```yaml
- step:
    type: Zap
    name: ZAP_DAST_Scan
    identifier: ZAP_DAST_Scan
    spec:
      mode: orchestration
      config: default
      target:
        type: instance
        detection: auto
      instance:
        domain: <target_app_url>
        protocol: https
        port: <port>
        path: <path>
      advanced:
        log:
          level: info
```

**For Nikto (open-source):**

```yaml
- step:
    type: Nikto
    name: Nikto_DAST_Scan
    identifier: Nikto_DAST_Scan
    spec:
      mode: orchestration
      config: default
      target:
        type: instance
        detection: auto
      instance:
        domain: <target_app_url>
        protocol: https
        port: <port>
        path: <path>
      advanced:
        log:
          level: info
```

**For Nmap (open-source network scanner):**

```yaml
- step:
    type: Nmap
    name: Nmap_Scan
    identifier: Nmap_Scan
    spec:
      mode: orchestration
      config: default
      target:
        type: instance
        detection: auto
      instance:
        domain: <target_app_url>
        protocol: https
        port: <port>
        path: <path>
      advanced:
        log:
          level: info
```

**Nmap scan configuration options:**
- `default` (common port scan with scripts)
- `No Default CLI Flags` (blank slate for custom flags)
- `Firewall Bypass`
- `Unusual Port`
- `SMB Security Mode`
- `Vuln`
- `Exploit`

### Step 7: Collect Infrastructure Details (if needed)

**Only required when adding a new `SecurityTests` stage.** If inserting into an existing stage, skip this step.

Ask the user for their infrastructure type:

**Option A — Harness Cloud (recommended for simplicity):**

```yaml
platform:
  os: Linux
  arch: Amd64
runtime:
  type: Cloud
  spec: {}
```

**Option B — Kubernetes Direct:**

Ask for:
- **Delegate connector** (e.g., `account.mydelegate`)
- **Namespace** (e.g., `harness-delegate-ng`)

```yaml
infrastructure:
  type: KubernetesDirect
  spec:
    connectorRef: <delegate_connector>
    namespace: <namespace>
    automountServiceAccountToken: true
    nodeSelector: {}
    os: Linux
```

If the user doesn't specify, default to Harness Cloud infrastructure.

### Step 8: Build the Updated Pipeline YAML

**Scenario A — Adding to an existing `SecurityTests` or `CI` stage:**

Insert the step into `spec.execution.steps` of the chosen stage. The stage already has its own infrastructure. Just append the step.

**Scenario B — Creating a new `SecurityTests` stage (Harness Cloud):**

```yaml
- stage:
    name: DAST Scan
    identifier: DAST_Scan_Stage
    type: SecurityTests
    spec:
      cloneCodebase: false
      platform:
        os: Linux
        arch: Amd64
      runtime:
        type: Cloud
        spec: {}
      execution:
        steps:
          - step:
              type: Traceable
              name: API_DAST_Scan
              identifier: API_DAST_Scan
              spec:
                mode: orchestration
                config: default
                target:
                  type: instance
                  detection: auto
                auth:
                  domain: <traceable_platform_url>
                  access_token: <+secrets.getValue("project.traceable_api_token")>
                tool:
                  suite_id: <traceable_scan_id>
                advanced:
                  log:
                    level: info
```

**Scenario C — Creating a new `SecurityTests` stage (Kubernetes Direct):**

```yaml
- stage:
    name: DAST Scan
    identifier: DAST_Scan_Stage
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
              type: Traceable
              name: API_DAST_Scan
              identifier: API_DAST_Scan
              spec:
                mode: orchestration
                config: default
                target:
                  type: instance
                  detection: auto
                auth:
                  domain: <traceable_platform_url>
                  access_token: <+secrets.getValue("project.traceable_api_token")>
                tool:
                  suite_id: <traceable_scan_id>
                advanced:
                  log:
                    level: info
```

### Step 9: Update Pipeline via MCP

```
Call MCP tool: harness_update
Parameters:
  resource_type: "pipeline"
  resource_id: "<pipeline_identifier>"
  org_id: "<organization>"
  project_id: "<project>"
  body: { yamlPipeline: "<updated pipeline YAML string>" }
```

### Step 10: Provide Summary and Next Steps

```
## DAST Scanner Configured

**Pipeline:** <pipeline_name>
**Scanner:** <scanner_name> (<scanner_type>)
**Stage:** <stage_name> (SecurityTests)
**Target:** <target_instance_url_or_scan_name>
**Mode:** <orchestration | extraction | ingestion>

**Pipeline URL:** https://app.harness.io/ng/account/<account_id>/module/sto/orgs/<org_id>/projects/<project_id>/pipelines/<pipeline_id>/pipeline-studio/

### Next Steps
1. Run the pipeline to verify the DAST scan step executes successfully
2. View scan results in the Security Tests tab of the execution
3. Set failure thresholds using `fail_on_severity` (CRITICAL, HIGH, MEDIUM, LOW) in the step's Advanced tab
4. Configure exemptions for false positives via `/security-report` skill
5. Enforce pipeline gates on severity via `/create-policy` skill
```

## Examples

### Add API DAST scan with Traceable (orchestration)

```
/configure-dast-scan
Add an API DAST scan to my backend-deploy pipeline. My Traceable domain is https://api.traceable.ai/ and the scan ID is b35b11b4-3e87-47df-8c2e-a5ceb5ea764c.
```

### Add Traceable in extraction mode

```
/configure-dast-scan
I want to pull the latest DAST results from my Traceable scan into STO. Use extraction mode.
The scan ID is abc123-def456 and my Traceable token secret is traceable_token.
```

### Add Burp Suite Enterprise scan

```
/configure-dast-scan
Add Burp Suite Enterprise scanning to my pipeline targeting https://staging.myapp.io:8443/api.
Use the "Crawl and audit deep" configuration for thorough coverage.
```

### Add ZAP scan after deployment

```
/configure-dast-scan
Add a ZAP DAST scan after the deployment stage in my frontend-deploy pipeline.
Target the deployed app at https://staging.example.com
```

### Add Nikto web server scan

```
/configure-dast-scan
Add Nikto scanning to check my web server at https://myapp.io:443 for common vulnerabilities.
Add it to the existing SecurityTests stage.
```

### Add Nmap network scan

```
/configure-dast-scan
Add an Nmap vulnerability scan against my service at 10.0.1.50 port 8080.
Use the Vuln scan configuration.
```

## Performance Notes

- Only works with **existing pipelines** — do not offer to create a new standalone pipeline
- Always ask the user which scanner they want — present the full list; default to **API DAST (Traceable)** if not specified
- DAST scans target **running application instances** — they do NOT need source code access, so `cloneCodebase: false` is always set on SecurityTests stages
- Place DAST scans **after deployment stages** when possible — the target application must be running and accessible
- For API DAST (Traceable), the scan must already exist in the Traceable platform — orchestration mode initiates a run of an existing scan, it cannot create new scans
- For Traceable orchestration mode, ensure runners are created and active in Traceable — the step cannot create runners
- For commercial scanners (API DAST, Burp Suite), always ask for scanner product credentials (`auth.domain` / `auth.access_token`) before generating YAML
- If required secrets don't exist yet, prompt the user to create them via `/create-secret` before proceeding
- For ZAP, Nikto, and Nmap, no product auth is needed — only the target instance details
- Default to `mode: orchestration` and `config: default` unless the user specifies otherwise
- Default to `target.detection: auto` — this sets the target name from the scan and variant from the timestamp
- Default to Harness Cloud infrastructure for new SecurityTests stages unless the user specifies Kubernetes Direct
- Nmap is primarily a network scanner — recommend it for port/service discovery and network-level vulnerabilities, not application-layer DAST
- Burp Suite provides the most comprehensive web application DAST with crawl + audit capabilities

## Troubleshooting

### Pipeline Not Found
- Verify `org_id` and `project_id` are correct
- Confirm the pipeline exists with `harness_list` (resource_type: "pipeline")

### API DAST (Traceable) Scan Fails to Start
- Verify the Scan ID (`suite_id`) is correct — find it in the Traceable scan URL
- Ensure the Traceable access token is valid and has permissions to trigger scans
- For orchestration mode: confirm runners are active in Traceable — the step cannot create runners
- Verify the Traceable domain URL is correct (e.g., `https://api.traceable.ai/` vs `https://api-staging.traceable.ai/`)

### Burp Suite Authentication Failure
- Verify `auth.domain` points to your Burp Enterprise server URL
- Confirm `auth.access_token` references a valid Harness secret containing the Burp API key
- Ensure the Burp Enterprise server is reachable from the pipeline infrastructure

### Target Instance Unreachable
- Verify the instance domain, protocol, and port are correct
- Ensure the target application is running and accessible from the pipeline infrastructure (delegate or Harness Cloud)
- For internal/private applications, ensure the delegate has network connectivity to the target
- Check firewall rules and security groups allow traffic from the scanner to the target

### Scanner Authentication Failure (commercial scanners)
- Verify `auth.access_token` (and `auth.domain`) reference valid Harness secrets
- Confirm the secret identifiers match exactly — check with `harness_get(resource_type="secret")`
- If secrets don't exist, create them first via `/create-secret` then re-run the skill

### No Results in Security Tests Tab
- Confirm STO module is enabled for the account
- Check the execution logs for scanner errors
- For API DAST (Traceable): verify the scan completed successfully in the Traceable platform
- For Burp Suite: ensure the crawl completed — very large applications may time out with restrictive crawl limits

### Pipeline Update Validation Errors
- Verify YAML indentation (2 spaces throughout)
- Ensure step `identifier` matches pattern `^[a-zA-Z_][0-9a-zA-Z_]{0,127}$`
- Confirm the `SecurityTests` stage has a valid infrastructure block (Harness Cloud or KubernetesDirect with a working delegate)
- Ensure `cloneCodebase: false` is set on SecurityTests stages (DAST does not need source code)
