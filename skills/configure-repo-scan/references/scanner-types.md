# Security Scanner Types

This reference lists all Harness STO SAST scanner steps with their configuration examples.

## SAST (Static Application Security Testing)

### Harness Code (Recommended - Default)

Native Harness SAST scanner with seamless STO integration.

```yaml
- step:
    identifier: harness_code_scan
    name: Harness Code Scan
    type: HarnessSAST
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

**Best for:** Native Harness integration, multi-language projects, minimal configuration
**Supports:** SAST with integrated STO reporting

### Bandit (Python - Open Source)

Python-specific SAST scanner.

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
        name: <repository_name>
        variant: <+codebase.branch>
      advanced:
        log:
          level: info
```

**Best for:** Python projects
**Supports:** Python SAST

### Black Duck (by Synopsys)

Enterprise SCA with comprehensive vulnerability and license detection.

```yaml
- step:
    identifier: blackduck_scan
    name: Black Duck SCA
    type: BlackDuck
    spec:
      mode: orchestration
      config: default
      target:
        type: repository
        name: <repository_name>
        variant: <+codebase.branch>
      advanced:
        log:
          level: info
```

**Best for:** Enterprise license compliance, deep dependency analysis
**Supports:** SCA, license compliance

### Brakeman (Ruby - Open Source)

Ruby on Rails security scanner.

```yaml
- step:
    identifier: brakeman_scan
    name: Brakeman SAST
    type: Brakeman
    spec:
      mode: orchestration
      config: default
      target:
        type: repository
        name: <repository_name>
        variant: <+codebase.branch>
      advanced:
        log:
          level: info
```

**Best for:** Ruby on Rails applications
**Supports:** Ruby SAST

### Checkmarx

Enterprise-grade SAST for large codebases.

```yaml
- step:
    identifier: checkmarx_scan
    name: Checkmarx SAST
    type: Checkmarx
    spec:
      mode: orchestration
      config: default
      target:
        type: repository
        name: <repository_name>
        variant: <+codebase.branch>
      advanced:
        log:
          level: info
```

**Best for:** Enterprise Java/.NET applications
**Supports:** SAST with compliance reporting

### Checkmarx One

Next-generation Checkmarx platform with unified security testing.

```yaml
- step:
    identifier: checkmarx_one_scan
    name: Checkmarx One SAST
    type: CheckmarxOne
    spec:
      mode: orchestration
      config: default
      target:
        type: repository
        name: <repository_name>
        variant: <+codebase.branch>
      advanced:
        log:
          level: info
```

**Best for:** Enterprise unified security testing
**Supports:** SAST, SCA, IaC scanning

### Coverity (Open Source)

Static analysis tool for C, C++, Java, and other languages.

```yaml
- step:
    identifier: coverity_scan
    name: Coverity SAST
    type: Coverity
    spec:
      mode: orchestration
      config: default
      target:
        type: repository
        name: <repository_name>
        variant: <+codebase.branch>
      advanced:
        log:
          level: info
```

**Best for:** C/C++, Java static analysis
**Supports:** SAST with deep code analysis

### CodeQL

GitHub's semantic code analysis engine.

```yaml
- step:
    identifier: codeql_scan
    name: CodeQL Scan
    type: CodeQL
    spec:
      mode: orchestration
      config: default
      target:
        type: repository
        name: <repository_name>
        variant: <+codebase.branch>
      advanced:
        log:
          level: info
```

**Best for:** Deep semantic analysis, GitHub integration
**Supports:** Multi-language SAST

### FOSSA

License compliance and dependency analysis.

```yaml
- step:
    identifier: fossa_scan
    name: FOSSA Scan
    type: Fossa
    spec:
      mode: orchestration
      config: default
      target:
        type: repository
        name: <repository_name>
        variant: <+codebase.branch>
      advanced:
        log:
          level: info
```

**Best for:** License compliance automation
**Supports:** SCA, license compliance, policy enforcement

### GitHub Advanced Security

GitHub's native security scanning platform.

```yaml
- step:
    identifier: ghas_scan
    name: GitHub Advanced Security
    type: GHAS
    spec:
      mode: orchestration
      config: default
      target:
        type: repository
        name: <repository_name>
        variant: <+codebase.branch>
      advanced:
        log:
          level: info
```

**Best for:** GitHub enterprise security
**Supports:** SAST, secret scanning, dependency scanning

### Mend (formerly WhiteSource)

Open source security and license compliance management.

```yaml
- step:
    identifier: mend_scan
    name: Mend SCA
    type: Mend
    spec:
      mode: orchestration
      config: default
      target:
        type: repository
        name: <repository_name>
        variant: <+codebase.branch>
      advanced:
        log:
          level: info
```

**Best for:** Open source license compliance, vulnerability management
**Supports:** SCA, license compliance

### Semgrep (Open Source)

Fast, customizable SAST scanner with extensive rule sets.

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
        name: <repository_name>
        variant: <+codebase.branch>
      advanced:
        log:
          level: info
```

**Best for:** JavaScript, Python, Java, Go, Ruby
**Supports:** SAST with customizable rules

### Snyk

Developer-friendly security scanner with fix recommendations.

```yaml
- step:
    identifier: snyk_scan
    name: Snyk Scan
    type: Snyk
    spec:
      mode: orchestration
      config: default
      target:
        type: repository
        name: <repository_name>
        variant: <+codebase.branch>
      advanced:
        log:
          level: info
```

**Best for:** JavaScript, Python, Java, .NET, Go, Ruby
**Supports:** SAST, SCA, container scanning, license compliance

### SonarQube

Comprehensive code quality and security scanner with detailed reporting.

```yaml
- step:
    identifier: sonarqube_scan
    name: SonarQube Scan
    type: Sonarqube
    spec:
      mode: orchestration
      config: default
      target:
        type: repository
        name: <repository_name>
        variant: <+codebase.branch>
      advanced:
        log:
          level: info
```

**Best for:** Enterprise projects requiring code quality + security
**Supports:** SAST, code smells, technical debt, coverage

### Veracode

Enterprise application security platform.

```yaml
- step:
    identifier: veracode_scan
    name: Veracode Scan
    type: Veracode
    spec:
      mode: orchestration
      config: default
      target:
        type: repository
        name: <repository_name>
        variant: <+codebase.branch>
      advanced:
        log:
          level: info
```

**Best for:** Enterprise SAST, SCA, and compliance
**Supports:** Static, dynamic, and mobile app security

### Wiz

Cloud security posture management and application security.

```yaml
- step:
    identifier: wiz_scan
    name: Wiz Scan
    type: Wiz
    spec:
      mode: orchestration
      config: default
      target:
        type: repository
        name: <repository_name>
        variant: <+codebase.branch>
      advanced:
        log:
          level: info
```

**Best for:** Cloud-native security, SAST, SCA, container scanning
**Supports:** SAST, SCA, container, VM, and cloud configuration scanning

## Scanner Selection Guide

| Use Case | Primary Scanner | Alternative |
|----------|----------------|-------------|
| Default/Multi-language | **Harness Code** | Semgrep, Snyk |
| Python projects | Bandit | Harness Code, Semgrep |
| Ruby on Rails | Brakeman | Harness Code |
| JavaScript/TypeScript | Semgrep | Harness Code, Snyk |
| Java/Spring Boot | SonarQube | Checkmarx, Harness Code |
| .NET applications | Checkmarx | SonarQube, Harness Code |
| Go projects | Semgrep | Harness Code, Snyk |
| Enterprise compliance | Checkmarx + Black Duck | Veracode |
| License compliance | Black Duck | FOSSA, Mend |
| GitHub integration | GitHub Advanced Security | CodeQL |
| Cloud-native security | Wiz | Snyk |

## Configuration Notes

### Target Types

- `repository`: Source code scanning (SAST, SCA, secrets)
- `container`: Container image scanning
- `instance`: Running application (DAST)
- `configuration`: Cloud/infrastructure configuration

### Mode Options

- `orchestration`: Harness manages scanner execution (recommended)
- `ingestion`: Import scan results from external scanner runs
- `extraction`: Extract and normalize existing scan data

### Variant Field

Use expressions for dynamic variant values:
- `<+codebase.branch>`: Current branch name
- `<+pipeline.sequenceId>`: Build number
- `<+trigger.commitSha>`: Commit SHA
- `main`, `develop`, `staging`: Static branch/environment names
