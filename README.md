# QA Engineer Skills

一个面向测试与质量工程师的公共 Agent Skills 仓库。当前提供 `test-case-design` skill：将 PRD、用户故事或业务规则拆解为原子测试点，并设计可追踪、风险驱动的测试用例；需要时可将符合约束的大纲构建为 MeterSphere 可导入的 XMind 文件。

Skill 内容遵循通用 `SKILL.md` 约定，可供 Codex、Claude Code、Cursor 和支持相同目录约定的工具复用。Codex 额外提供 marketplace 适配层；完整的跨 Agent 安装说明见 [docs/agent-installation.md](docs/agent-installation.md)。

## 能力

- 基于真实菜单路径组织测试资产，避免把 PRD 名称或版本号当成菜单目录。
- 建立“规则 -> 测试点 -> 模型项 -> 用例”的可追踪链路，支持增量复用已有资产。
- 覆盖等价类、边界值、判定表、状态迁移、组合、故障时序和探索式测试等适用方法。
- 输出 MeterSphere 大纲、测试点台账与评审记录，并明确待确认项和剩余风险。
- 使用内置 Python 脚本严格校验大纲结构，构建 XMind（Zen）文件。

## 安装

### Codex

前提：已安装支持插件的 Codex CLI，并可访问 GitHub。首次安装运行：

```powershell
codex plugin marketplace add forjone/qa-engineer-skills --ref main
codex plugin add test-case-design@qa-engineer-skills
```

确认安装结果：

```powershell
codex plugin list
```

插件安装后，请新建一个 Codex 任务再开始使用，以便它加载新 skill。

在本地开发或尚未发布到 GitHub 时，可用本地路径验证：

```powershell
codex plugin marketplace add <local-repository-path>
codex plugin add test-case-design@qa-engineer-skills
```

### Claude Code、Cursor 和其他 Agent

克隆仓库后，用内置安装脚本安装到项目级或用户级目录：

```powershell
git clone https://github.com/forjone/qa-engineer-skills.git
cd qa-engineer-skills
.\scripts\install-skill.ps1 -Agent ClaudeCode -Scope Project
.\scripts\install-skill.ps1 -Agent Cursor -Scope User
```

Qoder 或其他 Agent 请显式指定其版本文档要求的 skills 目录：

```powershell
.\scripts\install-skill.ps1 -Agent Qoder -Target 'C:\path\to\agent\skills'
```

## 使用方法

在 Codex 中提供需求资料并直接说明交付目标。例如：

```text
根据 docs/PRD.md 的“规则配置”章节，为 Web 端设计正式测试用例。
真实菜单路径是“管理中心 > 规则配置”；输出 outline.txt、test-points.md 和 review.md，
需要 MeterSphere XMind 文件。优先关注数据隔离、权限和日期边界。
```

若资料不完整，也可以要求草案：

```text
基于以下用户故事先输出测试点与草案用例。未定义的错误码、时限和幂等规则请单列待确认，
不要把假设混入正式用例。
```

skill 会先确认需求依据和范围；正式交付通常还需要真实菜单路径、验收规则、权限/状态/接口资料和历史测试资产。它不会声称已执行测试或已完成 MeterSphere 实际导入，除非你提供了对应的执行环境和授权。

## XMind 构建器

Python 3 标准库即可运行，不依赖第三方包。将结构合格的大纲转换为 XMind：

```powershell
py -3 -X utf8 plugins/test-case-design/skills/test-case-design/scripts/build_xmind.py --strict outline.txt output.xmind
```

运行脚本测试：

```powershell
py -3 -m unittest discover -s plugins/test-case-design/skills/test-case-design/scripts -p "test_*.py"
```

`--strict` 会检查用例优先级、`pc`/`rc`/`tag` 元数据、连续步骤、预期结果和目录层级。构建成功仅代表本地 ZIP 和主题树校验通过，不代表业务覆盖充分、测试已执行或已验证 MeterSphere 导入兼容性。

## 项目结构

```text
.
|-- .agents/plugins/marketplace.json  # Codex marketplace 清单
|-- docs/agent-installation.md         # 跨 Agent 安装说明
|-- plugins/
|   `-- test-case-design/
|       |-- .codex-plugin/plugin.json  # 插件元数据
|       `-- skills/test-case-design/
|           |-- SKILL.md               # 设计工作流和交付门禁
|           |-- reference/             # 方法、菜单资产和测试点参考
|           `-- scripts/               # XMind 构建器及单元测试
`-- scripts/install-skill.ps1          # 通用本地安装脚本
```

## 发布与更新

首次发布：

```powershell
git add .
git commit -m "feat: publish test case design skill"
git branch -M main
git push -u origin main
```

安装过插件的用户更新 marketplace 快照后重新安装：

```powershell
codex plugin marketplace upgrade qa-engineer-skills
codex plugin add test-case-design@qa-engineer-skills
```

新增 skill 时，在 `plugins/<skill-name>/` 创建包含 `SKILL.md` 的目录，在 `.codex-plugin/plugin.json` 的 `skills` 路径下保持可发现，并将插件条目追加到 `.agents/plugins/marketplace.json`。每次修改后都应运行相应测试并提高插件版本。

## 许可

[MIT](LICENSE)
