#!/usr/bin/env pwsh
<#
.SYNOPSIS
    RDC Debugger Hook Runner for PowerShell

.DESCRIPTION
    PowerShell wrapper for running RDC debugger hooks in the IDE context.
    This script provides a convenient way to execute hook commands that were
    originally designed for CLI usage in the copilot-cli platform.

.PARAMETER HookName
    The name of the hook to run. Valid values:
    - session-start: Run shared harness preflight
    - pretool-live: Validate dispatch readiness (requires env vars)
    - posttool-artifact: Validate artifact writes
    - write-bugcard: Validate BugCard schema
    - write-skeptic: Validate skeptic signoff format
    - stop-gate: Run finalization gate
    - stop-gate-force: Run finalization gate with force flag

.PARAMETER ToolOutputFile
    Path to the output file for write-bugcard and write-skeptic hooks.
    Can be relative to debugger root or absolute.

.PARAMETER DebuggerRoot
    Path to the debugger root directory. Defaults to the directory
    containing this script's parent (platforms/copilot-ide/hooks/../../..)

.EXAMPLE
    .\run-hook.ps1 session-start

    Run preflight check before starting a debugging session.

.EXAMPLE
    $env:DEBUGGER_RUN_ROOT = "D:\Projects\...\case_001\runs\run_001"
    .\run-hook.ps1 write-bugcard -ToolOutputFile "common/knowledge/library/bugcards/my-bugcard.yaml"

    Validate a BugCard file after writing it.

.EXAMPLE
    $env:DEBUGGER_RUN_ROOT = "D:\Projects\...\case_001\runs\run_001"
    .\run-hook.ps1 stop-gate

    Run finalization gate before completing a session.

.NOTES
    File Name      : run-hook.ps1
    Author         : RDC Agent Frameworks
    Prerequisite   : PowerShell 5.1 or later, Python 3.8+, PyYAML
    Copyright      : (c) 2025
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet(
        "session-start",
        "pretool-live",
        "posttool-artifact",
        "write-bugcard",
        "write-skeptic",
        "stop-gate",
        "stop-gate-force"
    )]
    [string]$HookName,

    [Parameter(Mandatory = $false)]
    [Alias("f")]
    [string]$ToolOutputFile,

    [Parameter(Mandatory = $false)]
    [Alias("r")]
    [string]$DebuggerRoot
)

# Error action preference
$ErrorActionPreference = "Stop"

# Determine debugger root
if (-not $DebuggerRoot) {
    $scriptPath = $PSScriptRoot
    if (-not $scriptPath) {
        $scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
    }
    # Navigate: hooks/.vscode -> hooks -> copilot-ide -> platforms -> debugger root
    $DebuggerRoot = Resolve-Path (Join-Path $scriptPath "..\..\..") | Select-Object -ExpandProperty Path
}

# Validate debugger root
if (-not (Test-Path $DebuggerRoot)) {
    Write-Error "Debugger root directory not found: $DebuggerRoot"
    exit 1
}

$dispatchScript = Join-Path $DebuggerRoot "common\hooks\utils\codebuddy_hook_dispatch.py"
if (-not (Test-Path $dispatchScript)) {
    Write-Error "Hook dispatcher not found: $dispatchScript"
    Write-Error "Are you running from the correct directory?"
    exit 1
}

Write-Host "RDC Debugger Hook Runner" -ForegroundColor Cyan
Write-Host "========================" -ForegroundColor Cyan
Write-Host "Hook: $HookName" -ForegroundColor Yellow
Write-Host "Debugger Root: $DebuggerRoot" -ForegroundColor Gray

# Set up environment
$env:PYTHONIOENCODING = "utf-8"

# Set TOOL_OUTPUT_FILE if provided
if ($ToolOutputFile) {
    $env:TOOL_OUTPUT_FILE = $ToolOutputFile
    Write-Host "Tool Output File: $ToolOutputFile" -ForegroundColor Gray
}

# Check required environment variables for specific hooks
$requiredVars = @{}
switch ($HookName) {
    "pretool-live" {
        $requiredVars["DEBUGGER_RUN_ROOT"] = "Path to run directory"
        $requiredVars["DEBUGGER_OWNERSHIP_LEASE"] = "Ownership lease reference"
        $requiredVars["DEBUGGER_OWNER_AGENT"] = "Owner agent ID"
    }
    "posttool-artifact" {
        $requiredVars["DEBUGGER_RUN_ROOT"] = "Path to run directory"
    }
    "write-bugcard" {
        $requiredVars["DEBUGGER_RUN_ROOT"] = "Path to run directory"
        if (-not $ToolOutputFile) {
            Write-Warning "write-bugcard hook works best with -ToolOutputFile parameter"
        }
    }
    "write-skeptic" {
        $requiredVars["DEBUGGER_RUN_ROOT"] = "Path to run directory"
        if (-not $ToolOutputFile) {
            Write-Warning "write-skeptic hook works best with -ToolOutputFile parameter"
        }
    }
    "stop-gate" {
        $requiredVars["DEBUGGER_RUN_ROOT"] = "Path to run directory"
    }
    "stop-gate-force" {
        $requiredVars["DEBUGGER_RUN_ROOT"] = "Path to run directory"
    }
}

# Check environment variables
$missingVars = @()
foreach ($var in $requiredVars.Keys) {
    $value = [Environment]::GetEnvironmentVariable($var)
    if (-not $value) {
        $missingVars += "$var ($($requiredVars[$var]))"
    } else {
        Write-Host "$var = $value" -ForegroundColor DarkGray
    }
}

if ($missingVars.Count -gt 0) {
    Write-Host ""
    Write-Warning "Missing recommended environment variables:"
    foreach ($var in $missingVars) {
        Write-Host "  - $var" -ForegroundColor Red
    }
    Write-Host ""
    Write-Host "Set them with: `$env:VAR_NAME = 'value'" -ForegroundColor Yellow
    Write-Host ""
}

# Build Python command
$pythonArgs = @(
    $dispatchScript,
    $HookName
)

# Run the hook
Write-Host ""
Write-Host "Executing hook..." -ForegroundColor Green
Write-Host "Command: python $($pythonArgs -join ' ')" -ForegroundColor DarkGray
Write-Host ""

try {
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = "python"
    $psi.Arguments = $pythonArgs -join " "
    $psi.WorkingDirectory = $DebuggerRoot
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.CreateNoWindow = $true

    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $psi
    $process.Start() | Out-Null

    $stdout = $process.StandardOutput.ReadToEnd()
    $stderr = $process.StandardError.ReadToEnd()
    $process.WaitForExit()

    # Output results
    if ($stdout) {
        Write-Host $stdout
    }

    if ($stderr) {
        Write-Host $stderr -ForegroundColor Red
    }

    $exitCode = $process.ExitCode

    Write-Host ""
    if ($exitCode -eq 0) {
        Write-Host "Hook completed successfully (exit code: $exitCode)" -ForegroundColor Green
    } else {
        Write-Host "Hook failed (exit code: $exitCode)" -ForegroundColor Red
    }

    exit $exitCode
}
catch {
    Write-Error "Failed to execute hook: $_"
    exit 1
}
