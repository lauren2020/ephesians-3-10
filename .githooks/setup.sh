#!/bin/sh
# Activate the repo's tracked git hooks. Run once per clone (mac/linux/Git Bash).
git config core.hooksPath .githooks
chmod +x .githooks/pre-commit 2>/dev/null
echo "Hooks activated: core.hooksPath -> .githooks"
