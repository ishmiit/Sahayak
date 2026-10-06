# Sahayak demo node: block every connection to the internet, allow the local network.
# Run in an Administrator PowerShell on the node:  .\scripts\firewall\windows-offline.ps1
# Undo:                                             .\scripts\firewall\windows-online.ps1
#
# Windows ships many outbound ALLOW rules (DNS, Windows Update, store apps). A default-block
# policy does not override them, but a BLOCK rule does, so this adds one block rule covering every
# address outside the local network. Phones on the Sahayak Wi-Fi still reach the node; nothing on
# the node can reach the internet, even if someone plugs in a cable or a hotspot by mistake.

$ErrorActionPreference = "Stop"

# Every IPv4 address except loopback (127/8), private (10/8, 172.16/12, 192.168/16),
# link-local (169.254/16) and multicast/broadcast (224/4 and above), plus all global IPv6.
$internet = @(
  "0.0.0.0-9.255.255.255", "11.0.0.0-126.255.255.255", "128.0.0.0-169.253.255.255",
  "169.255.0.0-172.15.255.255", "172.32.0.0-192.167.255.255", "192.169.0.0-223.255.255.255",
  "2000::/3"
)

Get-NetFirewallRule -DisplayName "Sahayak: block internet*" -ErrorAction SilentlyContinue | Remove-NetFirewallRule
New-NetFirewallRule -DisplayName "Sahayak: block internet (outbound)" -Direction Outbound -Action Block `
  -RemoteAddress $internet -Profile Any -Description "Sahayak zero-egress: nothing leaves the local network" | Out-Null
New-NetFirewallRule -DisplayName "Sahayak: block internet (inbound)" -Direction Inbound -Action Block `
  -RemoteAddress $internet -Profile Any -Description "Sahayak zero-egress: nothing comes in from the internet" | Out-Null

# Log dropped packets so the egress panel and the README can show the blocks happening.
Set-NetFirewallProfile -Profile Domain,Private,Public -Enabled True -LogBlocked True `
  -LogFileName "%SystemRoot%\System32\LogFiles\Firewall\pfirewall.log" -LogMaxSizeKilobytes 4096

Write-Host "Offline mode ON: the node can reach only the local network. The Sahayak status page shows it."
