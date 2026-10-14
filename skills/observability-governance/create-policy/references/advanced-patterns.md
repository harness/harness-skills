# Advanced Rego Patterns for Harness OPA

These patterns come from real-world customer implementations and the Harness Solutions Architecture team. They demonstrate techniques beyond simple field checks.

---

## Pattern 1: Exception Handling (Bypass for Approved Users/Groups/Tags)

Many policies need to be enforced globally but allow specific users, user groups, or tagged resources to bypass them. The standard approach is to create a `verify_exception_handlers` rule.

```rego
package pipeline

import future.keywords.if
import future.keywords.in

approved_users = ["admin@company.com"]
approved_groups = ["account._account_admin_group"]
approved_pipeline_tags = {"exception": "approved"}

deny[msg] {
	not verify_exception_handlers
	msg := sprintf("Pipeline '%s' failed policy check (no exception granted)", [input.pipeline.name])
}

verify_exception_handlers if {
	tmp_output := array.concat(
		[return_count_if_elem_in_list(input.metadata.user.email, approved_users)],
		array.concat(
			[return_count_if_elem_in_list(input.metadata.userGroups, approved_groups)],
			[return_count_if_elem_in_list(input.pipeline.tags, approved_pipeline_tags)],
		),
	)
	count([elem | some elem in tmp_output; elem > 0]) > 0
}

return_notated_obj(eval_item) := eval_item.identifier if {
	eval_item.projectIdentifier != ""
} else := concat(".", ["org", eval_item.identifier]) if {
	eval_item.orgIdentifier != ""
} else := concat(".", ["account", eval_item.identifier]) if {
	eval_item.identifier != ""
} else := eval_item

return_count_if_elem_in_list(items, eval_arr) := output if {
	is_array(items)
	output := count([item | some item in items; array_contains(eval_arr, return_notated_obj(item))])
} else := output if {
	is_object(items)
	output := to_number(has_all_keys_and_values(items, eval_arr))
} else := count([item | some item in [items]; array_contains(eval_arr, return_notated_obj(item))])

array_contains(arr, elem) if {
	arr[_] = elem
}

has_key(x, k) if {
	_ = x[k]
}

has_all_keys_and_values(truth, check) := true if {
	count([key | some key, elem in truth; has_key(check, key); elem == check[key]]) == count(object.keys(check))
} else := false
```

**When to use:** Any policy that requires a "bypass" mechanism for privileged users, groups, or specially tagged pipelines.

---

## Pattern 2: Restrict Pipeline Execution by User/Group

Limit which users or groups can execute specific pipelines.

```rego
package pipeline

import future.keywords.if
import future.keywords.in

approved_users = ["deployer@company.com"]
approved_groups = ["account.deploy_team"]
allow_webhooks = true

enforced_pipelines = [
	{"org": "default", "project": "prod", "pipeline": "production_deploy"},
]

deny[msg] {
	is_pipeline_enforced
	is_not_webhook
	not verify_exception_handlers
	msg := sprintf("Pipeline '%s' can only be executed by approved users", [input.pipeline.name])
}

is_pipeline_enforced {
	pipeline = input.pipeline
	enforced_orgs = [elem | some elem in enforced_pipelines; elem.org == pipeline.orgIdentifier]
	enforced_prjs = [elem | some elem in enforced_orgs; elem.project == pipeline.projectIdentifier]
	enforced_pipe = [elem.pipeline | some elem in enforced_prjs]
	array_contains(enforced_pipe, pipeline.identifier)
}

is_not_webhook if {
	not allow_webhooks
} else if {
	input.metadata.user != "null"
}

verify_exception_handlers if {
	tmp_output := array.concat(
		[return_count_if_elem_in_list(input.metadata.user.email, approved_users)],
		[return_count_if_elem_in_list(input.metadata.userGroups, approved_groups)],
	)
	count([elem | some elem in tmp_output; elem > 0]) > 0
}

return_notated_obj(eval_item) := eval_item.identifier if {
	eval_item.projectIdentifier != ""
} else := concat(".", ["org", eval_item.identifier]) if {
	eval_item.orgIdentifier != ""
} else := concat(".", ["account", eval_item.identifier]) if {
	eval_item.identifier != ""
} else := eval_item

return_count_if_elem_in_list(items, eval_arr) := output if {
	is_array(items)
	output := count([item | some item in items; array_contains(eval_arr, return_notated_obj(item))])
} else := output if {
	is_object(items)
	output := to_number(has_all_keys_and_values(items, eval_arr))
} else := count([item | some item in [items]; array_contains(eval_arr, return_notated_obj(item))])

array_contains(arr, elem) if {
	arr[_] = elem
}

has_all_keys_and_values(truth, check) := true if {
	count([key | some key, elem in truth; has_key(check, key); elem == check[key]]) == count(object.keys(check))
} else := false

has_key(x, k) if {
	_ = x[k]
}
```

---

## Pattern 3: Recursive Walk for Forbidden Values

Use OPA's `walk()` built-in to scan the entire pipeline document for any occurrence of a forbidden value (e.g., a secret reference, a connector ID). This finds values regardless of nesting depth.

```rego
package pipeline

import future.keywords.if
import future.keywords.in

approved_pipelines = []
forbidden_items = ["testing", "<+secrets.getValue(\"testing\")>"]
exact_match = true

deny[msg] {
	not array_contains(approved_pipelines, input.pipeline.identifier)
	[path, value] = walk(input)
	return_nonempty(path)
	return_nonempty(value)

	some forbidden_value in forbidden_items
	return_found_with_value(value, forbidden_value, exact_match)

	fmt_path = format_notated_array(path)
	forbidden_key := path[count(path) - 1]
	msg := sprintf("Path '%s' references forbidden value '%s' at key '%s'", [fmt_path, forbidden_value, forbidden_key])
}

return_nonempty(item) {
	item != ""
	item != []
	item != {}
}

return_found_with_value(value, forbidden_value, exact_match) := value if {
	exact_match == false
	contains(value, forbidden_value)
} else := value if {
	value == forbidden_value
}

format_notated_array(path) := output if {
	output := concat(".", [format_notation(elem) | some elem in array.slice(path, 0, count(path) - 1)])
}

format_notation(eval_elem) := format_int(eval_elem, 10) if is_number(eval_elem)
else := eval_elem

array_contains(arr, elem) if {
	arr[_] = elem
}
```

**Key concept:** `walk(input)` yields `[path, value]` pairs for every node in the document tree. Filter by path/value to find forbidden content anywhere in the payload.

---

## Pattern 4: Pipeline Git Branch Restrictions

Restrict which branches pipeline definitions can be sourced from, using `glob.match` for wildcard patterns.

```rego
package pipeline

import future.keywords.in

approved_branches := ["development", "release/*", "main"]

deny[msg] {
	branch := input.pipeline.gitConfig.branch
	count([elem | some elem in approved_branches; glob.match(elem, [], branch)]) == 0
	msg := sprintf("Pipeline source branch '%s' is not allowed. Approved branches: %s", [branch, approved_branches])
}
```

**Key concept:** `glob.match(pattern, delimiters, value)` supports `*` and `?` wildcards. Use `[]` for delimiters when matching flat strings.

---

## Pattern 5: CI Build Farm Namespace Restrictions

Ensure CI stages only use approved Kubernetes namespaces for build infrastructure.

```rego
package pipeline

import future.keywords.if

approved_namespaces = ["harnessci", "builds-prod"]

deny[msg] {
	stage = input.pipeline.stages[_].stage
	stage.type == "CI"
	stage_namespace := stage.spec.infrastructure.spec.namespace
	not array_contains(approved_namespaces, stage_namespace)
	msg := sprintf("CI stage '%s' uses namespace '%s' which is not approved. Allowed: %s", [stage.name, stage_namespace, approved_namespaces])
}

array_contains(arr, elem) if {
	arr[_] = elem
}
```

---

## Pattern 6: Secret Naming and Description Standards

Enforce naming conventions and mandatory descriptions on secrets.

```rego
package secret

import future.keywords.if

forbidden_secret_prefix = "secret"
mandatory_desc_prefix = "Provides access to "

deny[msg] {
	secret := input.secret
	startswith(lower(secret.name), lower(forbidden_secret_prefix))
	msg := sprintf("Secret '%s' must not begin with '%s'", [secret.name, forbidden_secret_prefix])
}

deny[msg] {
	secret := input.secret
	secret.description == ""
	msg := sprintf("Secret '%s' must have a description beginning with '%s'", [secret.name, mandatory_desc_prefix])
}

deny[msg] {
	secret := input.secret
	secret.description != ""
	not startswith(lower(secret.description), lower(mandatory_desc_prefix))
	msg := sprintf("Secret '%s' description must begin with '%s'", [secret.name, mandatory_desc_prefix])
}
```

**NOTE:** Some community examples use `input.secret` as the root path. The policy-mgmt examples use `input.secretEntity`. Check which root path your Harness instance sends. The `metadata` object at `input.metadata` is always available for user/role checks.

---

## Pattern 7: Secret Manager Restrictions

Force all secrets to use an approved secret manager.

```rego
package secret

import future.keywords.if

approved_secret_managers := ["harnessSecretManager", "vault_prod"]

deny[msg] {
	secret := input.secret
	not secret.spec.secretManagerIdentifier
	msg := sprintf("Secret '%s' must specify a Secret Manager", [secret.name])
}

deny[msg] {
	secret := input.secret
	not array_contains(approved_secret_managers, secret.spec.secretManagerIdentifier)
	msg := sprintf("Secret '%s' uses unapproved Secret Manager '%s'. Approved: [%s]",
		[secret.name, secret.spec.secretManagerIdentifier, concat(", ", approved_secret_managers)])
}

array_contains(arr, elem) if {
	arr[_] = elem
}
```

---

## Pattern 8: Template Version Schema Enforcement

Enforce semantic versioning on template version labels using regex.

```rego
package template

version_format = "^(0|[1-9]\\d*)\\.(0|[1-9]\\d*)\\.(0|[1-9]\\d*)(?:-((?:0|[1-9]\\d*|\\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\\.(?:0|[1-9]\\d*|\\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\\+([0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*))?$"

deny[msg] {
	template_version = input.template.versionLabel
	not regex.match(version_format, template_version)
	msg := sprintf("Template version '%s' does not follow semantic versioning (e.g., 1.0.0)", [template_version])
}
```

**Key concept:** `regex.match(pattern, value)` for pattern validation. Double-escape backslashes in Rego strings.

---

## Pattern 9: Approval Input Validation (Custom Policy)

Validate that approval step inputs match required patterns (e.g., ServiceNow ticket format).

```rego
package pipeline

import future.keywords.if
import future.keywords.in

verifications := {
	"SNOW TICKET": "CHG\\d{6}",
}

mandatory_keys := ["SNOW TICKET"]

deny[msg] {
	some key, value in input[0].outcome.approverInputs
	has_key(verifications, key)
	not regex.match(verifications[key], value)
	msg := sprintf("Approval input '%s' value (%s) does not match pattern (%s)", [key, value, verifications[key]])
}

deny[msg] {
	approverInputs = object.keys(input[0].outcome.approverInputs)
	some key in mandatory_keys
	not array_contains(approverInputs, key)
	msg := sprintf("Required approval input '%s' was not provided", [key])
}

array_contains(arr, elem) {
	arr[_] = elem
}

has_key(x, k) if {
	_ = x[k]
}
```

**Note:** Custom/approval policies use `input[0].outcome` as the root path — the input is an array of evaluation results.

---

## Pattern 10: Scoped Resource References

Harness resources (connectors, secrets, templates) can be scoped at account, org, or project level. The reference format is:
- **Project-level**: `my_connector` (no prefix)
- **Org-level**: `org.my_connector`
- **Account-level**: `account.my_connector`

Helper to normalize any connector/resource reference into its scoped notation:

```rego
return_notated_obj(eval_item) := eval_item.identifier if {
	eval_item.projectIdentifier != ""
} else := concat(".", ["org", eval_item.identifier]) if {
	eval_item.orgIdentifier != ""
} else := concat(".", ["account", eval_item.identifier]) if {
	eval_item.identifier != ""
} else := eval_item
```

When writing policies that check connector/secret references, always consider all three scopes:

```rego
forbidden_connectors = ["account.default_github_access", "org.shared_docker"]

deny[msg] {
	stage = input.pipeline.stages[_].stage
	connector_ref := stage.spec.infrastructure.spec.connector
	array_contains(forbidden_connectors, connector_ref)
	msg := sprintf("Stage '%s' uses forbidden connector '%s'", [stage.name, connector_ref])
}
```

---

## Pattern 11: Pipeline Exemption by Org/Project/Pipeline

Allow specific pipelines (identified by org + project + pipeline identifier) to bypass a policy.

```rego
exempted_pipelines = [
	{"org": "default", "project": "prod", "pipeline": "emergency_deploy"},
	{"org": "default", "project": "staging", "pipeline": "test_deploy"},
]

is_pipeline_exempt {
	pipeline = input.pipeline
	exempted_orgs = [elem | some elem in exempted_pipelines; elem.org == pipeline.orgIdentifier]
	exempted_prjs = [elem | some elem in exempted_orgs; elem.project == pipeline.projectIdentifier]
	exempted_pipe = [elem.pipeline | some elem in exempted_prjs]
	array_contains(exempted_pipe, pipeline.identifier)
}
```

Usage in a deny rule:

```rego
deny[msg] {
	not is_pipeline_exempt
	# ... rest of policy checks ...
	msg := "Policy violation detected"
}
```

---

## Pattern 12: Enforce Mandatory Step Group Templates in CI Stages

Require that all CI stages include a specific step group template (e.g., for mandatory security scanners).

```rego
package pipeline

import future.keywords.if
import future.keywords.in

stage_type = "CI"
mandatory_templates = ["account.requiredScanners"]

deny[msg] {
	stage = input.pipeline.stages[_].stage
	stage.type == stage_type
	not has_required_template(stage)
	msg := sprintf("CI stage '%s' must include one of the mandatory templates: [%s]",
		[stage.name, concat(", ", mandatory_templates)])
}

has_required_template(stage) if {
	step_group := stage.spec.execution.steps[_].stepGroup
	has_key(step_group, "template")
	array_contains(mandatory_templates, step_group.template.templateRef)
}

has_required_template(stage) if {
	has_key(stage, "template")
	array_contains(mandatory_templates, stage.template.templateRef)
}

array_contains(arr, elem) if {
	arr[_] = elem
}

has_key(x, k) if {
	_ = x[k]
}
```

---

## Pattern 13: Find Steps at Any Nesting Depth (Step Groups, Parallel, Inserts)

Pipeline execution steps can be nested inside step groups, parallel blocks, and insert nodes at arbitrary depth. A policy that only checks `steps[_].step` will miss steps inside these containers.

**Recommended: Use `walk()` to find all steps regardless of nesting:**

```rego
package pipeline

deny[msg] {
	stage := all_stages[_]
	stage.type == "Deployment"
	[path, step] = walk(stage.spec.execution)
	path[count(path) - 1] == "step"
	step.type == "ShellScript"
	msg := sprintf("forbidden ShellScript step '%s' found in stage '%s' (may be nested in step group or parallel block)", [step.name, stage.name])
}

all_stages[stage] {
	stage := input.pipeline.stages[_].stage
}

all_stages[stage] {
	stage := input.pipeline.stages[_].parallel[_].stage
}
```

**Alternative: Use `walk()` without path filtering when you know the type field is unique to steps:**

```rego
deny[msg] {
	[_, value] = walk(input.pipeline)
	value.type == "HarnessApproval"
	value.spec.approvers.disallowPipelineExecutor != true
	msg := sprintf("approval step '%s' must set disallowPipelineExecutor to true", [value.name])
}
```

**When you need positional information (e.g., order of steps), enumerate explicit paths:**

```rego
# Direct step
check_step(step) { step := input.pipeline.stages[_].stage.spec.execution.steps[_].step }
# Step in step group
check_step(step) { step := input.pipeline.stages[_].stage.spec.execution.steps[_].stepGroup.steps[_].step }
# Step in parallel block
check_step(step) { step := input.pipeline.stages[_].stage.spec.execution.steps[_].parallel[_].step }
# Step in step group inside parallel
check_step(step) { step := input.pipeline.stages[_].stage.spec.execution.steps[_].parallel[_].stepGroup.steps[_].step }
# Step in parallel inside step group
check_step(step) { step := input.pipeline.stages[_].stage.spec.execution.steps[_].stepGroup.steps[_].parallel[_].step }
```

**Also check rollback steps, which have the same recursive structure:**

```rego
deny[msg] {
	[_, step] = walk(input.pipeline)
	step.type == "ShellScript"
	# This will find ShellScript in both execution.steps AND execution.rollbackSteps
	msg := sprintf("forbidden ShellScript step '%s'", [step.name])
}
```

**Nesting model reference:**
```
ExecutionElementConfig
├── steps[] → ExecutionWrapperConfig (exactly one of):
│   ├── step         — single step (leaf)
│   ├── stepGroup    — StepGroupElementConfig
│   │   └── steps[] → ExecutionWrapperConfig (recursive)
│   ├── parallel[]   → ExecutionWrapperConfig[] (recursive)
│   └── insert       — InsertStepsNode
│       └── steps[] → ExecutionWrapperConfig (recursive)
└── rollbackSteps[] → ExecutionWrapperConfig (same structure)
```

---

## Useful Built-in Functions Reference

| Function | Use Case | Example |
|---|---|---|
| `walk(input)` | Recursively traverse all nodes | `[path, value] = walk(input)` |
| `glob.match(pattern, delims, value)` | Wildcard matching | `glob.match("release/*", [], branch)` |
| `regex.match(pattern, value)` | Regex validation | `regex.match("^v\\d+", version)` |
| `startswith(str, prefix)` | Prefix check | `startswith(name, "prod-")` |
| `contains(str, substr)` | Substring check | `contains(value, "forbidden")` |
| `lower(str)` | Case normalization | `lower(input.pipeline.name)` |
| `sprintf(fmt, args)` | Format messages | `sprintf("stage '%s'", [name])` |
| `object.get(obj, path, default)` | Safe nested access | `object.get(stage, ["spec", "env"], {})` |
| `object.keys(obj)` | Get all keys | `object.keys(input.pipeline.tags)` |
| `object.union(a, b)` | Merge objects | `object.union(base, override)` |
| `array.concat(a, b)` | Merge arrays | `array.concat(list1, list2)` |
| `format_int(n, base)` | Number to string | `format_int(count, 10)` |
| `time.now_ns()` | Current time (nanoseconds) | `time.now_ns()` |
| `time.diff(a, b)` | Time difference | `[y,m,d,h,min,s] = time.diff(t1, t2)` |
| `time.add_date(t, y, m, d)` | Add to timestamp | `time.add_date(base, 0, 0, 7)` |
