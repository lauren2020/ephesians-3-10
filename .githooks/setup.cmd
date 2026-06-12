@echo off
REM Activate the repo's tracked git hooks. Run once per clone (Windows).
git config core.hooksPath .githooks
echo Hooks activated: core.hooksPath -^> .githooks
