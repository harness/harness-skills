# Scope Establishment Playbook

Use this playbook for any skill that lists, creates, updates, deletes, or executes Harness resources.

## Goal

Establish the correct Harness scope before making MCP calls so the skill does not operate on the wrong account, organization, or project.

## Workflow

1. **Parse explicit context first**
   - Look for `account`, `org`, `project`, `identifier`, and environment names in the user's request.
   - If the user provides a Harness UI URL, extract scope values from it.

2. **Determine the scope level**
   - Account scope: no org/project
   - Org scope: org only
   - Project scope: org + project

3. **Ask only for what is missing**
   - Do not ask for org/project if the request or URL already provides them.
   - If the skill can work at multiple scope levels, recommend the safest scope first.

4. **Restate the active scope before writes**
   - Before `harness_create`, `harness_update`, `harness_delete`, or `harness_execute`, summarize the scope in one line.
   - Example: `Working in org=default, project=payments.`

5. **Do not invent defaults**
   - Never assume `default` org/project unless the user explicitly confirmed it or a provided URL resolved to it.

## Recommended Prompt Pattern

Use a concise confirmation like:

> I can do that. I need the Harness scope first: which org and project should this resource live in?

If there are multiple valid options, lead with a recommendation:

> Recommend project scope unless you need this shared across teams. Which should I use?  
> A) Project scope  
> B) Org scope  
> C) Account scope

## Output Contract

Before the first mutating call, include:

- requested operation
- confirmed scope
- any unresolved scope ambiguity
