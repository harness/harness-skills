---
name: manage-iacm
description: >-
  Manage Harness Infrastructure as Code Management (IaCM) via MCP. Configure Terraform workspaces
  with remote state and RBAC, set up continuous drift detection with auto-remediation, design
  multi-tier change approval workflows, and estimate infrastructure costs before deployment.
  Use when asked to manage Terraform workspaces, detect infrastructure drift, set up approval
  workflows for infrastructure changes, or estimate Terraform costs. Do NOT use for creating
  Harness infrastructure definitions (use create-infrastructure instead) or OPA policies
  (use create-policy instead). Trigger phrases: terraform, workspace, drift detection,
  infrastructure cost, IaCM, state management, change approval, terraform plan, infracost,
  infrastructure governance.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Manage IaCM

Configure Terraform workspaces, drift detection, change approval workflows, and cost estimation in Harness Infrastructure as Code Management.

## Instructions

### Step 1: Establish Scope

Confirm the user's org, project, cloud provider, and environments.

```
Call MCP tool: harness_list
Parameters:
  resource_type: "project"
  org_id: "<organization>"
```

### Step 2: Identify the IaCM Task

Determine which workflow the user needs:

1. **Workspace and State Management** -- Workspace structure, remote state, RBAC, module registry
2. **Drift Detection** -- Continuous drift scanning with remediation workflows
3. **Change Approval Workflows** -- Risk-based approval tiers for infrastructure changes
4. **Cost Estimation** -- Pre-deployment cost impact analysis using Infracost

### Step 3: Configure Workspaces and State Management

Gather from the user:
- Cloud provider (AWS, GCP, Azure, multi-cloud)
- Environments to manage (dev, staging, prod)
- Workspace naming convention (e.g., {project}-{env}-{region})
- State backend preference (S3+DynamoDB, GCS+Firestore, Azure Blob, Harness built-in)

Design workspace structure:
- One workspace per environment per account
- Remote state backend with encryption at rest and state locking
- State backup with versioning and configurable retention
- RBAC: Developer=plan only, Senior Dev=plan+apply to dev, Team Lead=staging, DevOps=all with prod approval

Configure module registry:
- Semantic versioning for modules
- Security scanning before module publication (Checkov, tfsec, Terrascan)
- Approval workflow for new module versions

### Step 4: Set Up Drift Detection

Gather from the user:
- Environments to monitor
- Scan frequency (hourly, every 6 hours, daily)
- Resources to exclude from drift scanning

Configure drift detection:
- Compare actual cloud resources against Terraform state on schedule
- Detect additions, deletions, and modifications outside Terraform control
- Classify drift by severity: critical (security group changes, IAM), warning (tags, descriptions), info (metadata)

Remediation workflows:
- Auto-remediate low-risk drift (tag corrections, description updates)
- Alert and create ticket for medium-risk drift
- Page on-call for critical drift (security-related changes)

### Step 5: Design Change Approval Workflows

Gather risk categories from the user:
- Low risk (e.g., tag changes, scaling adjustments) -- auto-apply after peer review
- Medium risk (e.g., new resources, config changes) -- team lead approval
- High risk (e.g., security groups, IAM, database changes) -- security team + CAB approval
- Emergency (break-glass) -- post-implementation review required

```
Call MCP tool: harness_create
Parameters:
  resource_type: "pipeline"
  org_id: "<organization>"
  project_id: "<project>"
  body:
    pipeline:
      name: "terraform-change-approval"
      identifier: "terraform_change_approval"
      stages:
        - stage:
            name: Plan
            type: CI
            spec:
              # terraform plan + output change summary
        - stage:
            name: Cost Estimate
            type: CI
            spec:
              # infracost diff
        - stage:
            name: Approval
            type: Approval
            spec:
              # risk-based approval routing
        - stage:
            name: Apply
            type: CI
            spec:
              # terraform apply
```

### Step 6: Estimate Infrastructure Costs

When asked for cost estimation:
- Identify the workspace and pending Terraform changes (PR or plan output)
- Run Infracost analysis on the plan

Present a cost report with:
- Current monthly cost vs. projected monthly cost
- Per-resource cost breakdown for new/modified resources
- Cost optimization recommendations (right-sizing, reserved instances)
- Budget impact assessment

## Examples

- "Set up Terraform workspaces for our AWS environments" -- Configure workspace structure with state management and RBAC
- "Enable drift detection for production infrastructure" -- Set up scheduled scanning with severity classification and remediation
- "Create an approval workflow for infrastructure changes" -- Design risk-based approval tiers with security review for high-risk changes
- "How much will this Terraform change cost?" -- Run Infracost analysis and present cost impact report
- "Configure our Terraform module registry" -- Set up versioned module registry with security scanning

## Performance Notes

- Workspace naming conventions should be established early -- renaming workspaces requires state migration.
- Drift detection scans should avoid peak hours to minimize API rate limit conflicts.
- Cost estimation accuracy depends on Infracost having pricing data for all resource types in use.
- Change approval workflows should include a break-glass path for emergencies -- blocking all changes can be as dangerous as no controls.

## Troubleshooting

### State Locking Conflicts
- Check for stuck locks from failed runs -- use `terraform force-unlock` cautiously
- Verify the state backend (DynamoDB, Firestore) is accessible from the runner

### Drift Detection False Positives
- Exclude resources managed by auto-scaling groups or Kubernetes operators
- Add ignore rules for metadata fields that change frequently (last-modified timestamps)
- Verify the scan is running against the correct workspace/state file

### Cost Estimation Missing Resources
- Infracost may not support all resource types -- check supported resource list
- Ensure the Terraform plan output includes all changed resources
- Custom modules may need explicit cost annotations
