# 安装本仓库中的 Claude Code 技能到个人技能目录。
# 用法：
#   powershell -ExecutionPolicy Bypass -File .\install.ps1
#   powershell -ExecutionPolicy Bypass -File .\install.ps1 safillu
#   powershell -ExecutionPolicy Bypass -File .\install.ps1 -Target D:\my-project\.claude\skills

param(
    [string[]]$Skills,
    [string]$Target = (Join-Path $env:USERPROFILE ".claude\skills")
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
$source = Join-Path $repo "skills"

$available = @(Get-ChildItem -Path $source -Directory | Select-Object -ExpandProperty Name)
if (-not $Skills -or $Skills.Count -eq 0) { $Skills = $available }

New-Item -ItemType Directory -Force -Path $Target | Out-Null

foreach ($name in $Skills) {
    if ($available -notcontains $name) {
        Write-Error "未知技能: $name（可选: $($available -join ', ')）"
    }
    $from = Join-Path $source $name
    $to = Join-Path $Target $name

    # 覆盖安装前保留用户自己放的本地 key 文件
    $savedKeys = @{}
    if (Test-Path $to) {
        Get-ChildItem -Path $to -Filter *.key -File | ForEach-Object {
            $savedKeys[$_.Name] = Get-Content -Raw $_.FullName
        }
    }

    if (Test-Path $to) { Remove-Item -Recurse -Force $to }
    Copy-Item -Recurse -Force $from $to

    foreach ($keyName in $savedKeys.Keys) {
        Set-Content -Path (Join-Path $to $keyName) -Value $savedKeys[$keyName] -NoNewline
    }

    Write-Host "已安装 $name -> $to"
}

Write-Host ""
Write-Host "重启 Claude Code 后生效。safillu 技能需要配置 key："
Write-Host "  python `"$Target\safillu\scripts\safillu.py`" login --key sk-xxxxxxxx"
