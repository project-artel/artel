param([ValidateSet('build', 'path')][string]$Action = 'build')
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$runtime = Get-ChildItem -LiteralPath (Join-Path $repoRoot '.work') -Directory -Filter 'latest-pr-local-*' |
    Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'runtime.json') } |
    Sort-Object Name -Descending | Select-Object -First 1
if (-not $runtime) { throw 'Prepared local runtime was not found under .work/latest-pr-local-*.' }
$desktopInfoPath = Join-Path $runtime.FullName 'desktop-build.json'
if ($Action -eq 'path') {
    if (-not (Test-Path -LiteralPath $desktopInfoPath)) { throw 'No copied desktop build has been recorded.' }
    $desktopInfo = Get-Content -LiteralPath $desktopInfoPath -Raw | ConvertFrom-Json
    Write-Output $desktopInfo.folder
    exit 0
}
$sourcePath = Join-Path $runtime.FullName 'game-source.json'
if (-not (Test-Path -LiteralPath $sourcePath)) { throw 'game-source.json is missing. Prepare a verified game revision first.' }
$source = Get-Content -LiteralPath $sourcePath -Raw | ConvertFrom-Json
$project = Join-Path $runtime.FullName ('game-v' + $source.version)
$settingsPath = Join-Path $project 'ProjectSettings/ProjectSettings.asset'
if (-not (Test-Path -LiteralPath $settingsPath)) { throw "Game project is missing: $project" }
$settings = Get-Content -LiteralPath $settingsPath -Raw
$bundleVersion = [regex]::Match($settings, '(?m)^  bundleVersion: (.+)$').Groups[1].Value.Trim()
if ($bundleVersion -ne $source.version) { throw 'Game source version differs from build metadata.' }
$editorVersionText = Get-Content -LiteralPath (Join-Path $project 'ProjectSettings/ProjectVersion.txt') -Raw
$editorVersion = [regex]::Match($editorVersionText, '(?m)^m_EditorVersion: (.+)$').Groups[1].Value.Trim()
$unity = Join-Path $env:ProgramFiles ('Unity/Hub/Editor/' + $editorVersion + '/Editor/Unity.exe')
if (-not (Test-Path -LiteralPath $unity)) { throw "Unity Editor is missing: $unity" }
$editorFolder = Join-Path $project 'Assets/Editor'
New-Item -ItemType Directory -Force -Path $editorFolder | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'ArtelLocalBuild.cs') -Destination (Join-Path $editorFolder 'ArtelLocalBuild.cs') -Force
$build = Join-Path $runtime.FullName ('build-v' + $bundleVersion)
New-Item -ItemType Directory -Force -Path $build | Out-Null
$output = Join-Path $build 'WordVenture.exe'
$successPath = $output + '.success'
if (Test-Path -LiteralPath $successPath) { Remove-Item -LiteralPath $successPath }
$log = Join-Path $runtime.FullName ('unity-build-v' + $bundleVersion + '.log')
$unityArgs = @('-batchmode', '-quit', '-nographics', '-projectPath', ('"' + $project + '"'),
    '-executeMethod', 'ArtelLocalBuild.BuildWindows64', '-artelBuildPath', ('"' + $output + '"'), '-logFile', ('"' + $log + '"'))
Write-Output ('Unity build: ' + $bundleVersion + ' / SDK ' + $source.sdkCommit)
$process = Start-Process -FilePath $unity -ArgumentList $unityArgs -WindowStyle Hidden -PassThru
$process.WaitForExit()
if (-not (Test-Path -LiteralPath $successPath)) { throw "Unity build failed. Inspect $log" }
if ((Get-Content -LiteralPath $successPath -Raw).Trim() -ne $bundleVersion) { throw 'Build success version mismatch.' }
$dll = Join-Path $build 'WordVenture_Data/Managed/Assembly-CSharp.dll'
$dllBytes = [System.IO.File]::ReadAllBytes($dll)
if ([System.Text.Encoding]::UTF8.GetString($dllBytes) -notmatch 'WordVentureGameFunctions') {
    throw 'ARTEL_GAME_FUNCTIONS was not included in the player assembly.'
}
$parent = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Wordventure build'
$label = 'ARTEL-PR177-v' + $bundleVersion + '-' + (Get-Date -Format 'yyyyMMdd')
$destination = Join-Path $parent $label
if (Test-Path -LiteralPath $destination) { $destination += '-' + (Get-Date -Format 'HHmmss') }
if (Test-Path -LiteralPath $destination) { throw 'Desktop destination already exists.' }
New-Item -ItemType Directory -Path $destination | Out-Null
Get-ChildItem -LiteralPath $build | Where-Object Name -ne 'WordVenture.exe.success' | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination $destination -Recurse
}
$sdkRelative = 'WordVenture_Data/Managed/Artel.Runtime.dll'
if ((Get-FileHash -LiteralPath (Join-Path $build $sdkRelative)).Hash -ne
    (Get-FileHash -LiteralPath (Join-Path $destination $sdkRelative)).Hash) { throw 'Copied SDK assembly hash mismatch.' }
$info = [ordered]@{
    sdkCommit = $source.sdkCommit
    gameCommit = $source.gameCommit
    upstreamCommit = $source.upstreamCommit
    version = $bundleVersion
    unity = $editorVersion
    developmentBuild = $true
    gameFunctions = $true
    folder = $destination
    server = 'http://127.0.0.1:8090'
}
$json = $info | ConvertTo-Json
$json | Set-Content -LiteralPath (Join-Path $destination 'build-info.json') -Encoding utf8
$json | Set-Content -LiteralPath $desktopInfoPath -Encoding utf8
@'
@echo off
start "" "%~dp0WordVenture.exe" -artel-server 127.0.0.1:8090 -artel-secure false -artel-project 1 -screen-fullscreen 0 -screen-width 1280 -screen-height 720
'@ | Set-Content -LiteralPath (Join-Path $destination 'Start-Local.cmd') -Encoding ascii
Write-Output ('Desktop build ready: ' + $destination)
Write-Output ('Build log: ' + $log)
Write-Output 'Existing services and game processes were not restarted.'
