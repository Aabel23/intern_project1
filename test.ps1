# Chạy các luồng kiểm tra FlexMix và cập nhật log/FLOWS.md.
#   .\test.ps1 -List                  danh sách luồng + trạng thái lần chạy cuối
#   .\test.ps1                        chạy mọi luồng (py, app, e2e)
#   .\test.ps1 -Flow S8,F2            chỉ vài luồng
#   .\test.ps1 -Flow py               theo nhóm: py, app, e2e, all
#   .\test.ps1 -Flow E4 -Note "..."   e2e nối tiếp: E4 chạy E0..E4
#   .\test.ps1 -Build                 luôn build lại APK trước e2e
# Tiêu chí từng luồng: log/TIEU_CHI_TEST.md. Thêm luồng mới: FLOWS trong sandbox/check_all.py.
param(
    [string]$Flow = "all",
    [switch]$List,
    [switch]$Build,
    [string]$Note = ""
)

$root = $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$arguments = @((Join-Path $root "sandbox\check_all.py"), "--flows", $Flow)
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
