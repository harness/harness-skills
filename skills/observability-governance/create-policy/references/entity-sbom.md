# SBOM (Software Bill of Materials) Policies

## Package: `sbom`
## Root path: `input` (array of packages at root level)
## Valid actions: `onstep`

## Input Schema

The SBOM input is a **flat array of package objects** at the root level:

```
input[i].uuid
input[i].packageName
input[i].packageVersion
input[i].packageLicense[j]                 # array of license strings, e.g. ["MIT", "Apache-2.0"]
input[i].purl                              # package URL, e.g. "pkg:golang/github.com/foo/bar@1.0.0"
input[i].packageOriginatorName             # supplier, e.g. "Organization: Red Hat, Inc."
input[i].filterTags[j]                     # image layer tags, e.g. ["BASE", "APP", "DISTRO"]
```

## Deny List Pattern

The standard SBOM policy uses configurable deny/allow lists with operators:

| Operator | Meaning |
|----------|---------|
| `==` | Exact match |
| `!` | Not equal |
| `~` | Regex match |
| `<`, `<=`, `>`, `>=` | Semver comparison |
| `><` | Between (exclusive) |
| `>=<`, `>=<=`, `><=` | Between (mixed inclusive/exclusive) |

## Example 1: Deny list (block specific packages)

**Scenario:** Block curl <= 3.0.0, any log4j, and busybot between 3.0.0 and 5.0.0.

```rego
package sbom

import future.keywords.if
import future.keywords.in

deny_list := fill_default_deny_rules([
  {
    "name": {"value": "curl", "operator": "=="},
    "version": {"value": "3.0.0", "operator": "<="},
  },
  {
    "name": {"value": ".*log4j.*", "operator": "~"},
    "version": {"value": "3.0.0", "operator": "<"},
  },
  {
    "name": {"value": "busybot", "operator": "=="},
    "version": {"value": "3.0.0,5.0.0", "operator": "><"},
  },
])

allow_list := {
  "licenses": [],
  "purls": [],
  "suppliers": [],
}

deny_list_violations[violations] {
  some deny_rule in deny_list
  violations := [x |
    x := {
      "type": "deny",
      "rule": deny_rule,
      "violations": [violating_id |
        some pkg in input
        violating_id := pkg.uuid
        deny_compare(pkg, deny_rule)
      ],
    }
  ]
  count(violations) > 0
}

deny_compare(pkg, rule) if {
  is_name_denied(pkg, rule)
  is_purl_denied(pkg, rule)
  is_supplier_denied(pkg, rule)
  pkg_version := version_to_semver(pkg.packageVersion)
  rule_version := version_to_semver(rule.version.value)
  semver_compare(pkg_version, rule.version.operator, rule_version)
}

is_name_denied(pkg, rule) if { str_compare(pkg.packageName, rule.name.operator, rule.name.value) }
is_name_denied(pkg, rule) if { not pkg.packageName; rule.name.value == null }

is_purl_denied(pkg, rule) if { str_compare(pkg.purl, rule.purl.operator, rule.purl.value) }
is_purl_denied(pkg, rule) if { not pkg.purl; rule.purl.value == null }

is_supplier_denied(pkg, rule) if { str_compare(pkg.packageOriginatorName, rule.supplier.operator, rule.supplier.value) }
is_supplier_denied(pkg, rule) if { not pkg.packageOriginatorName; rule.supplier.value == null }

str_compare(a, "==", b) := a == b
str_compare(a, "!", b) := a != b
str_compare(a, "~", b) := regex.match(b, a)
str_compare(a, null, b) := a == b if b != null
str_compare(_, null, null) := true

semver_compare(a, "<=", b) := semver.compare(a, b) <= 0
semver_compare(a, "<", b) := semver.compare(a, b) < 0
semver_compare(a, "==", b) := semver.compare(a, b) == 0
semver_compare(a, ">", b) := semver.compare(a, b) > 0
semver_compare(a, ">=", b) := semver.compare(a, b) >= 0
semver_compare(a, "!", b) := semver.compare(a, b) != 0

semver_compare(a, "><", b) if {
  ys := split(b, ",")
  semver.compare(a, ys[0]) > 0
  semver.compare(a, ys[1]) < 0
}

semver_compare(a, ">=<=", b) if {
  ys := split(b, ",")
  semver.compare(a, ys[0]) >= 0
  semver.compare(a, ys[1]) <= 0
}

version_to_semver(version) = output if {
    parts := split(version, "-")
    numeric := parts[0]
    numParts := split(numeric, ".")
    count(numParts) == 1
    normalized := concat(".", [numeric, "0", "0"])
    remainder := array.slice(parts, 1, count(parts))
    output := with_remainder(normalized, remainder)
}

version_to_semver(version) = output if {
    parts := split(version, "-")
    numeric := parts[0]
    numParts := split(numeric, ".")
    count(numParts) == 2
    normalized := concat(".", [numeric, "0"])
    remainder := array.slice(parts, 1, count(parts))
    output := with_remainder(normalized, remainder)
}

version_to_semver(version) = output if {
    parts := split(version, "-")
    numeric := parts[0]
    numParts := split(numeric, ".")
    count(numParts) >= 3
    remainder := array.slice(parts, 1, count(parts))
    output := with_remainder(numeric, remainder)
}

version_to_semver(version) = output if { version == null; output := null }

with_remainder(base, remainder) = concat("-", array.concat([base], remainder)) if count(remainder) > 0
with_remainder(base, remainder) = base if count(remainder) == 0

fill_default_deny_rules(obj) := list if {
  defaults := {
    "name": {"value": null, "operator": null},
    "license": {"value": null, "operator": null},
    "version": {"value": null, "operator": null},
    "supplier": {"value": null, "operator": null},
    "purl": {"value": null, "operator": null},
  }
  list := [x | x := object.union(defaults, obj[_])]
}
```

## Example 2: Allow list (only specific licenses allowed)

**Scenario:** Only permit packages with MIT, Apache-2.0, or Eclipse licenses.

```rego
package sbom

import future.keywords.if
import future.keywords.in

allow_list := {
  "licenses": [
    {"license": {"value": "MIT", "operator": "=="}},
    {"license": {"value": "Apache-2.0", "operator": "=="}},
    {"license": {"value": "EPL-.*", "operator": "~"}},
  ],
  "purls": [],
  "suppliers": [],
}

allow_rules_licenses_violations(rules) := violating_packages if {
  violating_packages := {result |
    some pkg in input
    does_violate_license(pkg, rules)
    result = pkg.uuid
  }
  count(violating_packages) > 0
}

does_violate_license(pkg, rules) if {
  some package_license in pkg.packageLicense
  not does_match_license(package_license, rules)
}

does_match_license(license, rules) if {
  some rule in rules
  str_compare(license, rule.license.operator, rule.license.value)
}

str_compare(a, "==", b) := a == b
str_compare(a, "~", b) := regex.match(b, a)
```

## Key Notes

- SBOM input is a **flat array** — iterate with `some pkg in input` or `input[i]`.
- The deny list + allow list + `fill_default_deny_rules` pattern is the standard. Only modify the list entries, not the boilerplate comparison functions.
- Version comparisons use `semver.compare()` — normalize versions to semver first with `version_to_semver()`.
- For image-layer-aware policies, use `pkg.filterTags` to scope rules to BASE, APP, or DISTRO layers.
