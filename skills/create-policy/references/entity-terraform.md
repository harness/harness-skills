# Terraform and Workspace Policies

---

## Terraform Plan

### Package: `terraform_plan`
### Root path: `input.planned_values`, `input.resource_changes`, `input.prior_state`
### Valid actions: `afterTerraformPlan`

### Schema

```
input.planned_values.root_module.resources[i].address
input.planned_values.root_module.resources[i].type        # "aws_instance", "aws_s3_bucket", etc.
input.planned_values.root_module.resources[i].name
input.planned_values.root_module.resources[i].values.ami
input.planned_values.root_module.resources[i].values.instance_type
input.planned_values.root_module.resources[i].values.tags          # object {"Name": "...", "Team": "..."}

input.resource_changes[i].address
input.resource_changes[i].type
input.resource_changes[i].change.actions[j]               # "create", "update", "delete", "no-op"
input.resource_changes[i].change.before                    # previous state values
input.resource_changes[i].change.after                     # planned state values
```

### Example: Enforce EC2 AMIs, instance types, and tags

```rego
package terraform_plan

allowed_amis = ["ami-0aa7d40eeae50c9a9"]
allowed_instance_types = ["t2.nano", "t2.micro"]
required_tags = ["Name", "Team"]

deny[sprintf("%s: ami %s is not allowed", [r.address, r.values.ami])] {
	r = input.planned_values.root_module.resources[_]
	r.type == "aws_instance"
	not contains(allowed_amis, r.values.ami)
}

deny[sprintf("%s: instance type %s is not allowed", [r.address, r.values.instance_type])] {
	r = input.planned_values.root_module.resources[_]
	r.type == "aws_instance"
	not contains(allowed_instance_types, r.values.instance_type)
}

deny[sprintf("%s: missing required tag '%s'", [r.address, required_tag])] {
	r = input.planned_values.root_module.resources[_]
	r.type == "aws_instance"
	existing_tags := [key | r.values.tags[key]]
	required_tag := required_tags[_]
	not contains(existing_tags, required_tag)
}

contains(arr, elem) {
	arr[_] = elem
}
```

---

## Terraform Plan Cost

### Package: `terraform_plan_cost`
### Root path: `input.TotalMonthlyCost`, etc.
### Valid actions: `afterTerraformPlan`

### Schema

```
input.TotalMonthlyCost                       # number
input.DiffTotalMonthlyCost                   # number
input.PercentageChangeTotalMonthlyCost       # number
```

### Example 1: Total cost cap

```rego
package terraform_plan_cost

deny[msg] {
  input.TotalMonthlyCost > 100
  msg := sprintf("Total monthly cost $%.2f exceeds the $100 budget", [input.TotalMonthlyCost])
}
```

### Example 2: Percentage increase cap

```rego
package terraform_plan_cost

deny[msg] {
  input.PercentageChangeTotalMonthlyCost > 10
  msg := sprintf("Cost increase of %.1f%% exceeds the 10%% threshold", [input.PercentageChangeTotalMonthlyCost])
}
```

---

## Terraform State

### Package: `terraform_state`
### Root path: `input.resources`
### Valid actions: `afterTerraformPlan`, `afterTerraformApply`

### Schema

```
input.resources[i].type                      # "aws_instance"
input.resources[i].name
input.resources[i].instances[j].attributes.ami
input.resources[i].instances[j].attributes.instance_type
input.resources[i].instances[j].attributes.tags         # object
```

### Example: Enforce EC2 constraints on state

```rego
package terraform_state

allowed_amis = ["ami-0aa7d40eeae50c9a9"]

deny[sprintf("instance %s uses disallowed AMI %s", [r.name, instance.attributes.ami])] {
  r = input.resources[_]
  r.type == "aws_instance"
  instance = r.instances[_]
  not contains(allowed_amis, instance.attributes.ami)
}

contains(arr, elem) {
  arr[_] = elem
}
```

---

## Workspace

### Package: `workspace`
### Root path: `input.workspace`
### Valid actions: `onsave`

### Schema

```
input.workspace.identifier
input.workspace.name
input.workspace.account
input.workspace.org
input.workspace.project
input.workspace.description
input.workspace.provisioner                  # "terraform"
input.workspace.provisioner_version          # "1.5.5"
input.workspace.repository
input.workspace.repository_branch
input.workspace.repository_path
input.workspace.repository_connector.identifier
input.workspace.repository_connector.type
input.workspace.repository_connector.spec.url
input.workspace.provider_connector.identifier
input.workspace.provider_connector.type
input.workspace.status
input.workspace.created
input.workspace.updated
```

### Example 1: Enforce minimum Terraform version

```rego
package workspace

deny[msg] {
  semver.compare(input.workspace.provisioner_version, "1.5.4") < 0
  msg := sprintf("workspace '%s' uses Terraform %s, minimum required is 1.5.4", [input.workspace.name, input.workspace.provisioner_version])
}
```

### Example 2: Restrict to approved connectors

```rego
package workspace

approved_connectors = ["approved_connector_1", "approved_connector_2"]

deny[msg] {
  connector := input.workspace.repository_connector.identifier
  not contains(approved_connectors, connector)
  msg := sprintf("workspace '%s' uses unapproved connector '%s'", [input.workspace.name, connector])
}

contains(arr, elem) {
  arr[_] = elem
}
```

### Example 3: Restrict repository organization

```rego
package workspace

approved_org = "github.com/my-org"

deny[msg] {
  url := input.workspace.repository_connector.spec.url
  not contains(url, approved_org)
  msg := sprintf("workspace '%s' repository must be from '%s'", [input.workspace.name, approved_org])
}
```

### Sample JSON

```json
{
  "workspace": {
    "identifier": "policy_as_code",
    "name": "test workspace",
    "account": "25NKDX79QPC",
    "org": "default",
    "project": "policy_as_code_testing",
    "provisioner": "terraform",
    "provisioner_version": "1.5.5",
    "repository": "test",
    "repository_branch": "main",
    "repository_connector": {},
    "repository_path": "test"
  }
}
```
