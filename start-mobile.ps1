[CmdletBinding()]
param(
    [int]$Port = 8000,
    [switch]$ConfigureFirewall
)

$ErrorActionPreference = "Stop"
$projectRoot = $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Missing .venv. Follow README to install dependencies first."
}

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
$isAdmin = $principal.IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)

if ($ConfigureFirewall -and -not $isAdmin) {
    $argumentLine = "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`" -Port $Port -ConfigureFirewall"
    Start-Process powershell -Verb RunAs -ArgumentList $argumentLine
    Write-Host "A UAC prompt was opened. Continue in the new window."
    exit 0
}

$listener = Get-NetTCPConnection `
    -LocalPort $Port `
    -State Listen `
    -ErrorAction SilentlyContinue
if ($listener) {
    $pids = @(
        $listener | Select-Object -ExpandProperty OwningProcess -Unique
    )
    foreach ($processId in $pids) {
        $process = Get-CimInstance Win32_Process `
            -Filter "ProcessId = $processId"
        $commandLine = [string]$process.CommandLine
        $isNavPark = $commandLine.Contains("uvicorn main:app") -and `
            $commandLine.Contains("$projectRoot\.venv\Scripts\python.exe")
        if (-not $isNavPark) {
            throw "Port $Port is owned by an unrelated process: $processId."
        }
    }
    foreach ($processId in $pids) {
        Stop-Process -Id $processId -Force
    }
    Start-Sleep -Milliseconds 700
    Write-Host "Restarted the existing NavPark server."
}

if ($ConfigureFirewall) {
    $ruleName = "NavPark Mobile TCP $Port"
    $existingRule = Get-NetFirewallRule `
        -DisplayName $ruleName `
        -ErrorAction SilentlyContinue
    if (-not $existingRule) {
        try {
            New-NetFirewallRule `
                -DisplayName $ruleName `
                -Direction Inbound `
                -Action Allow `
                -Protocol TCP `
                -LocalPort $Port `
                -Profile Private `
                -Description "Allow NavPark LAN access on private networks." | Out-Null
            Write-Host "Firewall rule created for private-network TCP $Port."
        }
        catch {
            Write-Warning "Firewall setup failed. Run as administrator or allow TCP $Port manually."
        }
    }
}

$codexInboundRule = netsh advfirewall firewall show rule `
    name="codex_sandbox_offline_block_inbound" 2>$null
if ($codexInboundRule) {
    Write-Warning "Codex inbound blocking is active. If the phone cannot connect, exit Codex and start this script from a normal PowerShell window."
}

$lanIp = & $python -c "from app.mobile import get_lan_ip; print(get_lan_ip())"
$accessUrl = "http://$lanIp`:$Port"

Write-Host ""
Write-Host "NavPark mobile access"
Write-Host "Desktop: http://127.0.0.1:$Port/"
Write-Host "QR page: http://127.0.0.1:$Port/mobile"
Write-Host "Phone:   $accessUrl/"
Write-Host ""
Write-Host "Phone and computer must use the same Wi-Fi."
Write-Host "Text chat works over HTTP. Voice and location require HTTPS."
Write-Host "Press Ctrl+C to stop."
Write-Host ""

Set-Location -LiteralPath $projectRoot
& $python -m uvicorn main:app --host 0.0.0.0 --port $Port
