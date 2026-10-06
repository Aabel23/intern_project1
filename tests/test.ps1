# Chạy các luồng kiểm tra FlexMix và cập nhật log/FLOWS.md.
#   .\tests\test.ps1 -List                  danh sách luồng + trạng thái lần chạy cuối
#   .\tests\test.ps1                        chạy mọi luồng (py, app, e2e)
#   .\tests\test.ps1 -Flow S8,F2            chỉ vài luồng
#   .\tests\test.ps1 -Flow py               theo nhóm: py, app, e2e, all
#   .\tests\test.ps1 -Flow E4 -Note "..."   e2e nối tiếp: E4 chạy E0..E4
#   .\tests\test.ps1 -Build                 luôn build lại APK trước e2e
# Tiêu chí từng luồng: log/TIEU_CHI_TEST.md. Thêm luồng mới: FLOWS trong tests/run_tests.py.
param(
    [string]$Flow = "all",
    [switch]$List,
    [switch]$Build,
    [string]$Note = ""
)

$root = Split-Path $PSScriptRoot -Parent
$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$arguments = @((Join-Path $root "tests\run_tests.py"), "--flows", $Flow)
if ($List) { $arguments += "--list" }
if ($Build) { $arguments += "--build" }
if ($Note) { $arguments += @("--note", $Note) }

Push-Location $root
try {
    & $python @arguments
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
