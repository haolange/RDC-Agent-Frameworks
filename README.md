# RDC-Agent Frameworks（多框架仓库）

本仓库是多 framework 仓库，用来承载构建在底层平台能力之上的上层 Agent framework。

它不是一个直接暴露 platform tools、runtime state 或 tool contract 的独立运行仓库。平台真相、tool catalog、daemon-owned session/runtime 语义由对应的底层工具仓库负责；本仓库只负责上层 framework 的任务编排、角色组织、输出契约与文档治理。

## 仓库分层

- framework 层负责把用户目标翻译成可执行的 workflow、角色协作、质量门槛与交付物约束。
- tools 层负责提供平台能力、运行时对象语义、共享错误面与 tool contract。
- 宿主平台适配层负责把 framework 落到具体宿主入口、插件形态或工作台结构上。

这三层是明确的上下层关系，不是替代关系。上层 framework 不重写平台真相，底层 tools 也不承载具体业务 workflow。

## 当前目录

- `debugger/`：当前唯一进入首发 GA 规划的 framework。
- `analyzer/`：`incubating`，当前仍是方法论骨架，不纳入首发 GA 承诺。
- `optimizer/`：`incubating`，当前仍是方法论骨架，不纳入首发 GA 承诺。

## 阅读方式

从仓库根进入时，只需要先理解目录地图与分层关系。

实际使用某个 framework 时，进入对应子目录阅读该 framework 自己的 `README.md`、核心约束与维护文档。仓库根文档不定义任何子框架专属的运行前提、输入要求或平台适配步骤。
