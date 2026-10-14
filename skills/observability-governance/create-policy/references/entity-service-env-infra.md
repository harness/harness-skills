# Service, Environment, Infrastructure Policies

---

## Service

### Package: `service`
### Root path: `input.serviceEntity`
### Valid actions: `onsave`, `onrun`

### Schema

```
input.serviceEntity.identifier
input.serviceEntity.name
input.serviceEntity.orgIdentifier
input.serviceEntity.projectIdentifier
input.serviceEntity.serviceDefinition.type                     # "Kubernetes", "NativeHelm", "Ssh", "WinRm", "ServerlessAwsLambda", "AzureWebApp", "ECS", "Elastigroup", "CustomDeployment", "TAS", "Asg", "GoogleCloudFunctions", "AwsLambda", "GoogleCloudRun", "AwsSam", "AzureFunctions"
input.serviceEntity.serviceDefinition.spec.release.name
input.serviceEntity.serviceDefinition.spec.variables[i].name
input.serviceEntity.serviceDefinition.spec.variables[i].type   # "String"
input.serviceEntity.serviceDefinition.spec.variables[i].value
input.serviceEntity.serviceDefinition.spec.variables[i].description
input.serviceEntity.serviceDefinition.spec.variables[i].required
input.serviceEntity.serviceDefinition.spec.manifests[i].manifest.spec.store.type  # "Git", "Github", "S3", etc.
input.serviceEntity.serviceDefinition.spec.manifests[i].manifest.spec.store.spec.branch
```

### Example 1: Block deployment type and name prefix

```rego
package service

deny[msg] {
  input.serviceEntity.serviceDefinition.type == "Kubernetes"
  msg := "Service with Kubernetes deployment type is not allowed"
}

deny[msg] {
  startswith(input.serviceEntity.name, "BLOCKED_SERVICE_NAME")
  msg := "Service which starts with BLOCKED_SERVICE_NAME prefix is not allowed"
}
```

### Example 2: Block GitHub manifest store

```rego
package service

deny[msg] {
  input.serviceEntity.serviceDefinition.spec.manifests[_].manifest.spec.store.type == "Github"
  msg := "Service manifest store type Github is not allowed"
}
```

### Sample JSON

```json
{
  "serviceEntity": {
    "identifier": "demo",
    "name": "demo",
    "orgIdentifier": "demo",
    "projectIdentifier": "demo",
    "serviceDefinition": {
      "type": "Asg",
      "spec": {
        "release": { "name": "release-<+INFRA_KEY_SHORT_ID>" },
        "variables": [
          { "name": "variable", "type": "String", "value": "value", "description": "Variable description" }
        ]
      }
    }
  }
}
```

---

## Environment

### Package: `environment` or `env`
### Root path: `input.environmentEntity`
### Valid actions: `onsave`, `onrun`

### Schema

```
input.environmentEntity.identifier
input.environmentEntity.name
input.environmentEntity.orgIdentifier
input.environmentEntity.projectIdentifier
input.environmentEntity.type                     # "Production", "PreProduction"
input.environmentEntity.tags                     # object {}
input.environmentEntity.variables[i].name
input.environmentEntity.variables[i].type        # "String"
input.environmentEntity.variables[i].value
input.environmentEntity.variables[i].description
input.environmentEntity.variables[i].required
```

### Example: Block production type with empty variable descriptions

```rego
package env

deny[msg] {
  input.environmentEntity.type == "Production"
  msg := "Environment with Production type is not allowed"
}

deny[msg] {
  some i
  input.environmentEntity.variables[i].description == ""
  msg := sprintf("Environment variable '%s' must have a description", [input.environmentEntity.variables[i].name])
}
```

### Sample JSON

```json
{
  "environmentEntity": {
    "identifier": "demo",
    "name": "demo",
    "type": "PreProduction",
    "variables": [
      { "name": "variable", "type": "String", "value": "value", "description": "description" }
    ]
  }
}
```

---

## Infrastructure

### Package: `infra`
### Root path: `input.infrastructureEntity`
### Valid actions: `onsave`, `onrun`

### Schema

```
input.infrastructureEntity.identifier
input.infrastructureEntity.name
input.infrastructureEntity.orgIdentifier
input.infrastructureEntity.projectIdentifier
input.infrastructureEntity.description
input.infrastructureEntity.deploymentType        # "Kubernetes", "NativeHelm", "Ssh", "WinRm", "ECS", "Serverless", "Asg", "CustomDeployment", "Elastigroup", "TAS", "AzureWebApp", "GoogleCloudFunctions", "AwsLambda", "GoogleCloudRun", "AwsSam", "AzureFunctions"
input.infrastructureEntity.environmentRef
input.infrastructureEntity.type                  # "KubernetesDirect", "KubernetesGcp", "KubernetesAzure", "KubernetesAws", "KubernetesRancher", "Pdc", "SshWinRmAws", "SshWinRmAzure", "ServerlessAwsLambda", "ECS", "Elastigroup", "TAS", "Asg", "GoogleCloudFunctions", "GoogleCloudRun", "AzureWebApp", "AWS_SAM", "AwsLambda", "CustomDeployment"
input.infrastructureEntity.allowSimultaneousDeployments
input.infrastructureEntity.spec.connectorRef
input.infrastructureEntity.spec.namespace
input.infrastructureEntity.spec.releaseName
```

### Example: Deny runtime inputs for connector or namespace

```rego
package infra

deny[msg] {
  input.infrastructureEntity.spec.connectorRef == "<+input>"
  msg := "Runtime input is not allowed for connector"
}

deny[msg] {
  input.infrastructureEntity.spec.namespace == "<+input>"
  msg := "Runtime input is not allowed for namespace"
}
```

### Sample JSON

```json
{
  "infrastructureEntity": {
    "identifier": "demo",
    "name": "demo",
    "deploymentType": "Kubernetes",
    "environmentRef": "demo",
    "type": "KubernetesDirect",
    "spec": {
      "connectorRef": "demo",
      "namespace": "namespace",
      "releaseName": "release-<+INFRA_KEY_SHORT_ID>"
    }
  }
}
```
