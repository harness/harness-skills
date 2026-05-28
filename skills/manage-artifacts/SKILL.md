---
name: manage-artifacts
description: >-
  Manage Harness Artifact Registry (AR) via MCP. Configure private registries for Docker, Helm,
  Maven, npm, and PyPI artifacts, set up upstream proxies for caching public images, configure
  RBAC and cross-region replication, and define security scanning policies with CVE thresholds
  and license compliance checks. Use when asked to set up an artifact registry, configure Docker
  or Helm repositories, manage artifact security scanning, or set up replication. Do NOT use
  for creating connectors to external registries (use create-connector instead). Trigger phrases:
  artifact registry, docker registry, helm repository, artifact security, image scanning,
  private registry, artifact replication, CVE threshold, license compliance, SBOM.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Manage Artifacts

Configure private artifact registries, security scanning policies, and cross-region replication in Harness Artifact Registry.

## Instructions

### Step 1: Establish Scope

Confirm the user's org, project, and artifact format requirements.

```
Call MCP tool: harness_list
Parameters:
  resource_type: "project"
  org_id: "<organization>"
```

### Step 2: Identify the AR Task

Determine which workflow the user needs:

1. **Private Registry Setup** -- Docker, Helm, Maven, npm, PyPI repositories with RBAC
2. **Security Scanning Policy** -- Vulnerability scanning with CVE thresholds and license checks

### Step 3: Configure Private Registry

Gather from the user:
- Artifact formats to support (Docker, Helm, Maven, npm, PyPI)
- Upstream proxy preferences (Docker Hub, ECR Public, GCR)
- Image signing requirements (Cosign, Notary, none)
- Multi-architecture support needs

**Docker Registry:**
- Repository name and upstream proxy configuration
- Image signing with Cosign or Notary v2
- Multi-arch support (amd64 + arm64)

**Helm Chart Repository:**
- Chart validation on push
- Dependency resolution enabled

**Additional Formats (Maven, npm, PyPI):**
- Separate repositories per format
- Snapshot/release policies
- Upstream proxies for public registries

**Access Controls:**
- Read access: all developers in the org scope
- Push access: CI/CD service accounts only (no personal credentials)
- Admin: platform team
- LDAP/SAML integration with identity provider

**Replication:**
- Primary region with replication to secondary regions
- Configurable sync interval (real-time, 15 minutes, hourly, daily)

### Step 4: Configure Security Scanning Policies

Gather from the user:
- Artifact types to scan
- Security scanner (Aqua Trivy, Snyk, Grype, Prisma Cloud)
- CVE severity thresholds (block on CRITICAL and HIGH above N)

Configure scanning policies:
- Scan on push and periodic rescans for stored artifacts
- Block download if critical or high CVE count exceeds thresholds
- License compliance: block artifacts with disallowed licenses (GPL-3.0, AGPL)
- SBOM generation: auto-generate CycloneDX or SPDX on every scan
- Exemption workflow: security team can approve specific CVEs with expiry dates

```
Call MCP tool: harness_create
Parameters:
  resource_type: "pipeline"
  org_id: "<organization>"
  project_id: "<project>"
  body:
    pipeline:
      name: "artifact-security-scan"
      identifier: "artifact_security_scan"
      stages:
        - stage:
            name: Scan
            type: SecurityTests
            spec:
              # vulnerability scanning step
        - stage:
            name: Policy Gate
            type: Approval
            spec:
              # block if thresholds exceeded
```

## Examples

- "Set up a private Docker registry for our team" -- Configure Docker repository with upstream proxy and RBAC
- "Add Helm chart repository to our artifact registry" -- Configure Helm repo with chart validation
- "Configure vulnerability scanning for our container images" -- Set up scanning with CVE thresholds and license checks
- "Set up cross-region replication for our artifacts" -- Configure primary and replica regions with sync interval
- "Block images with critical CVEs from being deployed" -- Create security scanning policy with severity gates

## Performance Notes

- Upstream proxies significantly reduce build times by caching public images locally -- enable for all formats.
- Security scanning on push adds latency to the push operation -- consider async scanning for large images.
- Cross-region replication increases storage costs linearly -- only replicate to regions where artifacts are consumed.
- Image signing adds a verification step to every pull -- ensure signing infrastructure is highly available.

## Troubleshooting

### Push Rejected by Security Policy
- Check the scan results for specific CVEs that triggered the block
- Use the exemption workflow to approve known false positives
- Verify the CVE threshold is not set too low for the artifact's dependency tree

### Replication Lag
- Check network connectivity between primary and replica regions
- Verify the sync interval is appropriate for the artifact volume
- Large artifacts (multi-GB images) may need a longer sync window

### Registry Authentication Failures
- Verify the service account has push permissions in the target repository
- Check that LDAP/SAML integration is syncing correctly
- Ensure Docker login credentials are not expired
