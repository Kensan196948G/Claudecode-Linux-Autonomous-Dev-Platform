#!/usr/bin/env bash
set -euo pipefail

git config --global user.name "${GIT_AUTHOR_NAME:-ClaudeOS}"
git config --global user.email "${GIT_AUTHOR_EMAIL:-claude@local.ai}"
git config --global pull.rebase false
git config --global init.defaultBranch main
