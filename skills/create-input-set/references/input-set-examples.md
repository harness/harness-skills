# Input Set YAML Examples

## CD Pipeline Input Set

```yaml
inputSet:
  identifier: deploy_staging
  name: Deploy to Staging
  orgIdentifier: default
  projectIdentifier: my_project
  pipeline:
    identifier: deploy_pipeline
    variables:
      - name: environment
        type: String
        value: staging
      - name: image_tag
        type: String
        value: <+trigger.artifact.build>
    stages:
      - stage:
          identifier: deploy
          type: Deployment
          spec:
            environment:
              environmentRef: staging
              infrastructureDefinitions:
                - identifier: k8s_staging
```

## CI Pipeline Input Set

```yaml
inputSet:
  identifier: ci_main_branch
  name: CI Main Branch
  orgIdentifier: default
  projectIdentifier: my_project
  pipeline:
    identifier: ci_pipeline
    properties:
      ci:
        codebase:
          build:
            type: branch
            spec:
              branch: main
    stages:
      - stage:
          identifier: build
          type: CI
          spec:
            execution:
              steps:
                - step:
                    identifier: build_image
                    type: BuildAndPushDockerRegistry
                    spec:
                      tags:
                        - latest
                        - <+pipeline.sequenceId>
```

## Overlay Input Set

```yaml
overlayInputSet:
  identifier: staging_with_canary
  name: Staging with Canary
  description: Combines staging inputs with canary deployment config
  orgIdentifier: default
  projectIdentifier: my_project
  pipeline:
    identifier: deploy_pipeline
  inputSetReferences:
    - base_config       # Applied first
    - staging_env       # Applied second (overrides base)
    - canary_config     # Applied third (overrides previous)
  tags:
    type: overlay
```

Reference order matters -- later input sets override values from earlier ones.

## Layered Input Set Strategy

Structure input sets in layers for maximum reusability:

| Layer | Purpose | Example Identifier |
|-------|---------|-------------------|
| Base | Common configuration (logging, monitoring) | `base_config` |
| Environment | Environment-specific values (env ref, replicas) | `staging_env` |
| Feature | Feature flags and options (canary %, blue-green) | `canary_enabled` |
| Release | Version-specific artifacts (image tag, version) | `release_v2_0_0` |

Combine with an overlay:

```yaml
overlayInputSet:
  identifier: staging_canary_v2
  name: Staging Canary v2.0.0
  pipeline:
    identifier: deploy_pipeline
  inputSetReferences:
    - base_config
    - staging_env
    - canary_enabled
    - release_v2_0_0
```
