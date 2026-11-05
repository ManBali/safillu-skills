#!/usr/bin/env bash
# 安装本仓库中的 Claude Code 技能到个人技能目录。
# 用法：
#   ./install.sh              # 安装全部技能
#   ./install.sh safillu      # 只装指定技能
#   CLAUDE_SKILLS_DIR=... ./install.sh

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE="$REPO_DIR/skills"
TARGET="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"

available=$(find "$SOURCE" -mindepth 1 -maxdepth 1 -type d -exec basename {} \; | sort)
if [ "$#" -eq 0 ]; then
  # shellcheck disable=SC2086
  set -- $available
fi

mkdir -p "$TARGET"
for name in "$@"; do
  if [ ! -d "$SOURCE/$name" ]; then
    echo "未知技能: $name（可选: $(echo $available | tr '\n' ' ')）" >&2
    exit 1
  fi

  dest="$TARGET/$name"
  # 覆盖安装前保留用户自己放的本地 key 文件
  keyBackup="$(mktemp -d)"
  if compgen -G "$dest/*.key" > /dev/null; then
    cp "$dest"/*.key "$keyBackup"/
  fi

  rm -rf "$dest"
  cp -R "$SOURCE/$name" "$dest"

  if compgen -G "$keyBackup/*.key" > /dev/null; then
    cp "$keyBackup"/*.key "$dest"/
    chmod 600 "$dest"/*.key
  fi
  rm -rf "$keyBackup"

  echo "已安装 $name -> $dest"
done

echo
echo "重启 Claude Code 后生效。safillu 技能需要配置 key："
echo "  python \"$TARGET/safillu/scripts/safillu.py\" login --key sk-xxxxxxxx"
