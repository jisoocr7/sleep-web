param(
    [int]$Port = 7861
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$serverScript = Join-Path $projectRoot "server.py"
$qaScript = Join-Path $projectRoot "tests\browser_qa.py"

function Stop-ProcessTree {
    param([int]$TargetId)

    $children = Get-CimInstance Win32_Process -Filter "ParentProcessId = $TargetId" -ErrorAction SilentlyContinue
    foreach ($child in $children) {
        Stop-ProcessTree -TargetId $child.ProcessId
    }
    Stop-Process -Id $TargetId -Force -ErrorAction SilentlyContinue
}

$previousPort = $env:PORT
$previousBaseUrl = $env:SAFE_WEB_BASE_URL
$env:PORT = [string]$Port
$env:SAFE_WEB_BASE_URL = "http://127.0.0.1:$Port"
$server = $null

try {
    $server = Start-Process -FilePath $python -ArgumentList $serverScript -WorkingDirectory $projectRoot -PassThru -WindowStyle Hidden
    $deadline = (Get-Date).AddSeconds(60)
    do {
        Start-Sleep -Milliseconds 250
        if ($server.HasExited) {
            throw "Local Flask server exited before becoming ready."
        }
        $listener = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
    } while (-not $listener -and (Get-Date) -lt $deadline)

    if (-not $listener) {
        throw "Local Flask server did not open port $Port within 60 seconds."
    }

    & $python $qaScript
    if ($LASTEXITCODE -ne 0) {
        throw "Browser QA failed with exit code $LASTEXITCODE."
    }
}
finally {
    if ($server -and -not $server.HasExited) {
        Stop-ProcessTree -TargetId $server.Id
    }
    $env:PORT = $previousPort
    $env:SAFE_WEB_BASE_URL = $previousBaseUrl
}
