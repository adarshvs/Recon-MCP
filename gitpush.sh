#!/bin/bash

# Check if current directory is a Git repo
if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
  echo "❌ Not inside a Git repository."
  exit 1
fi

# Check if remote "origin" is set
if ! git remote get-url origin > /dev/null 2>&1; then
  echo "❌ No remote named 'origin' found. Set it using:"
  echo "    git remote add origin https://github.com/adarshvs/Recon-MCP.git"
  exit 1
fi

# Ask for a commit message
read -p "Enter commit message: " commit_msg

# Add and commit changes
git add .
if git diff --cached --quiet; then
  echo "✅ Nothing to commit."
else
  git commit -m "$commit_msg"
fi

# Ensure main branch is tracked
git branch --set-upstream-to=origin/main main 2>/dev/null

# Pull and push
git pull origin main --allow-unrelated-histories --no-rebase
git push origin main
