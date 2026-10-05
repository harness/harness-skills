# Pull request template (flag cleanup)

Copy into the application-repo PR.

```markdown
## Summary

Remove feature flag `<flag_key>` and hardcode treatment `<forward_treatment>`.

## Why this is safe

- FME org/project: `<org>` / `<project>`
- Critical environments checked: `<env names>`
- `lastImpressionAt` stale in all critical envs since deploy: yes | no | unknown
- No active experiments on this flag
- Readiness verdict: safe | caution | blocked
- Forward treatment confirmed from FME (not SDK default in code)

## Code changes

- Kept: `<behavior matching forward treatment>`
- Removed: `<dead branches, tests, constants>`

## FME follow-up

- [ ] Archive flag after merge/deploy
- [ ] Other repos may still evaluate this flag: `<unknown | listed>`

## Test plan

- [ ] Flag key grep is clean in this repo
- [ ] Tests updated and passing
```
