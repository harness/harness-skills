---
name: optimize-pipeline
description: >-
  Optimize Harness CI/CD pipeline performance via MCP. Configure parallel test execution with
  Test Intelligence, design multi-layer caching strategies, analyze pipeline bottlenecks with
  stage-level timing breakdowns, optimize cache hit rates, and design monorepo CI pipelines
  with selective builds. Use when asked to speed up pipelines, improve cache hit rates, set up
  parallel testing, optimize build times, or configure monorepo builds. Do NOT use for creating
  new pipelines (use create-pipeline instead) or debugging failures (use debug-pipeline instead).
  Trigger phrases: pipeline speed, slow pipeline, cache hit rate, parallel tests, test intelligence,
  build optimization, caching strategy, monorepo pipeline, pipeline bottleneck, build speed.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Optimize Pipeline

Analyze and optimize Harness CI/CD pipeline performance through parallel testing, caching, bottleneck analysis, and monorepo strategies.

## Instructions

### Step 1: Establish Scope

Confirm the service, pipeline, and current performance baseline.

```
Call MCP tool: harness_list
Parameters:
  resource_type: "pipeline"
  org_id: "<organization>"
  project_id: "<project>"
```

Get recent execution timing data:

```
Call MCP tool: harness_list
Parameters:
  resource_type: "execution"
  org_id: "<organization>"
  project_id: "<project>"
  pipeline_id: "<pipeline_identifier>"
```

### Step 2: Identify the Optimization Task

Determine which optimization the user needs:

1. **Parallel Testing with Test Intelligence** -- Split tests across runners and skip unchanged tests
2. **Caching Strategy** -- Multi-layer dependency, build output, and test result caching
3. **Pipeline Bottleneck Analysis** -- Stage-level timing breakdown with recommendations
4. **Cache Hit Rate Improvement** -- Diagnose and fix low cache hit rates
5. **Monorepo CI Pipeline** -- Selective builds triggered by changed paths

### Step 3: Configure Parallel Testing with Test Intelligence

Gather from the user:
- Test framework (JUnit, pytest, Jest, Go test, etc.)
- Total test count and current runtime
- Target runtime

Design the parallel test strategy:
- Split tests across N parallel runners using Harness Test Intelligence
- Use TI to identify and skip unchanged tests based on code changes
- Configure test splitting method: by class, by file, or by timing data
- Set up test result aggregation across runners
- Track TI savings over time (tests skipped vs. total)

Configuration:
- Enable Test Intelligence in the pipeline stage
- Set parallelism level based on test count and runner capacity
- Configure test report collection from all parallel runners
- Set up failure thresholds (e.g., fail the stage if any runner fails)

### Step 4: Design Caching Strategy

Gather from the user:
- Build tool (Maven, Gradle, npm, yarn, pip, Go modules)
- Current build time breakdown (dependency download, compile, test)
- Cache key source (lockfile hash, manifest hash)

Design multi-layer caching:

**Layer 1 -- Dependencies:**
- Cache key: hash of lockfile (package-lock.json, pom.xml, go.sum)
- Cache path: dependency directory (~/.m2, node_modules, ~/.cache/pip)
- Fallback: use previous cache if exact match not found

**Layer 2 -- Build outputs:**
- Cache key: hash of source files
- Cache path: build output directory (target/, dist/, build/)
- Invalidation: any source file change

**Layer 3 -- Test results:**
- Cache key: hash of source + test files
- Cache path: test result and coverage directories
- Use to skip unchanged tests in combination with TI

Set cache TTL (recommended 7-14 days) with fallback strategy.

### Step 5: Analyze Pipeline Bottlenecks

Pull execution data and break down by stage:

```
Call MCP tool: harness_get
Parameters:
  resource_type: "execution"
  resource_id: "<execution_id>"
  org_id: "<organization>"
  project_id: "<project>"
```

For each stage, identify:
- Duration vs. pipeline total (find the longest stages)
- Queue time vs. execution time (runner availability issues)
- Sequential stages that could run in parallel
- Steps that download large artifacts repeatedly

Produce a prioritized optimization list ranked by time savings.

### Step 6: Design Monorepo CI Pipeline

Gather from the user:
- Number of services and their directories
- Shared libraries and their dependents
- Build tool

Design selective builds:
- Use path-based triggers: only build services with changed files
- Build shared libraries when they change, then rebuild all dependents
- Run integration tests only when cross-service dependencies change
- Use a dependency graph to determine the minimal build set

## Examples

- "My pipeline takes 45 minutes, help me speed it up" -- Analyze bottlenecks and recommend parallel testing, caching, and stage reordering
- "Set up parallel tests with Test Intelligence" -- Configure TI with test splitting across N runners
- "Improve our cache hit rate" -- Diagnose cache key configuration and fix common misses
- "Design a CI pipeline for our monorepo with 5 services" -- Configure path-based triggers with selective builds
- "Our builds download dependencies every time" -- Design multi-layer caching strategy with fallback

## Performance Notes

- Test Intelligence needs 2-3 full test runs to build its initial model -- first runs will execute all tests.
- Cache keys should be based on lockfiles, not timestamps -- timestamps cause unnecessary cache misses.
- Parallelism beyond runner capacity causes queuing -- profile available runner capacity before increasing parallelism.
- Monorepo path triggers should include shared library directories to avoid missing transitive changes.

## Troubleshooting

### Test Intelligence Not Skipping Tests
- Verify TI is enabled and has completed baseline runs
- Check that the test framework is supported by Harness TI
- Ensure test report format is correctly configured for the framework

### Cache Misses on Every Build
- Check cache key configuration -- keys should use file hashes, not timestamps
- Verify cache path matches the actual dependency directory
- Check that the cache storage backend is accessible from all runners

### Monorepo Building Everything
- Verify path-based triggers are configured correctly
- Check that the dependency graph includes shared library paths
- Ensure glob patterns in triggers match the actual directory structure
