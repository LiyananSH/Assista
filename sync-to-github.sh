#!/bin/bash
# Assista V3.3 自动上传脚本
# 每天检查变化，有更新则推送到 GitHub

REPO_DIR="/Users/shige/Desktop/Assista_V3/V3.3_开发版"
GITHUB_REPO="git@github.com:LiyananSH/Assista.git"
BRANCH="main"

cd "$REPO_DIR" || exit 1

# 检查是否有变化
if [ -z "$(git status --porcelain)" ]; then
    echo "$(date): 无变化，跳过上传"
    exit 0
fi

# 添加所有变化
git add -A

# 提交
git commit -m "Auto sync: $(date '+%Y-%m-%d %H:%M:%S')"

# 推送到 GitHub
git push origin "$BRANCH"

echo "$(date): 已同步到 GitHub"
