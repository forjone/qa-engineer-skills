# Cross-Agent Installation

`plugins/test-case-design/skills/test-case-design/` is a self-contained Agent Skill: it includes `SKILL.md`, `reference/`, and `scripts/`. Keep those files together when installing it into another tool.

## Codex

Codex consumes the repository's marketplace configuration. This is the only installation method that uses `.agents/plugins/marketplace.json` and `.codex-plugin/plugin.json`.

```powershell
codex plugin marketplace add forjone/qa-engineer-skills --ref main
codex plugin add test-case-design@qa-engineer-skills
```

## Claude Code

For a repository-local skill, install it under `.claude/skills/`. For a user-level skill, install it under `~/.claude/skills/`.

```powershell
.\scripts\install-skill.ps1 -Agent ClaudeCode -Scope Project
.\scripts\install-skill.ps1 -Agent ClaudeCode -Scope User
```

## Cursor

For tools configured to discover Agent Skills from `.cursor/skills/`, use the same script:

```powershell
.\scripts\install-skill.ps1 -Agent Cursor -Scope Project
.\scripts\install-skill.ps1 -Agent Cursor -Scope User
```

Confirm that the installed Cursor version has Agent Skills enabled. If the version only supports Rules, use its Rules workflow instead; do not rename `SKILL.md` to imply that it is a Rule.

## Qoder and Other Agents

The repository intentionally does not guess a Qoder skill path, because product releases can differ. Find the configured skill directory in the target Agent's documentation, then pass it explicitly:

```powershell
.\scripts\install-skill.ps1 -Agent Qoder -Target 'C:\path\to\agent\skills'
```

The resulting directory must be `<target>/test-case-design/` and retain `SKILL.md`, `reference/`, and `scripts/`.

## Updating

The script refuses to overwrite an existing skill. Remove or archive the existing `test-case-design` destination only after reviewing local changes, then run the installation command again. For Codex, refresh the marketplace and reinstall the plugin.
