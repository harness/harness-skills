# MCP Client Setup

Shared workflow for establishing the interface declared by the selected Harness skill. Most skills require MCP; some also support CLI. This playbook does not extend a skill's supported operations or assume transport parity.

## Step 1: Check for an existing transport first

Before suggesting MCP setup, check whether the user already has a working transport:

- **Harness CLI already available** → use it only if the selected skill declares CLI support and the installed command supports the needed operation. Verify access through a scoped read. For supported CLI workflows, MCP is optional; do not configure it unnecessarily.
- **MCP already available** → verify the required tool/capability and scoped read; don't add a duplicate server. Inspect only non-secret metadata such as server names, transport and client version, never dump existing client configuration or credentials.
- **Neither usable** → explain the interfaces the selected skill supports and ask which to configure. For CLI, consult the installed command's help and official secure authentication guidance; never place credentials in command arguments.

Honor the user's explicit choice. A denied operation is not permission to switch transports (see [Step 4](#step-4-after-setup-verify-read-only-in-scope)). For a genuinely unavailable/unsupported capability, stop and offer another interface only if the selected skill declares it, its capability is verified and the user explicitly approves. Never use that path to bypass authentication, authorization or governance.

## Step 2: Choose hosted vs. local MCP

Two supported options exist; pick based on what the account and client actually support, not by default:

| Option | When to use | Auth |
|---|---|---|
| **Hosted MCP** (`https://mcp.harness.io/mcp`) | Account has the hosted service enabled, and the client supports remote MCP servers | Harness Platform OAuth — never `HARNESS_API_KEY` |
| **Local / self-hosted** (`npx harness-mcp-v2` or a built server) | Hosted isn't enabled for the account, or the client only supports local/stdio servers | `HARNESS_API_KEY` (PAT/SAT) in the client's env config |

The server's hosted setup documentation lists per-account enablement through Harness Support. Verify current availability rather than promising access. If hosted access is unavailable or unconfirmed, ask the user/admin; offer local setup as an explicitly approved alternative, not an automatic installation. Local setup still requires valid permissions and credentials.

## Step 3: Apply client config with approval

Get explicit approval before writing or changing any client config file (e.g. `claude_desktop_config.json`, `.cursor/mcp.json`):

- Show only the proposed non-secret configuration diff, using a credential-reference placeholder (`"HARNESS_API_KEY": "<your-harness-api-key>"`), never a real token. Never put a key in a shell command, URL, or CLI flag — an authorized user supplies credentials through the client's documented secure mechanism outside the conversation. Prefer environment/secret-manager references or restricted user-local configuration; never commit credentials to project files or dump existing client configuration.
- Preserve every other entry already in the file; add or edit only the `harness`/`harness-hosted` key being configured. Don't reformat or reorder unrelated config.
- For local setups, verify the executable exists and its installed version. GUI clients may need an absolute executable path because they do not inherit shell search paths; don't copy the full shell environment into config. Explain and obtain permission before installing or changing a package version.
- For hosted setups, use the current client's documented OAuth flow. Don't invent OAuth identifiers/config fields or substitute an API-key variable for an OAuth-only endpoint. Follow the official server/client links below for the actual client version rather than copying another editor's schema.
- After changes, follow the client's reload/restart procedure. A missing tool can indicate a launch, configuration, capability or reload problem; confirm which before attributing it to authentication.

## Step 4: After setup, verify read-only in scope

Follow [scope-establishment.md](scope-establishment.md), then perform a read-only operation declared by the selected skill within that confirmed scope. Do not broaden to account-wide inventory or write a test resource. Discover tool/resource names through the installed schema or skill's Tools table; `harness_describe` is local schema discovery, not proof of authentication. A successful scoped API read establishes access only to that operation, not future write permissions.

If the call fails, distinguish the cause before reacting:

| Symptom | Likely cause | Response |
|---|---|---|
| Tool/server not found at all | Client hasn't reloaded config, or config wasn't saved to the right file/location | Confirm the file path and restart the client; this is not a credential problem |
| `401 Unauthorized` | Missing/expired/invalid credential, or hosted OAuth not completed | Re-check the credential reference or redo the OAuth flow; don't switch to the other transport to route around it |
| `403 Forbidden` | Credential is valid but lacks RBAC permission for the resource/scope | Report the permission gap; ask an admin to grant it, don't retry with a broader scope guess |

For authentication, authorization or governance denial, report the cause and stop; do not switch transport or escalate scope to bypass it. A missing/unsupported tool follows Step 1's explicit capability-and-approval handoff, not an automatic fallback.

## Official references

- [Harness MCP server source (`harness/mcp-server`)](https://github.com/harness/mcp-server) — quick start, hosted vs. local, client configuration examples
- [`harness-mcp-v2` on npm](https://www.npmjs.com/package/harness-mcp-v2) — published package used by the `npx`/global-install setup
- [Harness API Quickstart](https://developer.harness.io/docs/platform/automation/api/api-quickstart/) — generating a PAT/SAT for `HARNESS_API_KEY`
