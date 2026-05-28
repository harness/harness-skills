# CD Deployment Stage — Artifact Signing (not supported)

Use with `/sign-artifact` when the user asks about **Deploy** stage placement.

## Current Harness limitation

Per [Harness docs](https://developer.harness.io/docs/software-supply-chain-assurance/artifact-security/sign-verify/sign-artifacts),
**artifact signing in the Deployment stage is not supported today** (roadmap item).

**Do not** append signing steps to CD Deploy stages. Instead:

1. Place `SscaArtifactSigning` in the **CI** stage immediately after build/push.
2. Verify signatures in CI or via `SscaArtifactVerification` before deploy.
3. Use `/manage-supply-chain` or SBOM enforcement (`SscaOrchestration`) for deploy-time supply chain gates.

## If Deploy support is added later

Signing in Deploy stages would follow the same **containerized step group** pattern as SBOM enforcement
and SLSA verification — inside `stepGroup.steps` with `stepGroupInfra`, not top-level
`execution.steps`. Mirror `skills/verify-sign/references/cd-containerized-step-group.md` with
`SscaArtifactSigning` substituted for the step type.
