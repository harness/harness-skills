# Template Usage Report Templates

## Template Usage Report

```markdown
## Template Usage Report

**Template:** <template_name>
**Identifier:** <template_id>
**Type:** <Step | Stage | Pipeline | StepGroup>
**Scope:** <Account | Org | Project>
**Stable Version:** <version>

### Summary

| Metric | Count |
|--------|-------|
| Total References | <n> |
| Pipelines Using | <n> |
| Templates Using | <n> |
| Projects | <n> |

### Usage by Project

| Project | Org | Pipelines | Templates |
|---------|-----|-----------|-----------|
| <project> | <org> | <n> | <n> |

### Detailed References

| Entity | Type | Project | Version Used |
|--------|------|---------|-------------|
| <name> | Pipeline | <project> | <version> |
| <name> | Template | <project> | <version> |
```

## Impact Analysis Report

```markdown
## Template Update Impact Analysis

**Template:** <template_name>
**Current Version:** <current>
**Proposed Version:** <proposed>

### Impact Summary

| Impact Level | Count | Action Required |
|-------------|-------|-----------------
| Direct (Pipelines) | <n> | Test after update |
| Indirect (Templates) | <n> | Update version references |
| Total Affected | <n> | |

### Affected Entities

| Entity | Type | Version Used | Required Action |
|--------|------|-------------|-----------------|
| <name> | <type> | <version> | <action> |

### Recommended Update Strategy

1. Create new version (do not update stable yet)
2. Test with 2-3 non-production pipelines
3. Update dependent templates first
4. Gradual rollout by org/project
5. Mark new version as stable after validation
```

## Unused Templates Report

```markdown
## Unused Templates Report

**Scope:** <scope>
**Analysis Date:** <date>

### Templates with No References

| Template | Type | Scope | Last Modified |
|----------|------|-------|---------------|
| <name> | <type> | <scope> | <date> |

### Recommendations

- Templates unused for 6+ months: consider deletion
- Recently created templates: may be in development, verify first
- Archive template YAML before deleting for records
```
