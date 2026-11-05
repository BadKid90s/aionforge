#!/usr/bin/env bash
#
# 统一修改所有清单里的版本号。
#
#   scripts/bump-version.sh           列出各文件当前版本，不一致时退出码 1
#   scripts/bump-version.sh 0.2.0     全部改成 0.2.0，并刷新 uv.lock
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPTS="skills/aionforge/scripts"

# 第一行带 version 的 JSON 清单
JSON_FILES=(
  .claude-plugin/plugin.json
  .codex-plugin/plugin.json
  .cursor-plugin/plugin.json
  plugin.json
  gemini-extension.json
)
PYPROJECT="$SCRIPTS/pyproject.toml"
INIT_PY="$SCRIPTS/aionforge/__init__.py"

read_versions() {
  for f in "${JSON_FILES[@]}"; do
    printf '%s\t%s\n' "$(sed -nE 's/^  "version": "([^"]+)".*/\1/p' "$ROOT/$f" | head -1)" "$f"
  done
  printf '%s\t%s\n' "$(sed -nE 's/^version = "([^"]+)"/\1/p' "$ROOT/$PYPROJECT")" "$PYPROJECT"
  printf '%s\t%s\n' "$(sed -nE 's/^__version__ = "([^"]+)"/\1/p' "$ROOT/$INIT_PY")" "$INIT_PY"
}

if [[ $# -eq 0 ]]; then
  read_versions
  count=$(read_versions | cut -f1 | sort -u | wc -l | tr -d ' ')
  if [[ "$count" != 1 ]]; then
    echo "版本号不一致" >&2
    exit 1
  fi
  exit 0
fi

NEW="$1"
if [[ ! "$NEW" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "版本号格式应为 X.Y.Z：$NEW" >&2
  exit 1
fi

for f in "${JSON_FILES[@]}"; do
  sed -i.bak -E "s/^(  \"version\": \")[^\"]+(\")/\1$NEW\2/" "$ROOT/$f"
done
sed -i.bak -E "s/^version = \"[^\"]+\"/version = \"$NEW\"/" "$ROOT/$PYPROJECT"
sed -i.bak -E "s/^__version__ = \"[^\"]+\"/__version__ = \"$NEW\"/" "$ROOT/$INIT_PY"
find "$ROOT" -name '*.bak' -not -path '*/.git/*' -delete

(cd "$ROOT/$SCRIPTS" && uv lock -q)
read_versions
