param([switch]$Check)
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Common = Join-Path $Root "common"
$ConfigRoot = Join-Path $Common "config"
$RoleManifest = ConvertFrom-Json (Get-Content (Join-Path $ConfigRoot "role_manifest.json") -Raw)
$RolePolicy = ConvertFrom-Json (Get-Content (Join-Path $ConfigRoot "role_policy.json") -Raw)
$ModelRouting = ConvertFrom-Json (Get-Content (Join-Path $ConfigRoot "model_routing.json") -Raw)
$McpServers = ConvertFrom-Json (Get-Content (Join-Path $ConfigRoot "mcp_servers.json") -Raw)
$PlatformTargets = ConvertFrom-Json (Get-Content (Join-Path $ConfigRoot "platform_targets.json") -Raw)
$PlatformCaps = ConvertFrom-Json (Get-Content (Join-Path $ConfigRoot "platform_capabilities.json") -Raw)
$FrameworkCompliance = ConvertFrom-Json (Get-Content (Join-Path $ConfigRoot "framework_compliance.json") -Raw)
$CopyNotice = "未先将顶层 `debugger/common/` 拷入当前平台根目录的 `common/` 之前，不允许在宿主中使用当前平台模板。"
$Specs = @(
 @{ Key = "claude-code"; ManagedDirs = @(".claude", "common", "workspace"); ManagedFiles = @("README.md", "AGENTS.md") },
 @{ Key = "code-buddy"; ManagedDirs = @(".codebuddy-plugin", "agents", "skills", "hooks", "common", "workspace"); ManagedFiles = @("README.md", "AGENTS.md", ".mcp.json") },
 @{ Key = "copilot-cli"; ManagedDirs = @("agents", "skills", "hooks", "common", "workspace"); ManagedFiles = @("README.md", "AGENTS.md", ".mcp.json", ".copilot-plugin.json") },
 @{ Key = "copilot-ide"; ManagedDirs = @(".github", "references", "common", "workspace"); ManagedFiles = @("README.md", "AGENTS.md", "agent-plugin.json") },
 @{ Key = "claude-desktop"; ManagedDirs = @("references", "common", "workspace"); ManagedFiles = @("README.md", "AGENTS.md", "claude_desktop_config.json") },
 @{ Key = "manus"; ManagedDirs = @("references", "workflows", "common", "workspace"); ManagedFiles = @("README.md", "AGENTS.md") },
 @{ Key = "codex"; ManagedDirs = @(".agents", ".codex", "common", "workspace"); ManagedFiles = @("README.md", "AGENTS.md") }
)
$ForbiddenDirs = @("docs", "scripts")

function Normalize([string]$Text) {
 if ($null -eq $Text) { $Text = "" }
 $Text = $Text.Replace("`r`n", "`n").Replace("`r", "`n")
 return ($Text.TrimEnd("`n") + "`n")
}

function Write-Text([string]$Path, [string]$Text) {
 $dir = Split-Path $Path
 if ($dir) { $null = New-Item -ItemType Directory -Force $dir }
 [IO.File]::WriteAllText($Path, (Normalize $Text), [Text.UTF8Encoding]::new($true))
}
function Join-Parts([string[]]$Parts) {
 $path = $Parts[0]
 for ($i = 1; $i -lt $Parts.Count; $i++) { $path = Join-Path $path $Parts[$i] }
 return $path
}

function Package-Root([string]$Key) {
 $platformRoot = $(Join-Path $Root "platforms")
 return (Join-Path $platformRoot $Key)
}
function Common-Root([string]$Key) {
 $packageRoot = $(Package-Root $Key)
 return (Join-Path $packageRoot "common")
}
function Rel-Path([string]$FromFile, [string]$ToPath) {
 if ([string]::IsNullOrWhiteSpace($FromFile)) { throw "Rel-Path missing FromFile" }
 if ([string]::IsNullOrWhiteSpace($ToPath)) { throw "Rel-Path missing ToPath for FromFile=$FromFile" }
 try {
  $fromParts = [IO.Path]::GetFullPath((Split-Path $FromFile -Parent)).TrimEnd("\\").Split("\\")
  $toParts = [IO.Path]::GetFullPath($ToPath).TrimEnd("\\").Split("\\")
 } catch {
  throw "Rel-Path invalid path. from=`"$FromFile`" to=`"$ToPath`""
 }
 if ($fromParts[0] -ne $toParts[0]) { return ($ToPath.Replace("\\", "/")) }
 $i = 0
 while ($i -lt $fromParts.Count -and $i -lt $toParts.Count -and $fromParts[$i] -eq $toParts[$i]) { $i++ }
 $parts = @()
 for ($j = $i; $j -lt $fromParts.Count; $j++) { $parts += ".." }
 for ($j = $i; $j -lt $toParts.Count; $j++) { $parts += $toParts[$j] }
 if ($parts.Count -eq 0) { return "." }
 return ([string]::Join("/", $parts))
}
function Common-Ref([string]$Key, [string]$FromFile, [string[]]$Parts) {
 $commonRoot = $(Common-Root $Key)
 $joined = $(Join-Parts $Parts)
 if ([string]::IsNullOrWhiteSpace($commonRoot)) { throw "Common-Ref missing commonRoot for key=$Key" }
 if ([string]::IsNullOrWhiteSpace($joined)) { throw "Common-Ref missing joined path for key=$Key" }
 $target = $(Join-Path $commonRoot $joined)
 return $(Rel-Path $FromFile $target)
}
function Add-Expected($Table, [string]$Path, [string]$Text) { $Table[$Path] = $(Normalize $Text) }
function Roles() { return @($RoleManifest.roles) }

function Get-Role([string]$AgentId) {
 foreach ($role in (Roles)) { if ($role.agent_id -eq $AgentId) { return $role } }
 throw "missing role: $AgentId"
}

function Platform-Model([string]$PlatformKey, [string]$AgentId) {
 $profile = $ModelRouting.role_profiles.$AgentId
 return $ModelRouting.profiles.$profile.platform_rendering.$PlatformKey
}

function Role-Style([string]$AgentId) {
 $profile = $RolePolicy.roles.$AgentId.model_profile
 return $RolePolicy.model_profiles.$profile
}

function Role-Targets([string]$PlatformKey, [string]$AgentId) {
 $targets = @()
 foreach ($targetId in $RolePolicy.roles.$AgentId.delegates_to) {
 $targetRole = $(Get-Role $targetId)
 $fileName = $targetRole.platform_files.$PlatformKey
 if ($fileName) { $targets += [IO.Path]::GetFileNameWithoutExtension($fileName) }
 }
 return $targets
}

function Role-Skill-Ref([string]$PlatformKey, [string]$FromFile, $Role) {
 return Common-Ref $PlatformKey $FromFile @($Role.role_skill_path.Split("/"))
}

function Role-Skill-DirName($Role) {
 return Split-Path (Split-Path $Role.role_skill_path -Parent) -Leaf
}

function Compliance-Profile([string]$PlatformKey) {
 return $FrameworkCompliance.platforms.$PlatformKey
}

function Platform-Compliance-Notes([string]$PlatformKey) {
 $profile = $(Compliance-Profile $PlatformKey)
 $notes = New-Object System.Collections.Generic.List[string]
 if ($profile.enforcement_mode -eq "audit_only_gate") {
  $null = $notes.Add("- 当前宿主没有 native hooks；只有生成 `artifacts/run_compliance.yaml` 且 `status=passed` 后，结案才算合规。")
 } elseif ($profile.enforcement_mode -eq "workflow_audit_gate") {
  $null = $notes.Add("- 当前宿主按 `workflow_stage` 降级运行；最终仍必须生成 `artifacts/run_compliance.yaml` 才算合规结案。")
  $null = $notes.Add("- 不得在该宿主上模拟实时 multi-agent handoff。")
 } else {
  $null = $notes.Add("- native hooks 会阻断未通过 gate 的结案；同时仍要求生成 `artifacts/run_compliance.yaml` 作为统一合规裁决。")
 }
 return @($notes)
}

function Role-Compliance-Notes([string]$PlatformKey, [string]$AgentId) {
 $profile = $(Compliance-Profile $PlatformKey)
 $notes = New-Object System.Collections.Generic.List[string]
 if ($AgentId -eq "team_lead") {
  if ($profile.enforcement_mode -eq "audit_only_gate") {
   $null = $notes.Add("在 `run_compliance.yaml(status=passed)` 生成前，你只能输出阶段性 brief，不得宣称最终裁决。")
  } else {
   $null = $notes.Add("只有在 session artifacts 完整且 gate/audit 通过后，你才能输出最终裁决。")
  }
 }
 if ($AgentId -eq "curator_agent") {
  if ($profile.enforcement_mode -eq "audit_only_gate") {
   $null = $notes.Add("在 `run_compliance.yaml(status=passed)` 生成前，你只能产出 draft report，不得把报告视为正式结案。")
  } else {
   $null = $notes.Add("只有在 `session_evidence.yaml`、`skeptic_signoff.yaml`、`action_chain.jsonl` 完整后，你才能产出 final report。")
  }
 }
 if ($profile.coordination_mode -eq "workflow_stage") {
  $null = $notes.Add("当前平台只允许 `workflow_stage`；不得模拟实时 team-agent 并发 handoff。")
 }
 return @($notes)
}

function Role-Entry-Notice($Role) {
 if ($Role.formal_user_entry) {
 return '该角色是当前 framework 的唯一正式用户入口。正常用户请求必须从 `team_lead` 发起。'
 }
 return '该角色默认是 internal/debug-only specialist。正常用户请求应先交给 `team_lead` 路由，只有调试 framework 本身时才直接使用该角色。'
}

function Yaml-Block($Pairs) {
 $rows = New-Object System.Collections.Generic.List[string]
 $null = $rows.Add("---")
 foreach ($key in $Pairs.Keys) {
 $value = $Pairs[$key]
 if ($null -eq $value) { continue }
 if ($value -is [Array]) {
 if ($value.Count -eq 0) { continue }
 $null = $rows.Add("${key}:")
 foreach ($item in $value) { $null = $rows.Add(" - $item") }
 continue
 }
 if ($value -eq "") { continue }
 $null = $rows.Add("${key}: `"$value`"")
 }
 $null = $rows.Add("---")
 return ($rows -join "`n")
}

function Common-Placeholder-Files([string]$PlatformKey) {
 $root = $(Common-Root $PlatformKey)
 $expected = @{}
 Add-Expected $expected (Join-Path $root "README.md") @'
# Platform Local Common Placeholder

当前目录是平台本地 `common/` 的最小占位目录，不是正式运行时内容。

使用方式：

1. 选择一个 `debugger/platforms/<platform>/` 模板。
2. 将仓库根目录 `debugger/common/` 整体拷贝到该平台根目录的 `common/`，覆盖当前目录。
3. 完成覆盖后，再在对应宿主中打开该平台根目录使用。

约束：

- 平台内所有 skill、hooks、agents、config 只允许引用当前平台根目录的 `common/`。
- 平台内运行时工作区固定为当前平台根目录同级的 `workspace/`。
- 未完成覆盖前，当前平台模板不可用。
- 不为未覆盖状态提供伪完整 placeholder 文件；正式共享正文只来自顶层 `debugger/common/`。
'@
 return $expected
}
function Workspace-Placeholder-Files([string]$PlatformKey) {
 $workspaceRoot = Join-Path (Package-Root $PlatformKey) "workspace"
 $expected = @{}
 Add-Expected $expected (Join-Path $workspaceRoot "README.md") @'
# Platform Local Workspace Placeholder

当前目录是平台本地 `workspace/` 运行区骨架。

用途：

- 存放 `case_id/run_id` 级运行现场
- 承载 `captures/`、`screenshots/`、`artifacts/`、`logs/`、`notes/`
- 承载第二层交付物 `reports/report.md` 与 `reports/visual_report.html`

约束：

- 这里不是共享真相；共享真相仍由同级 `common/` 提供。
- `common/` 中的 shared prompt / skill / docs 应通过 `../workspace` 引用当前目录。
- 模板仓库只保留占位骨架，不提交真实运行产物。
'@
 Add-Expected $expected (Join-Path $workspaceRoot "cases\README.md") @'
# Workspace Cases Placeholder

当前目录用于承载运行时 case。

目录约定：

```text
cases/
  <case_id>/
    case.yaml
    runs/
      <run_id>/
        run.yaml
        artifacts/
        logs/
        notes/
        captures/
        screenshots/
        reports/
```

规则：

- `case_id` 是问题实例/需求线程的稳定标识。
- `run_id` 承担 debug version。
- 第一层 session artifacts 仍写入同级 `common/knowledge/library/sessions/`；`workspace/` 不复制 gate 真相。
'@
 return $expected
}
function Readme([string]$PlatformKey) {
 $caps = $PlatformCaps.platforms.$PlatformKey
 $target = $PlatformTargets.platforms.$PlatformKey
 $surfaces = [string]::Join(", ", @($target.native_surfaces))
 $lines = @(
 "# $($caps.display_name) Template",
 "",
 "当前目录是 $($caps.display_name) 的 platform-local 模板。Agent 的目标是使用 RenderDoc/RDC platform tools 调试 GPU 渲染问题。",
 "",
 "使用方式：",
 "",
 "1. 将仓库根目录 `debugger/common/` 整体拷贝到当前平台根目录的 `common/`，覆盖占位内容。",
 "2. 在当前平台根目录的 `common/config/platform_adapter.json` 中配置 `paths.tools_root`。",
 "3. 确认 `validation.required_paths` 在 `<resolved tools_root>/` 下全部存在。",
 "4. 使用当前平台根目录同级的 `workspace/` 作为运行区。",
 "5. 完成覆盖后，再在对应宿主中打开当前平台根目录。",
 "6. 正常用户请求从 `team_lead` 发起；其他 specialist 默认是 internal/debug-only。",
 "",
 "约束：",
 "",
 "- `common/` 默认只保留一个占位文件；正式共享正文仍由顶层 `debugger/common/` 提供，并由用户显式拷入。",
 "- 未完成 `debugger/common/` 覆盖前，当前平台模板不可用。",
 "- 未完成 `platform_adapter.json` 配置或 `tools_root` 校验前，Agent 必须拒绝执行依赖平台真相的工作。",
 "- `workspace/` 预生成空骨架；真实运行产物在平台使用阶段按 case/run 写入。",
 "- 维护者若重跑 scaffold，必须继续产出 platform-local `common/` 最小占位目录，不得回退到跨级引用。"
 )
 foreach ($note in $(Platform-Compliance-Notes $PlatformKey)) { $lines += $note }
 return ($lines -join "`n")
}

function PlatformAgentsMd([string]$PlatformKey, [string]$TargetFile) {
 $p1 = "common/AGENT_CORE.md"
 $p2 = "common/config/platform_adapter.json"
 $p3 = "common/skills/renderdoc-rdc-gpu-debug/SKILL.md"
 $p4 = "common/docs/platform-capability-model.md"
 $p5 = "common/docs/model-routing.md"
 $lines = @(
 "# $($PlatformCaps.platforms.$PlatformKey.display_name) Workspace Instructions",
 "",
 "当前目录是 $($PlatformCaps.platforms.$PlatformKey.display_name) 的 platform-local 模板。所有角色在进入 role-specific 行为前，都必须先服从本文件与共享 `common/` 约束。",
 "",
 "先阅读：",
 "",
 "1. $p1",
 "2. $p2",
 "3. $p3",
 "4. $p4",
 "5. $p5",
 "",
 '强制规则：',
 '',
 '- 正常用户入口只有 `team_lead`',
 '- 其他 specialist 默认是 internal/debug-only，由 `team_lead` 决定是否分派',
 '- `platform_adapter.json` 未配置或 `tools_root` 校验失败时，必须立即停止，不得继续做依赖平台真相的工作',
 '',
 "$CopyNotice",
 '',
 '运行时工作区固定为：`../workspace`'
 )
 foreach ($note in $(Platform-Compliance-Notes $PlatformKey)) { $lines += $note }
 return ($lines -join "`n")
}

function AgentBody([string]$PlatformKey, $Role, [string]$TargetFile) {
 $rolePath = $(Join-Path $(Common-Root $PlatformKey) $Role.source_prompt)
 $agentsRef = $(Join-Path $(Package-Root $PlatformKey) "AGENTS.md")
 $p0 = $(Rel-Path $TargetFile $agentsRef)
 $p1 = $(Common-Ref $PlatformKey $TargetFile @("AGENT_CORE.md"))
 $p2 = $(Rel-Path $TargetFile $rolePath)
 $p3 = $(Common-Ref $PlatformKey $TargetFile @("skills", "renderdoc-rdc-gpu-debug", "SKILL.md"))
 $p4 = $(Role-Skill-Ref $PlatformKey $TargetFile $Role)
 $entryNotice = $(Role-Entry-Notice $Role)
 $lines = @(
 "# RenderDoc/RDC Agent Wrapper",
 "",
 "当前文件是 $($PlatformCaps.platforms.$PlatformKey.display_name) 宿主入口。Agent 的目标是使用 RenderDoc/RDC platform tools 调试 GPU 渲染问题。",
 "",
 "本文件只负责宿主入口与角色元数据；共享正文统一从当前平台根目录的 `common/` 读取。",
 "",
 "$entryNotice",
 "",
 "按顺序阅读：",
 "",
 "1. $p0",
 "2. $p1",
 "3. $p2",
 "4. $p3",
 "5. $p4",
 "",
 "$CopyNotice",
 ""
 )
 foreach ($note in $(Role-Compliance-Notes $PlatformKey $Role.agent_id)) { $lines += $note }
 $lines += '运行时工作区固定为：`../workspace`'
 return ($lines -join "`n")
}

function CodeBuddyAgent($Role, [string]$TargetFile) {
 $front = Yaml-Block ([ordered]@{ agent_id = $Role.agent_id; category = $Role.category; model = $(Platform-Model "code-buddy" $Role.agent_id); delegates_to = @($RolePolicy.roles.($Role.agent_id).delegates_to) })
 return ($front + "`n`n" + $(AgentBody "code-buddy" $Role $TargetFile))
}

function ClaudeCodeAgent($Role, [string]$TargetFile) {
 $front = Yaml-Block ([ordered]@{ description = $Role.description; model = $(Platform-Model "claude-code" $Role.agent_id) })
 return ($front + "`n`n" + $(AgentBody "claude-code" $Role $TargetFile))
}

function CopilotIdeAgent($Role, [string]$TargetFile) {
 $front = Yaml-Block ([ordered]@{ description = $Role.description; model = $(Platform-Model "copilot-ide" $Role.agent_id); handoffs = @($(Role-Targets "copilot-ide" $Role.agent_id)) })
 return ($front + "`n`n" + $(AgentBody "copilot-ide" $Role $TargetFile))
}

function CopilotCliAgent($Role, [string]$TargetFile) {
 $front = Yaml-Block ([ordered]@{ description = $Role.description })
 return ($front + "`n`n" + $(AgentBody "copilot-cli" $Role $TargetFile))
}

function BaseSkillWrapper([string]$PlatformKey, [string]$TargetFile) {
 $skillRef = $(Common-Ref $PlatformKey $TargetFile @("skills", "renderdoc-rdc-gpu-debug", "SKILL.md"))
 $capRef = $(Common-Ref $PlatformKey $TargetFile @("config", "platform_capabilities.json"))
 $adapterRef = $(Common-Ref $PlatformKey $TargetFile @("config", "platform_adapter.json"))
 $lines = @(
 "# RenderDoc/RDC GPU Debug Base Skill Wrapper",
 "",
 "当前文件是 $($PlatformCaps.platforms.$PlatformKey.display_name) 的 base skill 入口。Agent 的目标是使用 RenderDoc/RDC platform tools 调试 GPU 渲染问题。",
 "",
 "本 skill 只引用当前平台根目录的 `common/`：",
 "",
 "- $skillRef",
 "- 进入任何平台真相相关工作前，必须先校验 $adapterRef",
 "- coordination_mode 与降级边界以 $capRef 的当前平台定义为准。",
 "",
 "$CopyNotice",
 "",
 '运行时 case/run 现场与第二层报告统一写入：`../workspace`'
 )
 return ($lines -join "`n")
}

function RoleSkillWrapper([string]$PlatformKey, $Role, [string]$TargetFile) {
 $baseRef = $(Common-Ref $PlatformKey $TargetFile @("skills", "renderdoc-rdc-gpu-debug", "SKILL.md"))
 $roleSkillRef = $(Role-Skill-Ref $PlatformKey $TargetFile $Role)
 $capRef = $(Common-Ref $PlatformKey $TargetFile @("config", "platform_capabilities.json"))
 $entryNotice = $(Role-Entry-Notice $Role)
 $lines = @(
 "# $($Role.display_name) Skill Wrapper",
 "",
 "当前文件是 $($PlatformCaps.platforms.$PlatformKey.display_name) 的 role skill 入口。",
 "",
 "$entryNotice",
 "",
 "先阅读：",
 "",
 "1. $baseRef",
 "2. $roleSkillRef",
 "3. $capRef",
 "",
 "$CopyNotice",
 ""
 )
 foreach ($note in $(Role-Compliance-Notes $PlatformKey $Role.agent_id)) { $lines += $note }
 $lines += '运行时 case/run 现场与第二层报告统一写入：`../workspace`'
 return ($lines -join "`n")
}

function ClaudeCodeEntry([string]$TargetFile) {
 $agentsRef = $(Join-Path $(Package-Root "claude-code") "AGENTS.md")
 $p1 = $(Rel-Path $TargetFile $agentsRef)
 $p2 = $(Common-Ref "claude-code" $TargetFile @("docs", "platform-capability-model.md"))
 $lines = @(
 "# Claude Code Entry",
 "",
 "当前目录是 Claude Code 的 platform-local 模板。Agent 的目标是使用 RenderDoc/RDC platform tools 调试 GPU 渲染问题。",
 "",
 "先阅读：",
 "",
 "1. $p1",
 "2. $p2",
 "",
 "$CopyNotice",
 "",
 '运行时工作区固定为：`../workspace`'
 )
 return ($lines -join "`n")
}

function CopilotInstructions([string]$TargetFile) {
 $agentsRef = $(Join-Path $(Package-Root "copilot-ide") "AGENTS.md")
 $p1 = $(Rel-Path $TargetFile $agentsRef)
 $p2 = $(Common-Ref "copilot-ide" $TargetFile @("docs", "platform-capability-model.md"))
 $lines = @(
 "# Copilot IDE Instructions",
 "",
 "当前目录是 Copilot IDE / VS Code 的 platform-local 模板。Agent 的目标是使用 RenderDoc/RDC platform tools 调试 GPU 渲染问题。",
 "",
 "先阅读：",
 "",
 "1. $p1",
 "2. $p2",
 "3. ../references/entrypoints.md",
 "",
 "$CopyNotice",
 "",
 '运行时工作区固定为：`../workspace`'
 )
 return ($lines -join "`n")
}

function ReferencesEntry([string]$PlatformKey, [string]$TargetFile) {
 $agentsRef = $(Join-Path $(Package-Root $PlatformKey) "AGENTS.md")
 $p1 = $(Rel-Path $TargetFile $agentsRef)
 $p2 = $(Common-Ref $PlatformKey $TargetFile @("docs", "platform-capability-model.md"))
 $lines = @(
 "# $($PlatformCaps.platforms.$PlatformKey.display_name) Entrypoints",
 "",
 "当前目录只提供宿主入口提示；运行时共享文档统一从当前平台根目录的 `common/` 读取。",
 "",
 "先阅读：",
 "",
 "1. $p1",
 "2. $p2",
 "",
 "$CopyNotice",
 ""
 )
 foreach ($note in $(Platform-Compliance-Notes $PlatformKey)) { $lines += $note }
 $lines += '运行时工作区固定为：`../workspace`'
 return ($lines -join "`n")
}

function ManusWorkflow() {
@"
# RenderDoc/RDC GPU Debug Workflow

## 目标

在低能力宿主中，用 workflow 方式完成 RenderDoc/RDC GPU Debug 的最小闭环。正常任务 intake 仍由 `team_lead` / orchestrator 语义承担。

## 阶段

1. `tools preflight`
 - 校验 `platform_adapter.json` 与 `tools_root`
2. `team_lead intake`
 - 接收用户请求，决定 triage / capture / specialist 的推进顺序
3. `triage`
 - 结构化现象、触发条件、可能的 SOP 入口
4. `capture/session`
 - 确认 `.rdc`、session、frame、event anchor
5. `specialist analysis`
 - 从 pipeline、forensics、shader、driver 四个方向收集证据
6. `skeptic`
 - 复核证据链是否足以支持结论
7. `curation`
 - 生成 BugFull / BugCard，写入 session artifacts

## workflow 约束

- Manus 不承担 custom agents / per-agent model 的宿主能力。
- `tools_root` 未配置或校验失败时必须立即停止。
- workflow 的每一阶段都必须引用共享 artifact contract。
- `workflow_stage` 是该平台的协作上限，不模拟 team-agent 实时协作。
- remote 阶段由单一 runtime owner 顺序完成 `rd.remote.connect -> rd.remote.ping -> rd.capture.open_file -> rd.capture.open_replay -> re-anchor -> collect evidence`。
- 若需要跨轮次继续调查，必须依赖可重建的 `runtime_baton`，不得凭记忆续跑 live runtime。
- 如需动态 tool discovery，应停止 workflow 并切回支持 `MCP` 的平台。
- 在 workflow 平台上，只有 `artifacts/run_compliance.yaml` 为 `status=passed` 时，结案才算合规。
"@
}
function Mcp-Payload() {
 $servers = @{}
 foreach ($prop in $McpServers.servers.PSObject.Properties) { $servers[$prop.Name] = @{ command = $prop.Value.command; args = @($prop.Value.args) } }
 return @{ servers = $servers }
}

function CodeBuddyPlugin() {
 return @{ name = "renderdoc-rdc-gpu-debug-agent"; description = "RenderDoc/RDC GPU Debug 的 Code Buddy 参考实现，要求先将顶层 debugger/common 覆盖到平台根目录 common 后再使用 hooks、skills、agents 与 MCP。"; author = @{ name = "RenderDoc/RDC GPU Debug" }; keywords = @("renderdoc", "rdc", "gpu", "debug", "mcp", "agent"); agents = "./agents/"; skills = "./skills/"; hooks = "./hooks/hooks.json"; mcpServers = "./.mcp.json" }
}

function CopilotCliPlugin() {
 return @{ name = "renderdoc-rdc-gpu-debug"; description = "Use RenderDoc/RDC platform tools to debug GPU rendering captures through platform-local agents, skills, hooks, and MCP."; author = @{ name = "RenderDoc/RDC GPU Debug" }; keywords = @("renderdoc", "rdc", "gpu", "debug", "mcp", "capture"); agents = "./agents/"; skills = "./skills/"; hooks = "./hooks/hooks.json"; mcpServers = "./.mcp.json" }
}

function CodeBuddyHooks() {
 $base = '${CODEBUDDY_PLUGIN_ROOT}/common/hooks/utils/codebuddy_hook_dispatch.py'
 return @{
 PostToolUse = @(
 @{ matcher = "Write"; hooks = @(@{ type = "command"; command = "uv run --with pyyaml python `"$base`" write-bugcard"; description = "BugCard contract and schema validation"; timeout = 30000 }) },
 @{ matcher = "Write"; hooks = @(@{ type = "command"; command = "uv run --with pyyaml python `"$base`" write-skeptic"; description = "Skeptic signoff artifact validation"; timeout = 30000 }) }
)
 Stop = @(@{ hooks = @(@{ type = "command"; command = "uv run --with pyyaml python `"$base`" stop-gate"; description = "Finalization gate: causal anchor + counterfactual + skeptic + session artifacts"; timeout = 30000 }) })
 }
}

function CopilotCliHooks() {
 $base = "common/hooks/utils/codebuddy_hook_dispatch.py"
 return @{
 PostToolUse = @(
 @{ matcher = "Write"; hooks = @(@{ type = "command"; command = "uv run --with pyyaml python $base write-bugcard"; description = "Validate BugCard before write" }) },
 @{ matcher = "Write"; hooks = @(@{ type = "command"; command = "uv run --with pyyaml python $base write-skeptic"; description = "Validate skeptic signoff artifact" }) }
)
 Stop = @(@{ hooks = @(@{ type = "command"; command = "uv run --with pyyaml python $base stop-gate"; description = "Finalization gate" }) })
 }
}

function ClaudeCodeSettings() {
 $base = "common/hooks/utils/codebuddy_hook_dispatch.py"
 $servers = @{}
 foreach ($prop in $McpServers.servers.PSObject.Properties) { $servers[$prop.Name] = @{ command = $prop.Value.command; args = @($prop.Value.args) } }
 return @{
 description = "RenderDoc/RDC GPU Debug - Claude Code platform-local common adaptation"
 hooks = @{
 PostToolUse = @(
 @{ matcher = @{ tool_name = "Write"; file_pattern = "**/knowledge/library/**/*bugcard*.yaml" }; hooks = @(@{ type = "command"; command = "uv run --with pyyaml python $base write-bugcard"; description = "Validate tool contract and BugCard schema before library write"; on_failure = "block"; failure_message = "BugCard write blocked: tool contract drift or schema validation failed." }) },
 @{ matcher = @{ tool_name = "Write"; file_pattern = "**/knowledge/library/sessions/**/skeptic_signoff.yaml" }; hooks = @(@{ type = "command"; command = "uv run --with pyyaml python $base write-skeptic"; description = "Validate skeptic signoff artifact format"; on_failure = "warn"; failure_message = "Skeptic signoff file did not pass validation." }) }
)
 Stop = @(@{ matcher = @{ assistant_message_pattern = ".*" }; hooks = @(@{ type = "command"; command = "uv run --with pyyaml python $base stop-gate"; description = "Finalization gate for RenderDoc/RDC GPU Debug (causal anchor + counterfactual + skeptic)"; on_failure = "block"; failure_message = "Finalization blocked by session artifact or contract checks." }) })
 }
 mcpServers = $servers
 }
}

function CopilotIdePlugin() {
 $notes = @("Start normal user requests from team_lead / orchestrator.", "Preserve role routing and evidence gates even when the host ignores model preference.", "Read references/entrypoints.md before attempting a CLI-style flow inside the IDE host.")
 $notes += $(Platform-Compliance-Notes "copilot-ide")
 return @{ name = "renderdoc-rdc-gpu-debug-ide"; description = "RenderDoc/RDC GPU Debug 的 Copilot IDE platform-local common 适配包。"; agentsRoot = ".github/agents"; notes = $notes }
}

function ClaudeDesktopConfig() {
 $servers = @{}
 foreach ($prop in $McpServers.servers.PSObject.Properties) { $servers[$prop.Name] = @{ command = $prop.Value.command; args = @($prop.Value.args) } }
 return @{ mcpServers = $servers }
}
function CodexReadme() {
 $base = @"
# Codex Template

当前目录是 Codex 的 workspace-native 模板。Agent 的目标是使用 RenderDoc/RDC platform tools 调试 GPU 渲染问题。

使用方式：

1. 将仓库根目录 `debugger/common/` 整体拷贝到当前平台根目录的 `common/`，覆盖占位内容。
2. 在 `common/config/platform_adapter.json` 中配置 `paths.tools_root`。
3. 确认 `validation.required_paths` 在 `<resolved tools_root>/` 下全部存在。
4. 使用当前平台根目录同级的 `workspace/` 作为运行区。
5. 完成覆盖后，打开当前目录作为 Codex workspace root。
6. 正常用户请求从 `team_lead` 发起；其他 specialist 默认是 internal/debug-only。
7. AGENTS.md、.agents/skills/、.codex/config.toml 与 .codex/agents/*.toml 只允许引用当前平台根目录的 common/。

约束：

- common/ 默认只保留一个占位文件；正式共享正文仍由顶层 debugger/common/ 提供，并由用户显式拷入。
- 未完成 debugger/common/ 覆盖前，当前平台模板不可用。
- 未完成 `platform_adapter.json` 配置或 `tools_root` 校验前，Agent 必须拒绝执行依赖平台真相的工作。
- workspace/ 预生成空骨架；真实运行产物在平台使用阶段按 case/run 写入。
- multi_agent 当前按 experimental / CLI-first 理解，但共享规则与 role config 已完整生成。
"@
 return ($base.TrimEnd() + "`n" + [string]::Join("`n", $(Platform-Compliance-Notes "codex")))
}

function CodexConfig() {
 $rows = New-Object System.Collections.Generic.List[string]
 foreach ($line in @("model = `"gpt-5.4`"", "model_reasoning_effort = `"high`"", "model_verbosity = `"medium`"", "", "[features]", "multi_agent = true", "", "[windows]", "sandbox = `"elevated`"", "")) { $null = $rows.Add($line) }
 foreach ($prop in $McpServers.servers.PSObject.Properties) {
 $null = $rows.Add("[mcp_servers.$($prop.Name)]")
 $null = $rows.Add("command = `"$($prop.Value.command)`"")
 $quotedArgs = @()
 foreach ($arg in $prop.Value.args) { $quotedArgs += "`"$arg`"" }
 $args = [string]::Join(", ", $quotedArgs)
 $null = $rows.Add("args = [$args]")
 $null = $rows.Add("")
 }
 foreach ($role in (Roles)) {
 $key = $role.platform_files.codex
 $null = $rows.Add("[agents.$key]")
 $null = $rows.Add("config_file = `".codex/agents/$key.toml`"")
 $null = $rows.Add("")
 }
 return (($rows -join "`n").TrimEnd())
}

function CodexRoleConfig($Role, [string]$TargetFile) {
 $style = $(Role-Style $Role.agent_id)
 $promptRef = $(Common-Ref "codex" $TargetFile @($Role.source_prompt.Split("/")))
@"
# Shared role prompt: $promptRef
model = "$(Platform-Model "codex" $Role.agent_id)"
model_reasoning_effort = "$($style.reasoning_effort)"
model_verbosity = "$($style.verbosity)"

[windows]
sandbox = "elevated"
"@
}
function Expected-Files($Spec) {
 $package = Package-Root $Spec.Key
 $expected = @{}
 foreach ($entry in ((& ${function:Common-Placeholder-Files} $Spec.Key).GetEnumerator())) { $expected[$entry.Key] = $entry.Value }
 foreach ($entry in ((& ${function:Workspace-Placeholder-Files} $Spec.Key).GetEnumerator())) { $expected[$entry.Key] = $entry.Value }
 if ($Spec.Key -eq "codex") {
  $readme = $(CodexReadme)
 } else {
  $readme = $(Readme $Spec.Key)
 }
 Add-Expected $expected (Join-Path $package "README.md") $readme
 $agentsMdPath = Join-Path $package "AGENTS.md"
 $agentsMd = $(PlatformAgentsMd $Spec.Key $agentsMdPath)
 Add-Expected $expected $agentsMdPath $agentsMd
 if (@("claude-code", "code-buddy", "copilot-cli", "copilot-ide") -contains $Spec.Key) {
  foreach ($role in (Roles)) {
   $fileName = $role.platform_files.($Spec.Key)
   if (-not $fileName) { continue }
   if ($Spec.Key -eq "claude-code") {
    $target = Join-Path $package (Join-Path ".claude\agents" $fileName)
    $content = $(ClaudeCodeAgent $role $target)
   } elseif ($Spec.Key -eq "code-buddy") {
    $target = Join-Path $package (Join-Path "agents" $fileName)
    $content = $(CodeBuddyAgent $role $target)
   } elseif ($Spec.Key -eq "copilot-cli") {
    $target = Join-Path $package (Join-Path "agents" $fileName)
    $content = $(CopilotCliAgent $role $target)
   } else {
    $target = Join-Path $package (Join-Path ".github\agents" $fileName)
    $content = $(CopilotIdeAgent $role $target)
   }
   Add-Expected $expected $target $content
  }
 }
 if ($Spec.Key -eq "code-buddy") {
  $skill = Join-Path $package "skills\renderdoc-rdc-gpu-debug\SKILL.md"
  Add-Expected $expected $skill $(BaseSkillWrapper $Spec.Key $skill)
  foreach ($role in (Roles)) {
   $roleSkillTarget = Join-Path $package (Join-Path "skills" (Join-Path (Role-Skill-DirName $role) "SKILL.md"))
   Add-Expected $expected $roleSkillTarget $(RoleSkillWrapper $Spec.Key $role $roleSkillTarget)
  }
  Add-Expected $expected (Join-Path $package ".codebuddy-plugin\plugin.json") (ConvertTo-Json (CodeBuddyPlugin) -Depth 20)
  Add-Expected $expected (Join-Path $package ".mcp.json") (ConvertTo-Json (Mcp-Payload) -Depth 20)
  Add-Expected $expected (Join-Path $package "hooks\hooks.json") (ConvertTo-Json (CodeBuddyHooks) -Depth 20)
 } elseif ($Spec.Key -eq "copilot-cli") {
  $skill = Join-Path $package "skills\renderdoc-rdc-gpu-debug\SKILL.md"
  Add-Expected $expected $skill $(BaseSkillWrapper $Spec.Key $skill)
  foreach ($role in (Roles)) {
   $roleSkillTarget = Join-Path $package (Join-Path "skills" (Join-Path (Role-Skill-DirName $role) "SKILL.md"))
   Add-Expected $expected $roleSkillTarget $(RoleSkillWrapper $Spec.Key $role $roleSkillTarget)
  }
  Add-Expected $expected (Join-Path $package ".copilot-plugin.json") (ConvertTo-Json (CopilotCliPlugin) -Depth 20)
  Add-Expected $expected (Join-Path $package ".mcp.json") (ConvertTo-Json (Mcp-Payload) -Depth 20)
  Add-Expected $expected (Join-Path $package "hooks\hooks.json") (ConvertTo-Json (CopilotCliHooks) -Depth 20)
 } elseif ($Spec.Key -eq "claude-code") {
  $entry = Join-Path $package ".claude\CLAUDE.md"
  Add-Expected $expected $entry $(ClaudeCodeEntry $entry)
  Add-Expected $expected (Join-Path $package ".claude\settings.json") (ConvertTo-Json (ClaudeCodeSettings) -Depth 20)
 } elseif ($Spec.Key -eq "copilot-ide") {
  $skill = Join-Path $package ".github\skills\renderdoc-rdc-gpu-debug\SKILL.md"
  $entry = Join-Path $package ".github\copilot-instructions.md"
  $ref = Join-Path $package "references\entrypoints.md"
  Add-Expected $expected $skill $(BaseSkillWrapper $Spec.Key $skill)
  foreach ($role in (Roles)) {
   $roleSkillTarget = Join-Path $package (Join-Path ".github\skills" (Join-Path (Role-Skill-DirName $role) "SKILL.md"))
   Add-Expected $expected $roleSkillTarget $(RoleSkillWrapper $Spec.Key $role $roleSkillTarget)
  }
  Add-Expected $expected $entry $(CopilotInstructions $entry)
  Add-Expected $expected $ref $(ReferencesEntry $Spec.Key $ref)
  Add-Expected $expected (Join-Path $package "agent-plugin.json") (ConvertTo-Json (CopilotIdePlugin) -Depth 20)
  Add-Expected $expected (Join-Path $package ".github\mcp.json") (ConvertTo-Json (Mcp-Payload) -Depth 20)
 } elseif ($Spec.Key -eq "claude-desktop") {
  $ref = Join-Path $package "references\entrypoints.md"
  Add-Expected $expected $ref $(ReferencesEntry $Spec.Key $ref)
  Add-Expected $expected (Join-Path $package "claude_desktop_config.json") (ConvertTo-Json (ClaudeDesktopConfig) -Depth 20)
 } elseif ($Spec.Key -eq "manus") {
  $ref = Join-Path $package "references\entrypoints.md"
  Add-Expected $expected $ref $(ReferencesEntry $Spec.Key $ref)
  Add-Expected $expected (Join-Path $package "workflows\00_debug_workflow.md") $(ManusWorkflow)
 } elseif ($Spec.Key -eq "codex") {
  $skill = Join-Path $package ".agents\skills\renderdoc-rdc-gpu-debug\SKILL.md"
  Add-Expected $expected $skill $(BaseSkillWrapper $Spec.Key $skill)
  foreach ($role in (Roles)) {
   $roleSkillTarget = Join-Path $package (Join-Path ".agents\skills" (Join-Path (Role-Skill-DirName $role) "SKILL.md"))
   Add-Expected $expected $roleSkillTarget $(RoleSkillWrapper $Spec.Key $role $roleSkillTarget)
  }
  Add-Expected $expected (Join-Path $package ".codex\config.toml") $(CodexConfig)
  foreach ($role in (Roles)) {
   $key = $role.platform_files.codex
   $target = Join-Path $package (Join-Path ".codex\agents" "$key.toml")
   Add-Expected $expected $target $(CodexRoleConfig $role $target)
  }
 }
 return $expected
}
function Compare-Files($Expected) {
 $findings = @()
 foreach ($path in $Expected.Keys) {
 if (-not (Test-Path $path)) { $findings += "missing file: $path"; continue }
 $normPath = $path.Replace("/", "\")
 if ($normPath -like "*\workspace\README.md" -or $normPath -like "*\workspace\cases\README.md") { continue }
 $current = Normalize ([System.IO.File]::ReadAllText($path, [System.Text.Encoding]::UTF8))
 if ($current -ne $Expected[$path]) { $findings += "content drift: $path" }
 }
 return $findings
}

function Compare-ManagedDirs($Spec, $Expected) {
 $findings = @()
 $package = Package-Root $Spec.Key
 foreach ($relDir in $Spec.ManagedDirs) {
 $dir = Join-Path $package $relDir
 $expectedNames = @{}
 foreach ($path in $Expected.Keys) {
 if (-not $path.StartsWith($dir)) { continue }
 $rest = $path.Substring($dir.Length).TrimStart("\")
 if ($rest) { $expectedNames[$rest.Split("\")[0]] = $true }
 }
 if (-not (Test-Path $dir)) { if ($expectedNames.Count -gt 0) { $findings += "missing directory: $dir" }; continue }
 foreach ($child in (Get-ChildItem $dir -Force)) { if (-not $expectedNames.ContainsKey($child.Name)) { $findings += "unexpected scaffold output: $($child.FullName)" } }
 }
 return $findings
}

function Stale-Findings($Spec) {
 $package = Package-Root $Spec.Key
 $findings = @()
 foreach ($rel in $ForbiddenDirs) { $target = Join-Path $package $rel; if (Test-Path $target) { $findings += "forbidden copied shared directory: $target" } }
 foreach ($path in (Get-ChildItem $package -Recurse -Filter "README.copy-common.md" -File -ErrorAction SilentlyContinue)) { $findings += "forbidden copy-common artifact: $($path.FullName)" }
 return $findings
}

function Collect-Findings($Spec) {
 $expected = $(Expected-Files $Spec)
 $rows = @()
 $rows += $(Compare-Files $expected)
 $rows += $(Compare-ManagedDirs $Spec $expected)
 $rows += $(Stale-Findings $Spec)
 return $rows
}

function Remove-PathIfExists([string]$Path) { if (Test-Path $Path) { Remove-Item $Path -Recurse -Force } }

function Sync-Spec($Spec) {
 $package = Package-Root $Spec.Key
 foreach ($rel in $ForbiddenDirs) { Remove-PathIfExists (Join-Path $package $rel) }
 foreach ($rel in $Spec.ManagedDirs) { Remove-PathIfExists (Join-Path $package $rel) }
 foreach ($rel in $Spec.ManagedFiles) { Remove-PathIfExists (Join-Path $package $rel) }
 foreach ($entry in $(Expected-Files $Spec).GetEnumerator()) { Write-Text $entry.Key $entry.Value }
}

function Validate-SourceTree() {
 $required = @($Common, (Join-Path $Common "agents"), (Join-Path $Common "skills\renderdoc-rdc-gpu-debug\SKILL.md"), (Join-Path $Common "docs\workspace-layout.md"), (Join-Path $Common "knowledge\proposals\README.md"), (Join-Path $ConfigRoot "role_manifest.json"), (Join-Path $ConfigRoot "role_policy.json"), (Join-Path $ConfigRoot "model_routing.json"), (Join-Path $ConfigRoot "mcp_servers.json"), (Join-Path $ConfigRoot "platform_adapter.json"), (Join-Path $ConfigRoot "platform_capabilities.json"), (Join-Path $ConfigRoot "platform_targets.json"), (Join-Path $ConfigRoot "framework_compliance.json"), (Join-Path $ConfigRoot "tool_catalog.snapshot.json"))
 $findings = @()
 foreach ($path in $required) { if (-not (Test-Path $path)) { $findings += "missing shared source: $path" } }
 foreach ($role in (Roles)) { $source = Join-Path $Common $role.source_prompt; if (-not (Test-Path $source)) { $findings += "missing shared agent source: $source" } }
 foreach ($role in (Roles)) { $skill = Join-Path $Common $role.role_skill_path; if (-not (Test-Path $skill)) { $findings += "missing shared role skill: $skill" } }
 return $findings
}

$sourceFindings = Validate-SourceTree
if ($sourceFindings.Count -gt 0) {
 Write-Output "[platform scaffold findings]"
 foreach ($row in $sourceFindings) { Write-Output " - $row" }
 exit 1
}

$findings = @()
foreach ($spec in $Specs) { $findings += $(Collect-Findings $spec) }
if ($Check) {
 if ($findings.Count -gt 0) {
 Write-Output "[platform scaffold findings]"
 foreach ($row in $findings) { Write-Output " - $row" }
 exit 1
 }
 Write-Output "platform scaffold check passed"
 exit 0
}

foreach ($spec in $Specs) { Sync-Spec $spec }
Write-Output "platform scaffold sync complete"
