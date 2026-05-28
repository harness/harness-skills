---
name: manage-supply-chain
description: >-
  Manage Harness Software Supply Chain Assurance (SSCA) via MCP. Configure automated SBOM
  generation with CycloneDX or SPDX formats, set up artifact signing and attestation with
  Cosign, define supply chain security policies using OPA, and track SLSA provenance levels.
  Use when asked to generate SBOMs, sign artifacts, enforce supply chain policies, track
  software provenance, or manage SLSA compliance. Do NOT use for OPA pipeline governance
  policies (use create-policy instead) or vulnerability scanning (use security-report instead).
  Trigger phrases: SBOM, software bill of materials, supply chain security, SLSA, artifact
  signing, cosign, provenance, attestation, CycloneDX, SPDX, supply chain policy.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Manage Supply Chain

Configure SBOM generation, artifact signing, supply chain policy enforcement, and SLSA provenance tracking in Harness SSCA.

## Instructions

### Step 1: Establish Scope

Confirm the user's org, project, service, and build tool.

```
Call MCP tool: harness_list
Parameters:
  resource_type: "project"
  org_id: "<organization>"
```

### Step 2: Identify the SSCA Task

Determine which workflow the user needs:

1. **SBOM Generation** -- Automated SBOM creation on every build with signing and attestation
2. **Supply Chain Policy Enforcement** -- OPA policies for artifact provenance, signing, and compliance

### Step 3: Configure SBOM Generation

Gather from the user:
- Service name, build tool, and language
- Pipeline to attach SBOM generation to
- SBOM format: CycloneDX 1.5 (JSON) or SPDX 2.3 (JSON)
- SBOM scope: direct dependencies, transitive, or full (OS + language + transitive)
- Signing key provider: Cosign keyless (Sigstore), Cosign with KMS, AWS KMS, GCP KMS

Configure SBOM generation in the CI pipeline:
- Trigger on every successful build or container push
- Generate SBOM in the selected format
- Sign SBOM with the configured key provider
- Attach as OCI artifact alongside the container image
- Require valid signature verification before deployment to protected environments

**Supply Chain Risk Analysis:**
- Flag dependencies with known CVEs above CVSS threshold (default 7.0)
- Detect license conflicts (e.g., GPL-3.0, AGPL-3.0)
- Flag dependencies outdated by more than N months
- Flag dependencies from untrusted registries

**Compliance Mapping:**
- Target SLSA level (Level 1, 2, or 3)
- Map to compliance frameworks: NIST SSDF, EO 14028, SOC2

### Step 4: Configure Supply Chain Policy Enforcement

Gather enforcement points from the user (build, push, deploy, or all stages).

Define OPA policies:
1. **Artifact Provenance** -- Require all container images to have valid Cosign signatures
2. **SLSA Level** -- Enforce minimum SLSA level for production deployments
3. **SBOM Requirements** -- Block deployment if SBOM is missing or unsigned
4. **Dependency Restrictions** -- Block artifacts with banned licenses or known malicious packages
5. **Registry Allowlist** -- Only allow artifacts from approved registries

```
Call MCP tool: harness_create
Parameters:
  resource_type: "policy"
  org_id: "<organization>"
  project_id: "<project>"
  body:
    name: "supply-chain-enforcement"
    identifier: "supply_chain_enforcement"
    rego: |
      package harness.supply_chain

      deny[msg] {
        not input.artifact.signed
        msg := "Artifact must be signed with Cosign before deployment"
      }

      deny[msg] {
        not input.artifact.sbom_attached
        msg := "SBOM must be generated and attached to artifact"
      }
```

### Step 5: Set Up SBOM Storage and Dashboards

Configure SBOM storage:
- Store in Harness AR alongside the image, or in S3/GCS/Dependency-Track
- Set retention period (default 365 days)

Enable the SSCA portal dashboard for:
- Real-time component inventory across all services
- Vulnerability trends over time
- License compliance status
- SLSA level tracking per service

## Examples

- "Generate SBOMs for our payment-service builds" -- Configure CycloneDX SBOM generation with Cosign signing in the CI pipeline
- "Enforce artifact signing for production deployments" -- Create OPA policy requiring valid Cosign signatures
- "Set up SLSA Level 2 compliance tracking" -- Configure provenance tracking and SBOM attestation
- "Block deployments with GPL-3.0 dependencies" -- Create supply chain policy with license restrictions
- "Track our software supply chain risk" -- Enable SSCA dashboard with CVE, license, and staleness analysis

## Performance Notes

- SBOM generation adds 10-30 seconds to the build depending on dependency count -- acceptable for most pipelines.
- Cosign keyless signing (Sigstore) is simpler to set up than KMS-backed keys but requires internet access.
- SLSA Level 3 requires hermetic builds -- this may require significant pipeline restructuring.
- SBOM storage costs are minimal (JSON files) but retention policies prevent unbounded growth.

## Troubleshooting

### SBOM Generation Failing
- Verify the build tool is supported by the SBOM generator (Syft, Trivy, cdxgen)
- Check that the container image is accessible at the point SBOM generation runs
- For monorepos, ensure the SBOM scope is set to the correct subdirectory

### Cosign Signing Errors
- For keyless: verify the OIDC provider (Sigstore/Fulcio) is reachable
- For KMS: verify the service account has signing permissions on the key
- Check that the Cosign binary version is compatible with the image format

### Policy Blocking Deployments
- Check which specific policy rule is triggering the deny
- Use the exemption workflow for known false positives
- Verify the policy is evaluating the correct input fields from the pipeline
