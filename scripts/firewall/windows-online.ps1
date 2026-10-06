# Undo windows-offline.ps1: remove the Sahayak block rules (Administrator PowerShell).
$ErrorActionPreference = "Stop"
Get-NetFirewallRule -DisplayName "Sahayak: block internet*" -ErrorAction SilentlyContinue | Remove-NetFirewallRule
Write-Host "Offline mode OFF: the Sahayak block rules are removed."
