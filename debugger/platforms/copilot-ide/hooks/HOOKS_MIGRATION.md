# Hooks Migration: copilot-cli to copilot-ide

## Overview

This document describes the migration strategy for converting the copilot-cli hooks configuration to the copilot-ide (GitHub Copilot IDE extension) format.

## Source Analysis

### Original copilot-cli hooks.json Structure

```json
{
  "version": 1,
  "hooks": {
    "sessionStart": [...],
    "preToolUse": [...],
    "postToolUse": [...],
    "agentStop": [...]
  }
}
```

### Hook Commands Analysis

| Hook Type | Command | Purpose |
|-----------|---------|---------|
| `sessionStart` | `codebuddy_hook_dispatch.py session-start` | Run shared harness preflight before debugger work starts |
| `preToolUse` | `codebuddy_hook_dispatch.py pretool-live` | Validate dispatch readiness and capability token before live investigation |
| `postToolUse` | `codebuddy_hook_dispatch.py posttool-artifact` | Validate artifact writes against the shared harness capability token |
| `postToolUse` | `codebuddy_hook_dispatch.py write-bugcard` | Validate BugCard contract and schema before library write |
| `postToolUse` | `codebuddy_hook_dispatch.py write-skeptic` | Validate skeptic signoff artifact format |
| `agentStop` | `codebuddy_hook_dispatch.py stop-gate` | Finalization gate for RenderDoc/RDC GPU Debug |

### Execution Context

The CLI hooks use:
- `uv run --with pyyaml python` for Python execution with dependency management
- Relative paths from debugger root: `common/hooks/utils/codebuddy_hook_dispatch.py`
- Environment variables for context: `DEBUGGER_RUN_ROOT`, `DEBUGGER_CASE_ROOT`, `DEBUGGER_OWNERSHIP_LEASE`, etc.
- Stdin/stdout JSON communication for tool input/output

## Migration Strategy

### Platform Capability Comparison

| Feature | copilot-cli | copilot-ide |
|---------|-------------|-------------|
| Native hooks support | Yes (native-hooks tier) | Limited (pseudo-hooks only) |
| Hook configuration | hooks.json | VS Code tasks or extension settings |
| Execution context | CLI with uv | VS Code extension host |
| Environment variables | Full control | Limited/sandboxed |
| Stdin/stdout piping | Full support | Limited support |

### Migration Approach by Hook Type

#### 1. sessionStart Hook

**Status:** PARTIAL MIGRATION REQUIRED

**CLI Behavior:**
- Runs preflight checks via `codebuddy_hook_dispatch.py session-start`
- Validates binding and tool contract
- Blocks session start if checks fail

**IDE Migration Options:**

**Option A: VS Code Task (Recommended)**
- Create a VS Code task that runs the preflight check
- User manually triggers before starting debugging session
- Task output shown in VS Code terminal

**Option B: Extension Activation Hook**
- If the copilot-ide platform has a custom extension, use `onStartupFinished` activation event
- Run preflight check on extension activation

**Option C: Pseudo-Hook via Agent Instructions**
- Add preflight validation instructions to agent prompts
- Agent runs validation as first step

**Implementation:** See `.vscode/tasks.json` for Option A implementation.

#### 2. preToolUse Hook

**Status:** NOT DIRECTLY MIGRATABLE

**CLI Behavior:**
- Validates dispatch readiness before each tool use
- Checks ownership lease and capability tokens
- Can block tool execution with JSON response

**IDE Limitations:**
- GitHub Copilot IDE extension does not support pre-tool-use hooks
- Cannot intercept tool calls before execution
- Cannot block tool execution programmatically

**Alternative Approaches:**

1. **Runtime Guard Wrapper (Recommended)**
   - Wrap tool calls in validation functions
   - Agent instructions require validation before tool use
   - Use shared harness as SSOT

2. **Post-Validation Pattern**
   - Cannot block before, but can validate after
   - Flag violations in postToolUse
   - Rollback or flag invalid operations

3. **Prompt-Based Enforcement**
   - Include validation requirements in agent system prompts
   - Agent self-regulates based on harness state

#### 3. postToolUse Hooks

**Status:** PARTIAL MIGRATION POSSIBLE

**CLI Behavior:**
- Validates artifact writes
- Validates BugCard schema
- Validates skeptic signoff format

**IDE Migration:**

**Option A: VS Code Task for Validation**
- Create tasks for artifact validation
- Run manually or via keybinding after writes

**Option B: File Watcher Tasks**
- Use VS Code file watchers to trigger validation
- Validate on file save in specific directories

**Option C: Agent-Based Validation**
- Include validation steps in agent workflows
- Agent runs validators after writing artifacts

**Implementation:**
- BugCard validator: `common/hooks/validators/bugcard_validator.py`
- Skeptic validator: `common/hooks/validators/skeptic_signoff_checker.py`

#### 4. agentStop Hook

**Status:** NOT DIRECTLY MIGRATABLE

**CLI Behavior:**
- Runs finalization gate on agent stop
- Validates session evidence, signoff, action chain
- Blocks completion if validation fails

**IDE Limitations:**
- No native agent stop hook
- Cannot block agent termination

**Alternative Approaches:**

1. **Pre-Completion Validation Task**
   - Create VS Code task for finalization gate
   - Run before considering session complete
   - Manual trigger by user

2. **Session Cleanup Task**
   - Run validation during session cleanup
   - Report issues but cannot block

3. **Compliance Report Generation**
   - Generate compliance report on session end
   - Flag any violations for review

## Implementation Files

### Created Files

1. **README.md** - Hook migration status and usage instructions
2. **.vscode/tasks.json** - VS Code tasks for manual hook execution
3. **run-hook.ps1** - PowerShell wrapper for hook execution
4. **run-hook.sh** - Bash wrapper for hook execution (WSL/Git Bash)

### File Locations

```
platforms/copilot-ide/hooks/
├── HOOKS_MIGRATION.md      # This document
├── README.md               # Usage instructions
├── .vscode/
│   └── tasks.json          # VS Code tasks
├── run-hook.ps1            # PowerShell wrapper
└── run-hook.sh             # Bash wrapper
```

## Usage Instructions

### Running Hooks in VS Code

1. **Preflight Check (sessionStart equivalent):**
   - Open Command Palette (Ctrl+Shift+P)
   - Run "Tasks: Run Task"
   - Select "RDC: Preflight Check"

2. **Validate BugCard (postToolUse equivalent):**
   - After writing a BugCard file
   - Run task "RDC: Validate BugCard"
   - Select the file to validate

3. **Finalization Gate (agentStop equivalent):**
   - Before completing a session
   - Run task "RDC: Finalization Gate"
   - Review validation results

### Environment Variables

The following environment variables must be set for hooks to function:

```bash
# Required
DEBUGGER_RUN_ROOT=<path_to_run_directory>
DEBUGGER_CASE_ROOT=<path_to_case_directory>

# Optional (for preToolUse validation)
DEBUGGER_OWNERSHIP_LEASE=<lease_reference>
DEBUGGER_AGENT_ID=<agent_id>
DEBUGGER_OWNER_AGENT=<owner_agent_id>
DEBUGGER_TARGET_ACTION=<action_class>
DEBUGGER_WORKFLOW_STAGE=<workflow_stage>
```

## Limitations and Workarounds

| CLI Feature | IDE Limitation | Workaround |
|-------------|----------------|------------|
| Automatic sessionStart | No auto-hook | Manual task or agent instruction |
| Blocking preToolUse | Cannot block tools | Post-validation + agent instructions |
| Stdin JSON payload | Limited stdin access | Use environment variables or files |
| Blocking agentStop | Cannot block termination | Pre-completion validation task |

## Recommendations

1. **Use Agent Instructions**: Add validation requirements to agent system prompts
2. **Manual Validation Tasks**: Use VS Code tasks for critical validation points
3. **Shared Harness as SSOT**: Continue using `common/hooks/utils/harness_guard.py` as the single source of truth
4. **Platform Capability Alignment**: Consider copilot-ide as "pseudo-hooks" tier per `platform_capabilities.json`

## References

- Source: `platforms/copilot-cli/hooks/hooks.json`
- Shared Harness: `common/hooks/utils/harness_guard.py`
- Hook Dispatcher: `common/hooks/utils/codebuddy_hook_dispatch.py`
- Platform Capabilities: `common/config/platform_capabilities.json`
