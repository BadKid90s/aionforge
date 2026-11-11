本扩展的入口 Skill 目录（下文 `<skill目录>`）是 `~/.gemini/extensions/aionforge/skills/aionforge`。`forge` CLI 始终用这个目录下的 `scripts/`。工作流 Skill 与入口同级。
每次提交代码（`git commit`）前必须运行 `uv run --project skills/aionforge/scripts ruff check skills/aionforge/scripts` 检查 Python/Ruff 代码规范。

@./skills/aionforge/SKILL.md
@./skills/aionforge-print/SKILL.md
@./skills/aionforge-product/SKILL.md
@./skills/aionforge-main/SKILL.md
@./skills/aionforge-detail/SKILL.md
