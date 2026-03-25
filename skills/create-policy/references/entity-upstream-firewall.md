# Upstream Firewall Policies

## Package: `firewall`
## Root path: `input` (array of packages at root level)
## Valid actions: `onEvaluation`

## Input Schema

The upstream firewall input is an **array of package objects** at the root level:

```
input[i].name
input[i].version
input[i].description
input[i].latest_version
input[i].licenses[j]                        # array of license strings
input[i].purl                               # package URL
input[i].package_manager                    # "npm", "pypi", "maven", etc.
input[i].release_date                       # ISO 8601 date string
input[i].cves[j].id                         # "CVE-2023-12345"
input[i].cves[j].impact.base_score         # float, e.g. 9.8
input[i].cves[j].impact.base_severity      # "CRITICAL", "HIGH", "MEDIUM", "LOW"
input[i].oss_risk.level                     # "critical", "high", "medium", "low"
input[i].oss_risk.score                     # integer
```

## Example 1: CVSS threshold

**Scenario:** Block packages with any CVE having a CVSS base score above 9.0.

```rego
package firewall

deny[msg] {
  pkg := input[_]
  cve := pkg.cves[_]
  cve.impact.base_score > 9.0
  msg := sprintf("Package '%s@%s' has CVE '%s' with CVSS score %.1f (threshold: 9.0)", [pkg.name, pkg.version, cve.id, cve.impact.base_score])
}
```

## Example 2: License policy

**Scenario:** Block packages with GPL licenses.

```rego
package firewall

blocked_licenses := ["GPL-2.0", "GPL-3.0", "AGPL-3.0"]

deny[msg] {
  pkg := input[_]
  license := pkg.licenses[_]
  is_blocked(license)
  msg := sprintf("Package '%s@%s' has blocked license '%s'", [pkg.name, pkg.version, license])
}

is_blocked(license) {
  blocked := blocked_licenses[_]
  license == blocked
}
```

## Example 3: Package age policy

**Scenario:** Block packages that haven't been updated in over 2 years.

```rego
package firewall

import future.keywords.if

max_age_days := 730

deny[msg] {
  pkg := input[_]
  release_ns := time.parse_rfc3339_ns(pkg.release_date)
  now_ns := time.now_ns()
  age_days := (now_ns - release_ns) / (24 * 60 * 60 * 1000000000)
  age_days > max_age_days
  msg := sprintf("Package '%s@%s' was released %d days ago (max allowed: %d)", [pkg.name, pkg.version, age_days, max_age_days])
}
```

## Example 4: OSS risk level

**Scenario:** Block packages with critical or high OSS risk.

```rego
package firewall

blocked_risk_levels := ["critical", "high"]

deny[msg] {
  pkg := input[_]
  contains(blocked_risk_levels, pkg.oss_risk.level)
  msg := sprintf("Package '%s@%s' has '%s' OSS risk level (score: %d)", [pkg.name, pkg.version, pkg.oss_risk.level, pkg.oss_risk.score])
}

contains(arr, elem) {
  arr[_] = elem
}
```
