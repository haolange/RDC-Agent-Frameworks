# Team Lead Skill Wrapper

当前文件是 Codex 的 role skill 入口。

该角色是当前 framework 的唯一正式用户入口。正常用户请求必须从 `team_lead` 发起。

先阅读：

1. ../../../common/skills/renderdoc-rdc-gpu-debug/SKILL.md
2. ../../../common/skills/team-lead-orchestration/SKILL.md
3. ../../../common/config/platform_capabilities.json

未先将顶层 debugger/common/ 拷入当前平台根目录的 common/ 之前，不允许在宿主中使用当前平台模板。

在 
un_compliance.yaml(status=passed) 生成前，你只能输出阶段性 brief，不得宣称最终裁决。
运行时 case/run 现场与第二层报告统一写入：`../workspace`
