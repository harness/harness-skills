---
name: configure-repo-scan
description: >-
  Configure code scanning in Harness pipelines using STO security scanners. Helps identify where to inject
  SAST/SCA scanning steps into existing pipelines, recommends appropriate scanners, and configures them with
  proper connector references. Use when asked to add code scanning, configure security scans, set up SAST/SCA,
  integrate vulnerability scanning, or add security checks to a pipeline. Trigger phrases: add code scanner,
  configure repo scan, set up SAST, add security scan, configure vulnerability scanning, integrate scanner.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Configure Repo Scan

Add code scanning steps to existing Harness pipelines using STO security scanners.

## Instructions

### Step 1: Establish Scope and Pipeline Context

Ask the user for the organization, project, and pipeline identifier if not already known. This skill only works with existing pipelines.

Once you have the identifiers, fetch the pipeline definition:

```
Call MCP tool: harness_get
Parameters:
  resource_type: "pipeline"
  resource_id: "<pipeline_identifier>"
  org_id: "<organization>"
  project_id: "<project>"
```

### Step 2: Extract Repository Connector from Pipeline

Parse the pipeline YAML from Step 1 to automatically identify the repository connector used in the pipeline.

Look for the connector reference in the pipeline structure:
- For v0 pipelines: Check `pipeline.properties.ci.codebase.connectorRef`
- For v1 pipelines: Check the codebase connector in the pipeline configuration

If no connector is found in the pipeline, inform the user that the pipeline does not have a codebase configuration and cannot proceed with repo scanning.

### Step 3: Analyze Pipeline Structure

Parse the pipeline YAML from Step 1 to identify:
- All stages (CI, Deployment, Approval, Custom)
- All steps within each stage
- Existing security scanning steps (if any)

Present a structured view to the user showing:
```
Pipeline: <name>

Stage 1: <stage_name> (type: <stage_type>)
  - Step 1: <step_name> (type: <step_type>)
  - Step 2: <step_name> (type: <step_type>)
  ...

Stage 2: <stage_name> (type: <stage_type>)
  - Step 1: <step_name> (type: <step_type>)
  ...
```

Ask the user where they would like to insert the code scanner step:
- "Before which step?" or "After which step?" or "At the end of which stage?"
- Provide suggestions (e.g., "I recommend adding it after the build step but before deployment")

### Step 4: Recommend Scanner Type

Present the available SAST scanners supported in Harness STO:

**Available SAST Scanners:**
- **Harness Code** (default - native Harness scanner)
- Bandit (open-source, Python)
- Black Duck (by Synopsys)
- Brakeman (open-source, Ruby)
- Checkmarx
- Checkmarx One
- Coverity (open-source)
- CodeQL
- FOSSA
- GitHub Advanced Security
- Mend (formerly WhiteSource)
- Semgrep (open-source)
- Snyk
- SonarQube
- Veracode
- Wiz

**Default recommendation:** Use **Harness Code** as the native Harness SAST scanner. It provides integrated security scanning with minimal configuration and seamless integration with Harness STO.

Ask the user which scanner they prefer. If they don't specify, use Harness Code as the default.

### Step 5: Generate Scanner Step Configuration

Based on the scanner choice and connector from Step 2, generate the appropriate step YAML. The scanner step should be a native Harness STO step, not a Run step.

**For Harness Code (default):**

```yaml
- step:
    identifier: harness_code_scan
    name: Harness Code Scan
    type: HarnessSAST
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

**For Bandit (Python):**

```yaml
- step:
    identifier: bandit_scan
    name: Bandit SAST
    type: Bandit
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

**For Semgrep:**

```yaml
- step:
    identifier: semgrep_scan
    name: Semgrep SAST
    type: Semgrep
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

**For other scanners:** Reference `references/scanner-types.md` for scanner-specific configuration.

### Step 6: Insert Step into Pipeline YAML

Insert the generated scanner step YAML at the location chosen in Step 3. Ensure proper indentation and structure.

**Key rules:**
- Scanner steps should be added to CI stages (type: CI), not Deployment or Approval stages
- Scanner steps should typically run after code checkout but before deployment
- If the pipeline has a `cloneCodebase: true` setting, the scanner will have access to the source code
- The scanner step should be added to the `execution.steps` array within the chosen stage

Create the updated pipeline YAML with the scanner step inserted.

### Step 7: Update Pipeline via MCP

Update the pipeline with the new scanner step:

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

Report the results to the user:

```
## Code Scanner Configured

**Pipeline:** <pipeline_name>
**Scanner:** <scanner_type>
**Location:** Stage "<stage_name>", <position description>
**Connector:** <connector_name>

**Pipeline URL:** https://app.harness.io/ng/account/<account_id>/module/ci/orgs/<org_id>/projects/<project_id>/pipelines/<pipeline_id>/pipeline-studio/

**Note:** The scanner step has been configured with default settings. You can review and modify the configuration in the pipeline studio if you need to customize scan behavior, add exclusions, or adjust other parameters.

### Next Steps
1. Run the pipeline to verify the scanner step executes successfully
2. View scan results in the Security Tests tab of the execution
3. Configure exemptions for false positives via `/security-report` skill
4. Set up policies to fail pipelines on critical vulnerabilities via `/create-policy` skill
```

## Examples

### Add scanner to existing pipeline

```
/configure-repo-scan
I want to add code scanning to my backend-api pipeline in the platform project
```

### Configure SAST for Python project

```
/configure-repo-scan
Set up SAST scanning for my Python service. Use Bandit and add it after the test step.
```

### Add Harness Code scan to CI pipeline

```
/configure-repo-scan
Add Harness Code scanner to my CI pipeline. Scan after build but before pushing to registry.
```

## Performance Notes

- Always verify the pipeline exists before attempting to modify it
- Automatically extract the repository connector from the pipeline configuration instead of asking the user
- Parse the complete pipeline structure to provide accurate insertion point recommendations
- Use native STO scanner steps (Harness Code, Bandit, Semgrep, etc.) instead of Run steps with scanner CLI commands
- Default to Harness Code scanner unless the user has specific scanner preferences
- Ensure the scanner step is added to a CI stage with `cloneCodebase: true` so source code is available
- This skill only works with existing pipelines; do not offer to create new pipelines

## Troubleshooting

### Pipeline Not Found
- Verify org_id and project_id are correct
- Check RBAC permissions for pipeline access
- Confirm the pipeline exists with `harness_list` (resource_type: "pipeline")
- Inform the user that this skill only works with existing pipelines

### Connector Not Found in Pipeline
- Verify the pipeline has a codebase configuration with a connector reference
- Check `pipeline.properties.ci.codebase.connectorRef` for v0 pipelines
- Inform the user that the pipeline must have a codebase connector configured for repo scanning

### Scanner Step Fails
- Verify `cloneCodebase: true` is set on the CI stage
- Check that the connector has proper authentication configured
- Ensure the scanner image is accessible (registry permissions)
- Review execution logs via `harness_diagnose` for specific scanner errors

### Pipeline Update Validation Errors
- Verify YAML indentation is correct (use 2 spaces)
- Ensure step identifier follows pattern `^[a-zA-Z_][0-9a-zA-Z_]{0,127}$`
- Check that the step is added to a valid stage with proper `spec.execution.steps` structure
- Confirm the scanner type is a valid Harness STO step type

### No Security Results After Scan
- Verify STO module is enabled for the account
- Check scan output logs for errors or warnings
- Confirm scanner target configuration matches repository structure
- Ensure scanner has proper permissions to access dependencies
