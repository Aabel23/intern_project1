param(
    [string]$ClaudePath,
    [string]$Deadline = "2026-09-29T05:00:00+07:00"
)

$root = Split-Path $PSScriptRoot -Parent
$runs = Join-Path $PSScriptRoot "runs"
New-Item -ItemType Directory -Force -Path $runs | Out-Null
$env:PATH = "E:\Development\flutter-sdk\bin;D:\Users\NGOCTRAN\AppData\Local\Android\Sdk\platform-tools;" + $env:PATH
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
$end = [DateTimeOffset]::Parse($Deadline)
Set-Content -LiteralPath (Join-Path $runs "claude.takeover") -Value "Requested at $(Get-Date -Format o)" -Encoding UTF8

# Let the current test batch finish and release the phone before Claude starts.
while (Test-Path (Join-Path $runs "night_loop.lock")) {
    if ([DateTimeOffset]::Now -ge $end) { exit 0 }
    $runnerPid = Get-Content -LiteralPath (Join-Path $runs "night_loop.lock") -ErrorAction SilentlyContinue
    if ($runnerPid -match '^\d+$' -and -not (Get-Process -Id ([int]$runnerPid) -ErrorAction SilentlyContinue)) {
        Remove-Item -LiteralPath (Join-Path $runs "night_loop.lock")
        break
    }
    Start-Sleep -Seconds 10
}
if ([DateTimeOffset]::Now -ge $end) { exit 0 }
$prompt = Get-Content -LiteralPath (Join-Path $PSScriptRoot "CLAUDE_HANDOFF.md") -Raw -Encoding UTF8
Push-Location $root
try {
    & $ClaudePath -p $prompt --allowedTools "Read,Glob,Grep,Edit,Write,Bash" --output-format text *> (Join-Path $runs "claude-handoff.log")
    $result = $LASTEXITCODE
    Set-Content -LiteralPath (Join-Path $runs "claude-exit.txt") -Value "$result $(Get-Date -Format o)" -Encoding UTF8
    if ([DateTimeOffset]::Now -lt $end) {
        # If Claude exits early (including a token limit), keep existing tests running.
        Remove-Item -LiteralPath (Join-Path $runs "claude.takeover") -ErrorAction SilentlyContinue
        $python = Join-Path $root ".venv/Scripts/python.exe"
        & $python (Join-Path $PSScriptRoot "night_loop.py") --until $Deadline *> (Join-Path $runs "fallback-loop.log")
    }
    exit $result
} finally {
    Pop-Location
}
