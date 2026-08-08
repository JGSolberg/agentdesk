@echo off
setlocal
cd /d "%~dp0"
start "AgentDesk API" powershell.exe -NoExit -NoLogo -NoProfile -Command "Set-Location -LiteralPath '%CD%'; just api"
start "AgentDesk Web" powershell.exe -NoExit -NoLogo -NoProfile -Command "Set-Location -LiteralPath '%CD%'; just web"
