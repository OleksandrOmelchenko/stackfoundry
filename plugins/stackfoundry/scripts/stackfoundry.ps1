# stackfoundry helper CLI launcher for Windows without sh. Same contract as stackfoundry.sh: finds Python >= 3.11 and
# runs the CLI isolated (-I), so a planted module in the user's repo is never imported.
# Usage: pwsh -NoProfile -File <plugin root>/scripts/stackfoundry.ps1 <subcommand> [args]
$ErrorActionPreference = 'Stop'
$cli = Join-Path $PSScriptRoot 'stackfoundry/cli.py'
$check = 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'

foreach ($candidate in @(@('python3'), @('python'), @('py', '-3'))) {
    $exe = Get-Command $candidate[0] -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $exe -or -not [System.IO.Path]::IsPathRooted($exe.Source)) { continue }
    $pre = @($candidate | Select-Object -Skip 1)
    & $exe.Source @pre -c $check *> $null
    if ($LASTEXITCODE -eq 0) {
        & $exe.Source @pre -I $cli @args
        exit $LASTEXITCODE
    }
}

[Console]::Error.WriteLine('stackfoundry: Python 3.11 or newer is required (tried python3, python, py -3).')
# Exit 0 when called as a hook, so a missing Python never blocks the session; the CLI's own callers see the message.
if ($args.Count -gt 0 -and $args[0] -eq 'guard') { exit 0 }
exit 127
