param(
    [ValidateSet('start', 'stop', 'client')]
    [string]$Action = 'start'
)

$ErrorActionPreference = 'Stop'
$mysqlBin = 'E:\Development\mysql-8.4.11-winx64\bin'
$mysqlConfig = 'E:\Development\mysql-flexmix\my.ini'
$mysqlCredentials = Join-Path $PSScriptRoot '..\secrets\mysql-admin.ini'

if ($Action -eq 'client') {
    & "$mysqlBin\mysql.exe" "--defaults-extra-file=$mysqlCredentials"
    exit $LASTEXITCODE
}
if ($Action -eq 'stop') {
    & "$mysqlBin\mysqladmin.exe" "--defaults-extra-file=$mysqlCredentials" shutdown
    exit $LASTEXITCODE
}

$mysqlProcess = Get-CimInstance Win32_Process -Filter "Name = 'mysqld.exe'" |
    Where-Object { $_.ExecutablePath -eq "$mysqlBin\mysqld.exe" }
if (-not $mysqlProcess) {
    Start-Process -FilePath "$mysqlBin\mysqld.exe" -ArgumentList "--defaults-file=$mysqlConfig" -WindowStyle Hidden
}
for ($attempt = 0; $attempt -lt 20; $attempt++) {
    if (Get-NetTCPConnection -State Listen -LocalPort 3306 -ErrorAction SilentlyContinue) {
        & "$mysqlBin\mysql.exe" "--defaults-extra-file=$mysqlCredentials" --execute='SELECT 1' | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'MySQL connection check failed.' }
        Write-Host 'MySQL is running at 127.0.0.1:3306.'
        exit 0
    }
    Start-Sleep -Seconds 1
}
throw 'MySQL failed to start. Check E:\Development\mysql-flexmix\mysql-error.log.'
