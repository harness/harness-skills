---
name: manage-cde
description: >-
  Manage Harness Cloud Development Environments (CDE) via MCP. Configure on-demand development
  environments with pre-installed tooling, design standardized workspace templates for teams,
  set up auto-hibernation and cost controls, and manage environment lifecycle. Use when asked
  to set up cloud dev environments, create workspace templates, configure remote development,
  or manage CDE lifecycle and costs. Trigger phrases: cloud dev environment, CDE, remote
  development, workspace template, dev environment, gitpod, codespace, auto-hibernation,
  developer workspace, ephemeral environment.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Manage CDE

Configure on-demand Cloud Development Environments with workspace templates, auto-hibernation, and cost controls in Harness.

## Instructions

### Step 1: Establish Scope

Confirm the user's org, project, team, and technology stack.

```
Call MCP tool: harness_list
Parameters:
  resource_type: "project"
  org_id: "<organization>"
```

### Step 2: Identify the CDE Task

Determine which workflow the user needs:

1. **On-Demand Environment Setup** -- Environment templates with resource allocation and lifecycle
2. **Workspace Standardization** -- Pre-configured templates per team/stack with consistent tooling

### Step 3: Configure On-Demand Environments

Gather from the user:
- Technology stack and runtime version
- Cloud provider (AWS, GCP, Azure)
- IDE preference (VS Code browser, VS Code SSH, JetBrains Gateway)
- Git provider for auto-clone on start

Design the environment template:

**Resource allocation:**
- Default size (e.g., 4 vCPU, 8GB RAM) with upgrade options
- Persistent storage for workspace files
- Ephemeral storage that clears on stop

**Lifecycle configuration:**
- Provisioning trigger: developer request, PR creation, or branch push
- Start time target (under 30 seconds recommended)
- Auto-stop after idle timeout (default 30 minutes)
- Persistent mode option for long-running work

**Integrations:**
- Secret injection from Harness Secrets, Vault, or cloud secret managers
- Supporting services (databases, caches, message queues) via Docker Compose or Kubernetes
- Custom access URL pattern (e.g., {user}-{env}.dev.company.com)

**Cost controls:**
- Daily cost cap per environment
- Team-level monthly budget
- Auto-hibernation for idle environments

### Step 4: Create Workspace Templates

When standardizing across teams, create templates per role/stack:

**Backend Service Developer:**
- Runtime, build tools, testing frameworks
- Database clients, API testing tools
- Pre-configured debugger and linter

**Frontend Developer:**
- Node.js runtime, package manager
- Browser dev tools, component library
- Hot-reload and preview server

**Full-Stack Developer:**
- Combined backend + frontend tooling
- Docker Compose for local service mesh
- API mocking tools

**Platform / DevOps Engineer:**
- kubectl, Helm, Terraform, cloud CLIs
- Monitoring and observability tools
- Infrastructure testing frameworks

Each template should include:
- Base image and pre-installed tools
- IDE extensions/plugins list
- Git hooks and code formatting config
- Environment variables and secrets

## Examples

- "Set up cloud dev environments for our backend team" -- Configure on-demand CDEs with Java/Go tooling and auto-hibernation
- "Create workspace templates for frontend and backend developers" -- Standardized templates with stack-specific tooling
- "Configure auto-hibernation to reduce CDE costs" -- Set idle timeout and daily cost caps
- "Provision a dev environment when a PR is created" -- Configure PR-triggered ephemeral environments

## Performance Notes

- Start time under 30 seconds requires pre-built images -- avoid installing tools at startup.
- Auto-hibernation timeout should balance developer productivity (too short = friction) with cost (too long = waste).
- Persistent storage should be sized for the repo plus build artifacts -- undersizing causes build failures.
- Pre-pull common base images to reduce cold start times.

## Troubleshooting

### Environment Slow to Start
- Check if the base image is being pulled from a remote registry -- use a local cache or pre-pull
- Reduce the number of tools installed at startup -- bake them into the base image
- Verify network connectivity to the Git provider for auto-clone

### Environment Auto-Stopping Too Aggressively
- Increase the idle timeout for developers doing research or design work
- Enable persistent mode for long-running tasks
- Check that IDE keepalive signals are reaching the CDE controller

### Cost Overruns
- Review environments that have been running for more than 24 hours
- Check for orphaned environments from deleted branches
- Verify auto-hibernation is enabled for all non-production environments
