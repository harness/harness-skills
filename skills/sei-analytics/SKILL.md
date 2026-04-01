---
name: sei-analytics
description: >-
  Advanced engineering analytics via Harness Software Engineering Insights (SEI) MCP. Configure
  sprint velocity and estimation accuracy tracking, engineering investment allocation breakdowns,
  sprint planning with capacity forecasts, and release readiness assessments. Use when asked about
  sprint analytics, investment allocation, sprint planning, capacity forecasting, or release
  readiness. Do NOT use for DORA metrics (use dora-metrics instead). Trigger phrases: sprint
  velocity, sprint analytics, investment allocation, capacity planning, sprint forecast, release
  readiness, engineering productivity, estimation accuracy, sprint planning, scope creep,
  code quality trends.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# SEI Analytics

Configure sprint analytics, investment allocation, capacity forecasting, and release readiness assessments in Harness Software Engineering Insights.

## Instructions

### Step 1: Establish Scope

Confirm the user's org, team, and tracking period.

```
Call MCP tool: harness_list
Parameters:
  resource_type: "project"
  org_id: "<organization>"
```

### Step 2: Identify the SEI Task

Determine which analytics the user needs:

1. **Sprint Analytics** -- Velocity, estimation accuracy, scope change tracking
2. **Investment Allocation** -- Engineering time breakdown by category
3. **Sprint Planning and Capacity Forecast** -- Data-driven sprint planning
4. **Release Readiness Assessment** -- Checklist for release go/no-go

### Step 3: Configure Sprint Analytics

Gather from the user:
- Team name and sprint length (weeks)
- Tracking period (last N sprints)
- Issue tracker integration (Jira, Azure DevOps, Linear)

Analyze sprint metrics:

**Velocity:**
- Story points committed vs. completed per sprint
- Velocity trend over the tracking period
- Carryover rate (% of stories that spill into next sprint)

**Estimation Accuracy:**
- Actual vs. estimated story points across sprints
- Which issue types are consistently underestimated
- Estimation accuracy trend (improving or degrading)

**Scope Change:**
- Stories added mid-sprint (scope creep %)
- Stories removed mid-sprint
- Net scope change and its impact on completion rate

**Delivery Composition:**
- Breakdown by issue type: features, bugs, tech debt, maintenance
- Breakdown by priority: P0/P1 vs. lower priority
- Team-level vs. individual-level trends

### Step 4: Analyze Investment Allocation

Gather from the user:
- Teams to analyze
- Time period for analysis
- Investment categories (features, bugs, tech debt, maintenance, ops)

Calculate allocation:
- % of engineering time per category
- Compare against target allocation (e.g., 70% features, 15% tech debt, 10% bugs, 5% ops)
- Trend over time: is tech debt growing or shrinking?
- Per-team breakdowns to identify teams disproportionately spending on bugs or ops

Present with:
- Current allocation vs. target allocation
- Recommendations for rebalancing
- Impact of current allocation on velocity and quality trends

### Step 5: Sprint Planning and Capacity Forecast

Gather from the user:
- Sprint number, duration, and team size
- Planned PTO, meetings, and other commitments

Calculate capacity:
- Available engineering days = team size * sprint days - PTO - meeting overhead
- Historical velocity per engineer per sprint
- Recommended story points for the sprint (based on rolling average)

Risk factors to flag:
- Large stories (>8 points) that could block the sprint
- Dependencies on other teams
- Carryover from previous sprint
- Tech debt items that may slow feature work

### Step 6: Release Readiness Assessment

Gather from the user:
- Service name, version, target environment
- Change summary and target release date

Assess readiness:

**Code Quality:**
- Code coverage delta (current vs. threshold)
- Static analysis findings (new warnings or errors)
- Code review completion (all PRs reviewed and approved)

**Pipeline Health:**
```
Call MCP tool: harness_list
Parameters:
  resource_type: "execution"
  org_id: "<organization>"
  project_id: "<project>"
```
- CI pipeline pass rate for the release branch
- All required stages green (build, test, security, integration)

**Testing:**
- Unit test pass rate and coverage
- Integration test results
- Performance test results vs. baseline

**Security:**
- No unresolved critical or high CVEs
- Security scan completed and approved
- Compliance attestations present

**Operational Readiness:**
- Monitoring and alerting configured for the release
- Runbooks updated for new features
- Rollback plan documented and tested

Present as a structured readiness report with GO/NO-GO recommendation.

## Examples

- "Show sprint velocity trends for the platform team" -- Analyze committed vs. completed points over the last N sprints
- "How is our engineering investment split between features and bugs?" -- Calculate investment allocation with recommendations
- "Help plan Sprint 24 based on our capacity" -- Calculate available capacity and recommend story point commitment
- "Is the checkout-service v2.1 ready to release?" -- Run full readiness assessment with go/no-go recommendation
- "Why are our sprints always over-committed?" -- Analyze estimation accuracy and scope change patterns

## Performance Notes

- Sprint analytics require consistent use of story points across the team -- mixed estimation methods reduce accuracy.
- Investment allocation analysis needs accurate issue labeling -- unlabeled issues default to "unclassified" and skew results.
- Capacity forecasts should account for context-switching overhead (typically 10-20% of engineering time).
- Release readiness assessments should run at least 24 hours before the planned release date.

## Troubleshooting

### Velocity Data Inconsistent
- Verify story points are assigned before sprint start (not mid-sprint)
- Check that completed stories are marked done within the sprint, not after
- Ensure the issue tracker integration is syncing correctly

### Investment Allocation Missing Categories
- Check issue labeling conventions -- all issues should have a type (feature, bug, tech debt)
- Review the mapping between issue tracker labels and SEI categories
- Add default categorization rules for unlabeled issues

### Release Readiness Check Incomplete
- Verify all pipeline stages have run for the release branch
- Check that security scan results are available for the release artifacts
- Ensure monitoring configuration has been validated in staging
