$ErrorActionPreference = 'Stop'
$bash = Join-Path $env:ProgramFiles 'Git/bin/bash.exe'
if (-not (Test-Path -LiteralPath $bash)) { throw 'Git for Windows bash is required.' }
& $bash (Join-Path $PSScriptRoot 'dev') @args
exit $LASTEXITCODE
