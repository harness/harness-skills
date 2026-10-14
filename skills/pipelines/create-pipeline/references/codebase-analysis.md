# Codebase Analysis for Pipeline Generation

Before generating a pipeline, analyze the user's codebase to detect language, build tools, test frameworks, deployment targets, and manifest types. This produces the right CI steps, CD stages, and Harness service type automatically.

## Step 1: Detect Language and Runtime

| File | Language | Build Command | Base Image |
|------|----------|--------------|------------|
| `package.json` | Node.js | `npm ci && npm run build` | `node:<version>` |
| `package.json` (with `next`, `remix`, `nuxt`) | Node.js (SSR framework) | `npm ci && npm run build` | `node:<version>` |
| `go.mod` | Go | `go build ./...` | `golang:<version>` |
| `requirements.txt` / `pyproject.toml` / `Pipfile` | Python | `pip install -r requirements.txt` | `python:<version>` |
| `pom.xml` | Java (Maven) | `mvn clean package` | `maven:<version>` |
| `build.gradle` / `build.gradle.kts` | Java/Kotlin (Gradle) | `gradle build` | `gradle:<version>` |
| `Cargo.toml` | Rust | `cargo build --release` | `rust:<version>` |
| `*.csproj` / `*.sln` | .NET | `dotnet build` / `dotnet publish` | `mcr.microsoft.com/dotnet/sdk:<version>` |
| `Gemfile` | Ruby | `bundle install` | `ruby:<version>` |
| `mix.exs` | Elixir | `mix deps.get && mix compile` | `elixir:<version>` |
| `composer.json` | PHP | `composer install` | `php:<version>` |

### Version Detection

Extract the runtime version from:
- `package.json` → `engines.node`
- `go.mod` → `go` directive
- `pyproject.toml` → `requires-python` or `python_requires`
- `pom.xml` → `maven.compiler.source`
- `Cargo.toml` → `rust-version`
- `.tool-versions` → asdf version manager
- `.node-version`, `.python-version`, `.ruby-version`, `.go-version`

## Step 2: Detect Build and Test Tools

### Build Tools

| File | Tool | Build Step |
|------|------|-----------|
| `Makefile` | Make | `make build` |
| `Dockerfile` | Docker | BuildAndPushDockerRegistry step |
| `docker-compose.yml` | Docker Compose | `docker compose build` |
| `webpack.config.js` | Webpack | `npx webpack` |
| `vite.config.*` | Vite | `npm run build` |
| `tsconfig.json` | TypeScript | `npx tsc` |
| `Taskfile.yml` | Task | `task build` |
| `justfile` | Just | `just build` |
| `bazel` / `BUILD` | Bazel | `bazel build //...` |

### Test Frameworks

| File / Dependency | Framework | Test Command | Report Format |
|-------------------|-----------|-------------|---------------|
| `jest.config.*` or `jest` in package.json | Jest | `npx jest --ci` | JUnit (`--reporters=jest-junit`) |
| `vitest` in package.json | Vitest | `npx vitest run` | JUnit |
| `.mocharc.*` or `mocha` in package.json | Mocha | `npx mocha` | JUnit (`mocha-junit-reporter`) |
| `*_test.go` files | Go test | `go test ./... -v` | JUnit (`go-junit-report`) |
| `pytest.ini` / `conftest.py` / `pyproject.toml [tool.pytest]` | pytest | `pytest --junitxml=report.xml` | JUnit |
| `pom.xml` (surefire) | JUnit/TestNG | `mvn test` | JUnit (built-in) |
| `build.gradle` | JUnit/TestNG | `gradle test` | JUnit (built-in) |
| `*.test.rs` / `#[cfg(test)]` | Rust test | `cargo test` | JUnit (`cargo2junit`) |
| `*_test.rb` / `spec/` | RSpec/Minitest | `bundle exec rspec --format RspecJunitFormatter` | JUnit |

### Linting

| File | Linter | Lint Command |
|------|--------|-------------|
| `.eslintrc*` / `eslint.config.*` | ESLint | `npx eslint .` |
| `biome.json` | Biome | `npx biome check .` |
| `.pylintrc` / `pyproject.toml [tool.pylint]` | Pylint | `pylint src/` |
| `pyproject.toml [tool.ruff]` / `ruff.toml` | Ruff | `ruff check .` |
| `.golangci.yml` | golangci-lint | `golangci-lint run` |
| `.rubocop.yml` | RuboCop | `rubocop` |
| `clippy` in Cargo.toml | Clippy | `cargo clippy` |

### Code Formatting

| File | Formatter | Check Command |
|------|-----------|--------------|
| `.prettierrc*` | Prettier | `npx prettier --check .` |
| `biome.json` | Biome | `npx biome format --check .` |
| `pyproject.toml [tool.black]` | Black | `black --check .` |
| `rustfmt.toml` | rustfmt | `cargo fmt --check` |

## Step 3: Detect Containerization

| File | Type | Pipeline Step |
|------|------|--------------|
| `Dockerfile` | Docker build | `BuildAndPushDockerRegistry` (or ECR/GCR/ACR variant) |
| `Dockerfile.*` (e.g., `Dockerfile.prod`) | Multi-stage / env-specific | Use the appropriate Dockerfile |
| `.dockerignore` | Docker context optimization | Confirms Docker usage |
| `docker-compose.yml` | Multi-container | May need Background steps for dependencies |
| `Containerfile` | Podman/OCI | Same as Dockerfile |

### Registry Detection

| File / Config | Registry | Step Type |
|--------------|----------|-----------|
| Docker Hub reference in Dockerfile | Docker Hub | `BuildAndPushDockerRegistry` |
| `*.dkr.ecr.*.amazonaws.com` | AWS ECR | `BuildAndPushECR` |
| `gcr.io` / `*-docker.pkg.dev` | GCR / Google Artifact Registry | `BuildAndPushGCR` / `BuildAndPushGAR` |
| `*.azurecr.io` | Azure ACR | `BuildAndPushACR` |

## Step 4: Detect Deployment Target and Harness Service Type

### Kubernetes Manifests → `Kubernetes` service type

| File / Directory | Manifest Type | Harness Manifest Type |
|-----------------|---------------|----------------------|
| `k8s/`, `kubernetes/`, `manifests/`, `deploy/` with `*.yaml` | Raw K8s YAML | `K8sManifest` |
| `kustomization.yaml` / `kustomize/` | Kustomize | `Kustomize` |
| `Chart.yaml` / `charts/` / `helm/` | Helm chart | → Use `NativeHelm` service type instead |
| `values.yaml`, `values-*.yaml` | Helm values | `Values` (with Helm or K8s) |

### Helm Charts → `NativeHelm` service type

| File | Signal | Harness Manifest Type |
|------|--------|----------------------|
| `Chart.yaml` in repo root or `charts/` | Helm chart source | `HelmChart` |
| `values.yaml` + `templates/` | Helm chart structure | `HelmChart` |
| `helmfile.yaml` | Helmfile | `HelmChart` (use chart references) |

### ECS → `ECS` service type

| File | Signal | Harness Manifest Type |
|------|--------|----------------------|
| `task-definition.json` / `taskdef.json` | ECS task definition | `EcsTaskDefinition` |
| `service-definition.json` / `servicedef.json` | ECS service definition | `EcsServiceDefinition` |
| `appspec.yaml` (with ECS hooks) | ECS CodeDeploy | `EcsTaskDefinition` |

### Serverless → `ServerlessAwsLambda` service type

| File | Signal | Harness Manifest Type |
|------|--------|----------------------|
| `serverless.yml` / `serverless.ts` | Serverless Framework | `ServerlessAwsLambda` |
| `template.yaml` (SAM) | AWS SAM | `ServerlessAwsLambda` |
| `function.json` (Azure) | Azure Functions | → `AzureWebApp` service type |

### Azure → `AzureWebApp` service type

| File | Signal |
|------|--------|
| `azure-pipelines.yml` | Azure DevOps (migration candidate) |
| `host.json` + `function.json` | Azure Functions |
| `web.config` / `appsettings.json` | Azure Web App |

### SSH/WinRM → `Ssh` or `WinRm` service type

| Signal | Type |
|--------|------|
| No container/K8s/cloud manifests, traditional app (JAR, WAR, ZIP) | `Ssh` |
| `.NET` app targeting Windows, IIS config | `WinRm` |

## Step 5: Detect Existing CI/CD for Migration

| File | Source CI/CD | Migration Notes |
|------|-------------|----------------|
| `.github/workflows/*.yml` | GitHub Actions | Map `jobs` → stages, `steps` → steps, `uses` → plugins |
| `Jenkinsfile` | Jenkins | Map `stage` → stages, `sh` → Run steps |
| `.gitlab-ci.yml` | GitLab CI | Map `stages`/`jobs` → stages/steps |
| `.circleci/config.yml` | CircleCI | Map `jobs`/`workflows` → stages |
| `azure-pipelines.yml` | Azure DevOps | Map `stages`/`jobs`/`steps` → Harness equivalents |
| `bitbucket-pipelines.yml` | Bitbucket Pipelines | Map `pipelines.default` → stages |
| `.travis.yml` | Travis CI | Map `script` → Run steps |
| `buildkite.yml` / `.buildkite/` | Buildkite | Map `steps` → stages/steps |

## Step 6: Detect Security Scanning

| File / Dependency | Scanner | Pipeline Step |
|-------------------|---------|---------------|
| `.snyk` / `snyk` in dependencies | Snyk | Security scan step |
| `.trivyignore` / `trivy.yaml` | Trivy | Container scan step |
| `sonar-project.properties` | SonarQube | Code quality step |
| `.checkov.yml` | Checkov | IaC scan step |
| `CODEOWNERS` | Code ownership | Approval step reference |

## Service Type Decision Tree

```
Has Dockerfile?
├─ Yes → Container-based deployment
│  ├─ Has Chart.yaml/helm/ → NativeHelm
│  ├─ Has k8s/kustomization.yaml → Kubernetes
│  ├─ Has task-definition.json → ECS
│  ├─ Has serverless.yml → ServerlessAwsLambda
│  └─ Default → Kubernetes (most common)
└─ No
   ├─ Has serverless.yml/template.yaml → ServerlessAwsLambda
   ├─ Has task-definition.json → ECS
   ├─ Has function.json (Azure) → AzureWebApp
   ├─ .NET + Windows target → WinRm
   ├─ JAR/WAR output + no K8s → Ssh
   └─ Default → Kubernetes (assume containerization will be added)
```

## Putting It All Together

After analysis, generate:

1. **CI Stage** with steps in this order:
   - Install dependencies (language-specific)
   - Lint (if linter config found)
   - Test (if test framework found, with JUnit reports)
   - Build (compile/package)
   - Docker build and push (if Dockerfile found)

2. **CD Stage** with:
   - `deploymentType` matching the detected service type
   - `serviceRef` pointing to a service with the correct manifest type
   - Appropriate deploy steps (K8sRollingDeploy, HelmDeploy, EcsRollingDeploy, etc.)

3. **Service definition** with:
   - `type` from the decision tree above
   - `artifacts.primary` matching the detected registry
   - `manifests` matching the detected manifest type and paths
