param(
    [int]$Port = 7860,
    [switch]$AllowLan,
    [string]$PublicBaseUrl = ""
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Local environment not found. Run: python -m venv .venv; .\.venv\Scripts\python.exe -m pip install -r requirements.txt"
}

$env:PORT = [string]$Port
$env:HOST = if ($AllowLan) { "0.0.0.0" } else { "127.0.0.1" }

if ($PublicBaseUrl) {
    $env:PUBLIC_BASE_URL = $PublicBaseUrl.TrimEnd("/")
} elseif ($AllowLan) {
    $lanAddress = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" } |
        Sort-Object InterfaceMetric |
        Select-Object -First 1 -ExpandProperty IPAddress
    if ($lanAddress) {
        $env:PUBLIC_BASE_URL = "http://${lanAddress}:$Port"
        Write-Host "Phone URL: $env:PUBLIC_BASE_URL/mobile"
    } else {
        Write-Warning "No LAN IPv4 address was detected. Set -PublicBaseUrl manually for a phone-readable QR code."
    }
}

Write-Host "Desktop URL: http://127.0.0.1:$Port/"
& $python (Join-Path $projectRoot "server.py")
