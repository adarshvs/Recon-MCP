#!/bin/bash

# Go to the current directory
cd "$(pwd)"

# Ask for a commit message
read -p "Enter commit message: " commit_msg

# Git add, commit, and push
git add .
git commit -m "$commit_msg"
#git branch --set-upstream-to=origin/main main 2>/dev/null
# git pull origin main --allow-unrelated-histories --no-rebase
git push origin main

