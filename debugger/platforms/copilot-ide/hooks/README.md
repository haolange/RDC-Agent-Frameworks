# Copilot IDE Hooks

This directory contains the migrated hooks configuration for the GitHub Copilot IDE extension platform.

## Migration Status

| Hook Type | CLI Status | IDE Status | Migration Approach |
|-----------|------------|------------|-------------------|
| `sessionStart` | Native | Manual Task | VS Code task for preflight check |
| `preToolUse` | Native | Not Available | Use agent instructions + runtime guard |
| `postToolUse` | Native | Partial | VS Code tasks for validation |
| `agentStop` | Native | Manual Task | VS Code task for finalization gate |

## Important Note

The GitHub Copilot IDE extension does not support native hooks like the CLI version. This migration provides:

1. **VS Code Tasks** for manual hook execution
2. **Wrapper Scripts** for running hook commands
3. **Documentation** on adapting workflows for IDE constraints

## Quick Start

### Prerequisites

- Python 3.8+ with PyYAML installed
- VS Code with GitHub Copilot extension
- PowerShell (Windows) or Bash (WSL/Git Bash)

### Environment Setup

Set the following environment variables in your VS Code settings or terminal:

```json
{
  "terminal.integrated.env.windows": {
    "DEBUGGER_RUN_ROOT": "${workspaceFolder}/workspace/cases/<case_name>/runs/<run_id>",
    "DEBUGGER_CASE_ROOT": "${workspaceFolder}/workspace/cases/<case_name>"
  }
}
```

### Running Hooks

#### Option 1: VS Code Tasks

1. Open Command Palette (`Ctrl+Shift+P` or `Cmd+Shift+P`)
2. Type "Tasks: Run Task"
3. Select one of the RDC tasks:
   - `RDC: Preflight Check` - Run session start validation
   - `RDC: Validate BugCard` - Validate a BugCard YAML file
   - `RDC: Validate Skeptic Signoff` - Validate skeptic signoff YAML
   - `RDC: Finalization Gate` - Run session finalization checks

#### Option 2: PowerShell Wrapper

```powershell
# Set environment variables
$env:DEBUGGER_RUN_ROOT = "D:\Projects\Native\RDX\RDC-Agent-Frameworks\debugger\workspace\cases\case_001\runs\run_001"
$env:DEBUGGER_CASE_ROOT = "D:\Projects\Native\RDX\RDC-Agent-Frameworks\debugger\workspace\cases\case_001"

# Run preflight check
.\run-hook.ps1 session-start

# Validate a BugCard file
.\run-hook.ps1 write-bugcard -ToolOutputFile "common/knowledge/library/bugcards/my-bugcard.yaml"

# Run finalization gate
.\run-hook.ps1 stop-gate
```

#### Option 3: Bash Wrapper (WSL/Git Bash)

```bash
# Set environment variables
export DEBUGGER_RUN_ROOT="/mnt/d/Projects/Native/RDX/RDC-Agent-Frameworks/debugger/workspace/cases/case_001/runs/run_001"
export DEBUGGER_CASE_ROOT="/mnt/d/Projects/Native/RDX/RDC-Agent-Frameworks/debugger/workspace/cases/case_001"

# Run preflight check
./run-hook.sh session-start

# Validate a BugCard file
./run-hook.sh write-bugcard --tool-output-file "common/knowledge/library/bugcards/my-bugcard.yaml"

# Run finalization gate
./run-hook.sh stop-gate
```

## Hook Reference

### session-start

**Purpose:** Run shared harness preflight before debugger work starts

**When to Run:** Before starting a new debugging session

**Validation:**
- Binding validation
- Runtime tool contract validation

**Exit Codes:**
- `0` - Preflight passed
- `1` - Preflight failed (check output for blockers)

### pretool-live

**Purpose:** Validate dispatch readiness and capability token before live investigation

**IDE Note:** This hook cannot be automatically triggered in the IDE. Use agent instructions to enforce validation before tool use.

**Required Environment Variables:**
- `DEBUGGER_RUN_ROOT`
- `DEBUGGER_OWNERSHIP_LEASE`
- `DEBUGGER_OWNER_AGENT`
- `DEBUGGER_TARGET_ACTION`
- `DEBUGGER_WORKFLOW_STAGE`

### posttool-artifact

**Purpose:** Validate artifact writes against the shared harness capability token

**When to Run:** After writing artifacts to the run directory

### write-bugcard

**Purpose:** Validate BugCard contract and schema before library write

**When to Run:** After writing a BugCard YAML file to `common/knowledge/library/bugcards/`

**Parameters:**
- `tool-output-file` - Path to the BugCard YAML file

### write-skeptic

**Purpose:** Validate skeptic signoff artifact format

**When to Run:** After writing a skeptic signoff file to `common/knowledge/library/sessions/<session_id>/skeptic_signoff.yaml`

**Parameters:**
- `tool-output-file` - Path to the skeptic signoff YAML file

### stop-gate

**Purpose:** Finalization gate for RenderDoc/RDC GPU Debug

**When to Run:** Before considering a debugging session complete

**Validation:**
- Tool contract validation
- Session evidence artifact
- Skeptic signoff artifact
- Action chain artifact
- Causal anchor validation
- Counterfactual validation

## Directory Structure

```
hooks/
├── README.md              # This file
├── HOOKS_MIGRATION.md     # Detailed migration documentation
├── .vscode/
│   └── tasks.json         # VS Code tasks configuration
├── run-hook.ps1           # PowerShell wrapper script
└── run-hook.sh            # Bash wrapper script
```

## Troubleshooting

### "Cannot find codebuddy_hook_dispatch.py"

Ensure you're running the hook from the debugger root directory:
```
D:\Projects\Native\RDX\RDC-Agent-Frameworks\debugger>
```

### "Missing PyYAML dependency"

Install PyYAML:
```bash
pip install pyyaml
```

Or use the wrapper scripts which handle the dependency.

### "DEBUGGER_RUN_ROOT not set"

Set the environment variable before running hooks:
```powershell
$env:DEBUGGER_RUN_ROOT = "<path_to_run_directory>"
```

### Validation fails but should pass

Check that all required artifacts exist:
- `run.yaml` in run directory
- `session_evidence.yaml` (for stop-gate)
- `skeptic_signoff.yaml` (for stop-gate)
- `action_chain.jsonl` (for stop-gate)

## Integration with Agent Workflows

Since the IDE cannot automatically trigger hooks, add these instructions to your agent prompts:

```markdown
## Validation Requirements

Before starting work:
1. Run preflight check via VS Code task "RDC: Preflight Check"

After writing BugCards:
1. Run "RDC: Validate BugCard" task
2. Ensure validation passes before proceeding

Before completing session:
1. Run "RDC: Finalization Gate" task
2. Address any validation failures
3. Ensure all required artifacts are present
```

## References

- [Hooks Migration Guide](./HOOKS_MIGRATION.md)
- [Shared Harness Documentation](../../../common/hooks/README.md)
- [Platform Capabilities](../../../common/config/platform_capabilities.json)
