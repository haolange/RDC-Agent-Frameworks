#!/usr/bin/env bash
#
# RDC Debugger Hook Runner for Bash
#
# DESCRIPTION:
#   Bash wrapper for running RDC debugger hooks in the IDE context.
#   This script provides a convenient way to execute hook commands that were
#   originally designed for CLI usage in the copilot-cli platform.
#
# USAGE:
#   ./run-hook.sh <hook-name> [options]
#
# HOOK NAMES:
#   session-start       Run shared harness preflight
#   pretool-live        Validate dispatch readiness (requires env vars)
#   posttool-artifact   Validate artifact writes
#   write-bugcard       Validate BugCard schema
#   write-skeptic       Validate skeptic signoff format
#   stop-gate           Run finalization gate
#   stop-gate-force     Run finalization gate with force flag
#
# OPTIONS:
#   -f, --file PATH     Path to output file (for write-bugcard/write-skeptic)
#   -r, --root PATH     Path to debugger root directory
#   -h, --help          Show this help message
#
# EXAMPLES:
#   # Run preflight check
#   ./run-hook.sh session-start
#
#   # Validate a BugCard file
#   export DEBUGGER_RUN_ROOT="/path/to/case/runs/run_001"
#   ./run-hook.sh write-bugcard -f common/knowledge/library/bugcards/my-bugcard.yaml
#
#   # Run finalization gate
#   export DEBUGGER_RUN_ROOT="/path/to/case/runs/run_001"
#   ./run-hook.sh stop-gate
#
# ENVIRONMENT VARIABLES:
#   DEBUGGER_RUN_ROOT         Path to run directory
#   DEBUGGER_CASE_ROOT        Path to case directory
#   DEBUGGER_OWNERSHIP_LEASE  Ownership lease reference
#   DEBUGGER_OWNER_AGENT      Owner agent ID
#   DEBUGGER_TARGET_ACTION    Target action class
#   DEBUGGER_WORKFLOW_STAGE   Current workflow stage
#   TOOL_OUTPUT_FILE          Path to tool output file
#
# PREREQUISITES:
#   - Python 3.8 or later
#   - PyYAML installed (pip install pyyaml)
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;90m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default values
DEBUGGER_ROOT=""
TOOL_OUTPUT_FILE=""
HOOK_NAME=""

# Help message
show_help() {
    sed -n '/^#/,/^#$/p' "$0" | sed 's/^# //; s/^#$//'
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -r|--root)
            DEBUGGER_ROOT="$2"
            shift 2
            ;;
        -f|--file)
            TOOL_OUTPUT_FILE="$2"
            shift 2
            ;;
        -*)
            echo -e "${RED}Error: Unknown option $1${NC}" >&2
            echo "Use -h or --help for usage information" >&2
            exit 1
            ;;
        *)
            if [[ -z "$HOOK_NAME" ]]; then
                HOOK_NAME="$1"
            else
                echo -e "${RED}Error: Unknown argument $1${NC}" >&2
                exit 1
            fi
            shift
            ;;
    esac
done

# Validate hook name
VALID_HOOKS=("session-start" "pretool-live" "posttool-artifact" "write-bugcard" "write-skeptic" "stop-gate" "stop-gate-force")

if [[ -z "$HOOK_NAME" ]]; then
    echo -e "${RED}Error: Hook name is required${NC}" >&2
    echo "Valid hooks: ${VALID_HOOKS[*]}" >&2
    exit 1
fi

valid_hook=false
for hook in "${VALID_HOOKS[@]}"; do
    if [[ "$hook" == "$HOOK_NAME" ]]; then
        valid_hook=true
        break
    fi
done

if [[ "$valid_hook" == false ]]; then
    echo -e "${RED}Error: Invalid hook name '$HOOK_NAME'${NC}" >&2
    echo "Valid hooks: ${VALID_HOOKS[*]}" >&2
    exit 1
fi

# Determine debugger root
if [[ -z "$DEBUGGER_ROOT" ]]; then
    # Navigate: hooks -> copilot-ide -> platforms -> debugger root
    DEBUGGER_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
fi

# Validate debugger root
if [[ ! -d "$DEBUGGER_ROOT" ]]; then
    echo -e "${RED}Error: Debugger root directory not found: $DEBUGGER_ROOT${NC}" >&2
    exit 1
fi

DISPATCH_SCRIPT="$DEBUGGER_ROOT/common/hooks/utils/codebuddy_hook_dispatch.py"

if [[ ! -f "$DISPATCH_SCRIPT" ]]; then
    echo -e "${RED}Error: Hook dispatcher not found: $DISPATCH_SCRIPT${NC}" >&2
    echo -e "${RED}Are you running from the correct directory?${NC}" >&2
    exit 1
fi

# Print header
echo -e "${CYAN}RDC Debugger Hook Runner${NC}"
echo -e "${CYAN}========================${NC}"
echo -e "${YELLOW}Hook: $HOOK_NAME${NC}"
echo -e "${GRAY}Debugger Root: $DEBUGGER_ROOT${NC}"

# Set up environment
export PYTHONIOENCODING=utf-8

# Set TOOL_OUTPUT_FILE if provided
if [[ -n "$TOOL_OUTPUT_FILE" ]]; then
    export TOOL_OUTPUT_FILE
    echo -e "${GRAY}Tool Output File: $TOOL_OUTPUT_FILE${NC}"
fi

# Check required environment variables for specific hooks
declare -A REQUIRED_VARS
case "$HOOK_NAME" in
    pretool-live)
        REQUIRED_VARS["DEBUGGER_RUN_ROOT"]="Path to run directory"
        REQUIRED_VARS["DEBUGGER_OWNERSHIP_LEASE"]="Ownership lease reference"
        REQUIRED_VARS["DEBUGGER_OWNER_AGENT"]="Owner agent ID"
        ;;
    posttool-artifact)
        REQUIRED_VARS["DEBUGGER_RUN_ROOT"]="Path to run directory"
        ;;
    write-bugcard)
        REQUIRED_VARS["DEBUGGER_RUN_ROOT"]="Path to run directory"
        if [[ -z "$TOOL_OUTPUT_FILE" ]]; then
            echo -e "${YELLOW}Warning: write-bugcard hook works best with -f or --file parameter${NC}" >&2
        fi
        ;;
    write-skeptic)
        REQUIRED_VARS["DEBUGGER_RUN_ROOT"]="Path to run directory"
        if [[ -z "$TOOL_OUTPUT_FILE" ]]; then
            echo -e "${YELLOW}Warning: write-skeptic hook works best with -f or --file parameter${NC}" >&2
        fi
        ;;
    stop-gate|stop-gate-force)
        REQUIRED_VARS["DEBUGGER_RUN_ROOT"]="Path to run directory"
        ;;
esac

# Check environment variables
MISSING_VARS=()
for var in "${!REQUIRED_VARS[@]}"; do
    if [[ -z "${!var:-}" ]]; then
        MISSING_VARS+=("$var (${REQUIRED_VARS[$var]})")
    else
        echo -e "${GRAY}$var = ${!var}${NC}"
    fi
done

if [[ ${#MISSING_VARS[@]} -gt 0 ]]; then
    echo ""
    echo -e "${YELLOW}Warning: Missing recommended environment variables:${NC}"
    for var in "${MISSING_VARS[@]}"; do
        echo -e "  ${RED}- $var${NC}"
    done
    echo ""
    echo -e "${YELLOW}Set them with: export VAR_NAME='value'${NC}"
    echo ""
fi

# Run the hook
echo ""
echo -e "${GREEN}Executing hook...${NC}"
echo -e "${GRAY}Command: python $DISPATCH_SCRIPT $HOOK_NAME${NC}"
echo ""

cd "$DEBUGGER_ROOT"

if python "$DISPATCH_SCRIPT" "$HOOK_NAME"; then
    EXIT_CODE=$?
    echo ""
    echo -e "${GREEN}Hook completed successfully (exit code: $EXIT_CODE)${NC}"
else
    EXIT_CODE=$?
    echo ""
    echo -e "${RED}Hook failed (exit code: $EXIT_CODE)${NC}"
fi

exit $EXIT_CODE
