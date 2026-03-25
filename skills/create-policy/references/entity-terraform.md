# Terraform and Workspace Policies

---

## Terraform Plan

### Package: `terraform_plan`
### Root path: `input.planned_values`, `input.resource_changes`, `input.configuration`, `input.metadata`, `input.iacmMetadata`
### Valid actions: `afterTerraformPlan`

### Schema

```
# Planned values — resources with resolved attribute values
input.planned_values.root_module.resources[i].address            # e.g. "aws_instance.ec2test1"
input.planned_values.root_module.resources[i].type               # "aws_instance", "aws_s3_bucket", etc.
input.planned_values.root_module.resources[i].name               # resource name
input.planned_values.root_module.resources[i].mode               # "managed"
input.planned_values.root_module.resources[i].provider_name      # e.g. "registry.terraform.io/hashicorp/aws"
input.planned_values.root_module.resources[i].values.ami
input.planned_values.root_module.resources[i].values.instance_type
input.planned_values.root_module.resources[i].values.tags        # object {"Name": "...", "Team": "..."}
input.planned_values.root_module.resources[i].values.tags_all

# Planned outputs
input.planned_values.outputs.<output_name>.value
input.planned_values.outputs.<output_name>.sensitive             # boolean

# Resource changes — what will be created/updated/deleted
input.resource_changes[i].address
input.resource_changes[i].type
input.resource_changes[i].name
input.resource_changes[i].mode                                   # "managed"
input.resource_changes[i].change.actions[j]                      # "create", "update", "delete", "no-op"
input.resource_changes[i].change.before                          # previous state values (null for create)
input.resource_changes[i].change.after                           # planned state values (null for delete)

# Configuration — source expressions and provider config
input.configuration.provider_config.<provider>.name
input.configuration.provider_config.<provider>.full_name
input.configuration.provider_config.<provider>.version_constraint
input.configuration.provider_config.<provider>.expressions.region.constant_value
input.configuration.root_module.resources[i].address
input.configuration.root_module.resources[i].type
input.configuration.root_module.variables.<var_name>.description
input.configuration.root_module.variables.<var_name>.default

# Variables — resolved variable values
input.variables.<var_name>.value

# Output changes
input.output_changes.<output_name>.actions[j]                    # "create", "update", "delete"
input.output_changes.<output_name>.after
input.output_changes.<output_name>.before

# Prior state
input.prior_state.terraform_version
input.prior_state.values.root_module

# IACM metadata
input.iacmMetadata.account
input.iacmMetadata.org
input.iacmMetadata.project
input.iacmMetadata.workspace
input.iacmMetadata.pipelineExecutionID

# Standard metadata
input.metadata.action                                            # "afterTerraformPlan"
input.metadata.type                                              # "terraformPlan"
input.metadata.timestamp
input.metadata.principalIdentifier
input.metadata.principalType
input.metadata.projectMetadata.identifier
input.metadata.projectMetadata.orgIdentifier

# Top-level fields
input.terraform_version                                          # e.g. "1.5.6"
input.format_version                                             # e.g. "1.2"
input.timestamp                                                  # ISO 8601
```

### Example 1: Enforce EC2 AMIs, instance types, and tags

```rego
package terraform_plan

allowed_amis = ["ami-0aa7d40eeae50c9a9"]
allowed_instance_types = ["t2.nano", "t2.micro"]
required_tags = ["Name", "Team"]

deny[sprintf("%s: ami %s is not allowed", [r.address, r.values.ami])] {
	r = input.planned_values.root_module.resources[_]
	r.type == "aws_instance"
	not array_contains(allowed_amis, r.values.ami)
}

deny[sprintf("%s: instance type %s is not allowed", [r.address, r.values.instance_type])] {
	r = input.planned_values.root_module.resources[_]
	r.type == "aws_instance"
	not array_contains(allowed_instance_types, r.values.instance_type)
}

deny[sprintf("%s: missing required tag '%s'", [r.address, required_tag])] {
	r = input.planned_values.root_module.resources[_]
	r.type == "aws_instance"
	existing_tags := [key | r.values.tags[key]]
	required_tag := required_tags[_]
	not array_contains(existing_tags, required_tag)
}

array_contains(arr, elem) {
	arr[_] = elem
}
```

### Example 2: Deny deletion of resources

```rego
package terraform_plan

deny[msg] {
	rc := input.resource_changes[_]
	rc.change.actions[_] == "delete"
	msg := sprintf("Deleting resource '%s' of type '%s' is not allowed", [rc.address, rc.type])
}
```

### Example 3: Restrict AWS provider region

```rego
package terraform_plan

allowed_regions = ["us-east-1", "us-west-2"]

deny[msg] {
	region := input.configuration.provider_config.aws.expressions.region.constant_value
	not array_contains(allowed_regions, region)
	msg := sprintf("AWS region '%s' is not allowed. Allowed: %v", [region, allowed_regions])
}

array_contains(arr, elem) {
	arr[_] = elem
}
```

### Example 4: Enforce minimum Terraform version

```rego
package terraform_plan

deny[msg] {
	semver.compare(input.terraform_version, "1.5.0") < 0
	msg := sprintf("Terraform version %s is below minimum required 1.5.0", [input.terraform_version])
}
```

### Example 5: Restrict resource types that can be created

```rego
package terraform_plan

forbidden_resource_types = ["aws_iam_user", "aws_iam_access_key"]

deny[msg] {
	rc := input.resource_changes[_]
	rc.change.actions[_] == "create"
	array_contains(forbidden_resource_types, rc.type)
	msg := sprintf("Creating resource type '%s' is not allowed (%s)", [rc.type, rc.address])
}

array_contains(arr, elem) {
	arr[_] = elem
}
```

### Sample JSON

```json
{
  "configuration": {
    "provider_config": {
      "aws": {
        "expressions": { "region": { "constant_value": "us-east-1" } },
        "full_name": "registry.terraform.io/hashicorp/aws",
        "name": "aws",
        "version_constraint": "~> 4.16"
      }
    },
    "root_module": {
      "resources": [
        {
          "address": "aws_instance.ec2test1",
          "expressions": {
            "ami": { "constant_value": "ami-0aa7d40eeae50c9a9" },
            "instance_type": { "references": ["var.instance_type"] }
          },
          "mode": "managed",
          "name": "ec2test1",
          "type": "aws_instance"
        }
      ],
      "variables": {
        "instance_type": {},
        "bucket_name": { "description": "Name of the s3 bucket. Must be unique." }
      }
    }
  },
  "format_version": "1.2",
  "iacmMetadata": {
    "account": "l7HREAyVTnyfUsfUtPZUow",
    "org": "default",
    "project": "Testim",
    "workspace": "verifyPipeline",
    "pipelineExecutionID": "zojGbuFsRi-ymnk4cmrwTg"
  },
  "metadata": {
    "action": "afterTerraformPlan",
    "principalIdentifier": "SERVICE",
    "principalType": "SERVICE",
    "projectMetadata": {
      "identifier": "Testim",
      "name": "Testim",
      "orgIdentifier": "default"
    },
    "timestamp": 1774465034,
    "type": "terraformPlan"
  },
  "planned_values": {
    "outputs": {
      "instance_type": { "sensitive": false, "type": "string", "value": "t2.micro" }
    },
    "root_module": {
      "resources": [
        {
          "address": "aws_instance.ec2test1",
          "mode": "managed",
          "name": "ec2test1",
          "provider_name": "registry.terraform.io/hashicorp/aws",
          "type": "aws_instance",
          "values": {
            "ami": "ami-0aa7d40eeae50c9a9",
            "instance_type": "t2.micro",
            "tags": { "extra": "I am from the git", "name": "ec2test1" },
            "tags_all": { "extra": "I am from the git", "name": "ec2test1" }
          }
        },
        {
          "address": "aws_s3_bucket.s3_bucket",
          "mode": "managed",
          "name": "s3_bucket",
          "type": "aws_s3_bucket",
          "values": { "bucket_prefix": "test65", "force_destroy": false }
        }
      ]
    }
  },
  "resource_changes": [
    {
      "address": "aws_instance.ec2test1",
      "change": {
        "actions": ["create"],
        "after": {
          "ami": "ami-0aa7d40eeae50c9a9",
          "instance_type": "t2.micro",
          "tags": { "extra": "I am from the git", "name": "ec2test1" }
        },
        "before": null
      },
      "mode": "managed",
      "name": "ec2test1",
      "type": "aws_instance"
    }
  ],
  "terraform_version": "1.5.6",
  "timestamp": "2026-03-25T18:57:04Z",
  "variables": {
    "instance_type": { "value": "t2.micro" },
    "bucket_name": { "value": "test65" }
  }
}
```

---

## Terraform Plan Cost

### Package: `terraform_plan_cost`
### Root path: `input` (flat structure with cost fields, `input.Diff`, `input.metadata`, `input.iacmMetadata`)
### Valid actions: `afterTerraformPlan`

### Schema

```
# Top-level cost summary
input.TotalMonthlyCost                                           # string e.g. "9.27"
input.PastTotalMonthlyCost                                       # string e.g. "0.00"
input.DiffTotalMonthlyCost                                       # string e.g. "9.27"
input.PercentageChangeTotalMonthlyCost                           # number e.g. 100
input.Currency                                                   # "USD"

# Per-resource-type cost breakdown
input.Diff.<resource_type>.CurrentMonthlyCost                    # string e.g. "9.27"
input.Diff.<resource_type>.PreviousMonthlyCost                   # string
input.Diff.<resource_type>.DiffMonthlyCost                       # string
input.Diff.<resource_type>.PercentageChangeMonthlyCost           # number

# Per-resource instance cost breakdown
input.Diff.<resource_type>.Diff[i].Name                          # e.g. "aws_instance.ec2test1"
input.Diff.<resource_type>.Diff[i].CurrentMonthlyCost            # string
input.Diff.<resource_type>.Diff[i].PreviousMonthlyCost           # string
input.Diff.<resource_type>.Diff[i].DiffMonthlyCost               # string
input.Diff.<resource_type>.Diff[i].PercentageChangeMonthlyCost   # number

# Per-resource subresource cost breakdown
input.Diff.<resource_type>.Diff[i].Subresources.<subresource_name>.CurrentMonthlyCost
input.Diff.<resource_type>.Diff[i].Subresources.<subresource_name>.PreviousMonthlyCost
input.Diff.<resource_type>.Diff[i].Subresources.<subresource_name>.DiffMonthlyCost
input.Diff.<resource_type>.Diff[i].Subresources.<subresource_name>.PercentageChangeMonthlyCost

# IACM metadata
input.iacmMetadata.account
input.iacmMetadata.org
input.iacmMetadata.project
input.iacmMetadata.workspace
input.iacmMetadata.pipelineExecutionID

# Standard metadata
input.metadata.action                                            # "afterTerraformPlan"
input.metadata.type                                              # "terraformPlanCost"
input.metadata.timestamp
input.metadata.principalIdentifier
input.metadata.principalType
input.metadata.projectMetadata.identifier
input.metadata.projectMetadata.orgIdentifier
```

**NOTE:** Cost values (`TotalMonthlyCost`, `DiffTotalMonthlyCost`, etc.) are **strings**, not numbers. Use `to_number()` to compare them numerically.

### Example 1: Total cost cap

```rego
package terraform_plan_cost

deny[msg] {
  to_number(input.TotalMonthlyCost) > 100
  msg := sprintf("Total monthly cost $%s exceeds the $100 budget", [input.TotalMonthlyCost])
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

### Example 3: Cap cost per resource type

```rego
package terraform_plan_cost

max_cost_per_type = 50

deny[msg] {
  cost_info := input.Diff[resource_type]
  to_number(cost_info.CurrentMonthlyCost) > max_cost_per_type
  msg := sprintf("Resource type '%s' monthly cost $%s exceeds $%d limit", [resource_type, cost_info.CurrentMonthlyCost, max_cost_per_type])
}
```

### Example 4: Deny cost increases on specific resource types

```rego
package terraform_plan_cost

restricted_types = ["aws_instance", "aws_rds_cluster"]

deny[msg] {
  cost_info := input.Diff[resource_type]
  array_contains(restricted_types, resource_type)
  to_number(cost_info.DiffMonthlyCost) > 0
  msg := sprintf("Cost increase of $%s for restricted resource type '%s' requires approval", [cost_info.DiffMonthlyCost, resource_type])
}

array_contains(arr, elem) {
  arr[_] = elem
}
```

### Sample JSON

```json
{
  "Currency": "USD",
  "Diff": {
    "aws_instance": {
      "CurrentMonthlyCost": "9.27",
      "DiffMonthlyCost": "9.27",
      "PercentageChangeMonthlyCost": 100,
      "PreviousMonthlyCost": "0.00",
      "Diff": [
        {
          "CurrentMonthlyCost": "9.27",
          "DiffMonthlyCost": "9.27",
          "Name": "aws_instance.ec2test1",
          "PercentageChangeMonthlyCost": 100,
          "PreviousMonthlyCost": "0.00",
          "Subresources": {
            "Instance usage (Linux/UNIX, on-demand, t2.micro)": {
              "CurrentMonthlyCost": "8.47",
              "DiffMonthlyCost": "8.47",
              "PercentageChangeMonthlyCost": 100,
              "PreviousMonthlyCost": "0.00"
            },
            "root_block_device": {
              "CurrentMonthlyCost": "0.80",
              "DiffMonthlyCost": "0.80",
              "PercentageChangeMonthlyCost": 100,
              "PreviousMonthlyCost": "0.00"
            }
          }
        }
      ]
    },
    "aws_s3_bucket": {
      "CurrentMonthlyCost": "0.00",
      "DiffMonthlyCost": "0.00",
      "PercentageChangeMonthlyCost": 0,
      "PreviousMonthlyCost": "0.00",
      "Diff": [
        {
          "CurrentMonthlyCost": "0.00",
          "DiffMonthlyCost": "0.00",
          "Name": "aws_s3_bucket.s3_bucket",
          "PercentageChangeMonthlyCost": 0,
          "PreviousMonthlyCost": "0.00"
        }
      ]
    }
  },
  "DiffTotalMonthlyCost": "9.27",
  "PastTotalMonthlyCost": "0.00",
  "PercentageChangeTotalMonthlyCost": 100,
  "TotalMonthlyCost": "9.27",
  "iacmMetadata": {
    "account": "l7HREAyVTnyfUsfUtPZUow",
    "org": "default",
    "project": "Testim",
    "workspace": "verifyPipeline",
    "pipelineExecutionID": "vlPq8vxjRLiPQQcYnxLytQ"
  },
  "metadata": {
    "action": "afterTerraformPlan",
    "principalIdentifier": "SERVICE",
    "principalType": "SERVICE",
    "projectMetadata": {
      "identifier": "Testim",
      "name": "Testim",
      "orgIdentifier": "default"
    },
    "timestamp": 1774464734,
    "type": "terraformPlanCost"
  }
}
```

---

## Terraform State

### Package: `terraform_state`
### Root path: `input.resources`, `input.outputs`, `input.metadata`, `input.iacmMetadata`
### Valid actions: `afterTerraformPlan`, `afterTerraformApply`

### Schema

```
# Resources and their instances
input.resources[i].type                                          # "aws_instance", "aws_s3_bucket", etc.
input.resources[i].name                                          # resource name e.g. "ec2test1"
input.resources[i].mode                                          # "managed"
input.resources[i].provider                                      # e.g. "provider[\"registry.terraform.io/hashicorp/aws\"]"

# Instance attributes (full resolved state)
input.resources[i].instances[j].attributes.ami
input.resources[i].instances[j].attributes.instance_type
input.resources[i].instances[j].attributes.instance_state        # "running", "stopped", etc.
input.resources[i].instances[j].attributes.tags                  # object {"Name": "...", "Environment": "..."}
input.resources[i].instances[j].attributes.tags_all
input.resources[i].instances[j].attributes.arn
input.resources[i].instances[j].attributes.id
input.resources[i].instances[j].attributes.public_ip
input.resources[i].instances[j].attributes.private_ip
input.resources[i].instances[j].attributes.security_groups[]
input.resources[i].instances[j].attributes.vpc_security_group_ids[]
input.resources[i].instances[j].attributes.subnet_id
input.resources[i].instances[j].attributes.availability_zone
input.resources[i].instances[j].attributes.ebs_optimized         # boolean
input.resources[i].instances[j].attributes.monitoring            # boolean
input.resources[i].instances[j].attributes.associate_public_ip_address  # boolean
input.resources[i].instances[j].attributes.root_block_device[k].encrypted        # boolean
input.resources[i].instances[j].attributes.root_block_device[k].volume_size      # number
input.resources[i].instances[j].attributes.root_block_device[k].volume_type      # "gp2", "gp3", etc.
input.resources[i].instances[j].attributes.metadata_options[k].http_tokens       # "optional", "required"

# S3 bucket specific attributes
input.resources[i].instances[j].attributes.bucket
input.resources[i].instances[j].attributes.bucket_prefix
input.resources[i].instances[j].attributes.region
input.resources[i].instances[j].attributes.versioning[k].enabled                 # boolean
input.resources[i].instances[j].attributes.server_side_encryption_configuration[k].rule[l].apply_server_side_encryption_by_default[m].sse_algorithm  # "AES256", "aws:kms"
input.resources[i].instances[j].attributes.force_destroy                         # boolean

# Instance dependencies
input.resources[i].instances[j].dependencies[]                   # e.g. ["aws_s3_bucket.s3_bucket"]

# Outputs
input.outputs.<output_name>.type                                 # "string"
input.outputs.<output_name>.value

# Top-level state metadata
input.terraform_version                                          # e.g. "1.5.3"
input.version                                                    # state format version, e.g. 4
input.serial                                                     # state serial number
input.lineage                                                    # state lineage UUID

# IACM metadata
input.iacmMetadata.account
input.iacmMetadata.org
input.iacmMetadata.project
input.iacmMetadata.workspace
input.iacmMetadata.pipelineExecutionID

# Standard metadata
input.metadata.action                                            # "afterTerraformPlan"
input.metadata.type                                              # "terraformState"
input.metadata.timestamp
input.metadata.principalIdentifier
input.metadata.principalType
input.metadata.projectMetadata.identifier
input.metadata.projectMetadata.orgIdentifier
```

### Example 1: Enforce allowed AMIs

```rego
package terraform_state

allowed_amis = ["ami-0aa7d40eeae50c9a9"]

deny[msg] {
  r = input.resources[_]
  r.type == "aws_instance"
  instance = r.instances[_]
  not array_contains(allowed_amis, instance.attributes.ami)
  msg := sprintf("Instance '%s' uses disallowed AMI '%s'", [r.name, instance.attributes.ami])
}

array_contains(arr, elem) {
  arr[_] = elem
}
```

### Example 2: Require encryption on EBS volumes

```rego
package terraform_state

deny[msg] {
  r = input.resources[_]
  r.type == "aws_instance"
  instance = r.instances[_]
  block_device = instance.attributes.root_block_device[_]
  block_device.encrypted == false
  msg := sprintf("Instance '%s' has unencrypted root block device", [r.name])
}
```

### Example 3: Deny public IP addresses on instances

```rego
package terraform_state

deny[msg] {
  r = input.resources[_]
  r.type == "aws_instance"
  instance = r.instances[_]
  instance.attributes.associate_public_ip_address == true
  msg := sprintf("Instance '%s' must not have a public IP address", [r.name])
}
```

### Example 4: Require S3 bucket encryption

```rego
package terraform_state

deny[msg] {
  r = input.resources[_]
  r.type == "aws_s3_bucket"
  instance = r.instances[_]
  not has_encryption(instance)
  msg := sprintf("S3 bucket '%s' must have server-side encryption enabled", [r.name])
}

has_encryption(instance) {
  instance.attributes.server_side_encryption_configuration[_].rule[_].apply_server_side_encryption_by_default[_].sse_algorithm
}
```

### Example 5: Require IMDSv2 (http_tokens = "required")

```rego
package terraform_state

deny[msg] {
  r = input.resources[_]
  r.type == "aws_instance"
  instance = r.instances[_]
  metadata = instance.attributes.metadata_options[_]
  metadata.http_tokens != "required"
  msg := sprintf("Instance '%s' must use IMDSv2 (http_tokens must be 'required')", [r.name])
}
```

### Sample JSON

```json
{
  "iacmMetadata": {
    "account": "l7HREAyVTnyfUsfUtPZUow",
    "org": "default",
    "project": "Testim",
    "workspace": "beta1new",
    "pipelineExecutionID": "NXQfSd1cQv2fWBO42z-FpA"
  },
  "lineage": "4db5d6ad-807f-0ac6-fd93-2261c55ccd4b",
  "metadata": {
    "action": "afterTerraformPlan",
    "principalIdentifier": "SERVICE",
    "principalType": "SERVICE",
    "projectMetadata": {
      "identifier": "Testim",
      "name": "Testim",
      "orgIdentifier": "default"
    },
    "timestamp": 1774427935,
    "type": "terraformState"
  },
  "outputs": {
    "instance_type": { "type": "string", "value": "t2.micro" },
    "bucket_arn": { "type": "string", "value": "arn:aws:s3:::bucket620260325083249414000000001" },
    "ip": { "type": "string", "value": "172.31.51.178" }
  },
  "resources": [
    {
      "instances": [
        {
          "attributes": {
            "ami": "ami-0aa7d40eeae50c9a9",
            "arn": "arn:aws:ec2:us-east-1:326699728404:instance/i-0d9ba3f7e13e4a60d",
            "associate_public_ip_address": true,
            "availability_zone": "us-east-1a",
            "ebs_optimized": false,
            "instance_state": "running",
            "instance_type": "t2.micro",
            "metadata_options": [{ "http_endpoint": "enabled", "http_tokens": "optional" }],
            "monitoring": false,
            "private_ip": "172.31.51.178",
            "public_ip": "50.19.163.1",
            "root_block_device": [{ "encrypted": false, "volume_size": 8, "volume_type": "gp2" }],
            "security_groups": ["default"],
            "tags": { "extra": "I am from the git", "name": "ec2test1" }
          }
        }
      ],
      "mode": "managed",
      "name": "ec2test1",
      "provider": "provider[\"registry.terraform.io/hashicorp/aws\"]",
      "type": "aws_instance"
    },
    {
      "instances": [
        {
          "attributes": {
            "arn": "arn:aws:s3:::bucket620260325083249414000000001",
            "bucket": "bucket620260325083249414000000001",
            "bucket_prefix": "bucket6",
            "force_destroy": false,
            "region": "us-east-1",
            "server_side_encryption_configuration": [
              { "rule": [{ "apply_server_side_encryption_by_default": [{ "sse_algorithm": "AES256" }] }] }
            ],
            "tags": { "Environment": "test1env", "Name": "testname1" },
            "versioning": [{ "enabled": false }]
          }
        }
      ],
      "mode": "managed",
      "name": "s3_bucket",
      "provider": "provider[\"registry.terraform.io/hashicorp/aws\"]",
      "type": "aws_s3_bucket"
    }
  ],
  "serial": 5264,
  "terraform_version": "1.5.3",
  "version": 4
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
