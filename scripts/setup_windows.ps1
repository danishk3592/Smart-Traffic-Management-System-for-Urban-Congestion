[CmdletBinding()]
param(
    [switch]$CheckOnly
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$venvPath = Join-Path $repoRoot 'Ai\.venv'
$venvPython = Join-Path $venvPath 'Scripts\python.exe'
$checkerPath = Join-Path $repoRoot 'scripts\check_environment.py'

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)][string]$Executable,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [Parameter(Mandatory = $true)][string]$Purpose
    )

    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Purpose failed with exit code $LASTEXITCODE. See the command output above."
    }
}

function Get-Python314 {
    $launcher = Get-Command py -ErrorAction SilentlyContinue
    if ($null -ne $launcher) {
        $probe = & $launcher.Source -3.14 -c 'import sys; print(sys.version.split()[0])' 2>$null
        if ($LASTEXITCODE -eq 0 -and "$probe" -match '^3\.14\.') {
            return @{ Executable = $launcher.Source; Prefix = @('-3.14'); Version = "$probe" }
        }
    }

    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($null -ne $pythonCommand) {
        $probe = & $pythonCommand.Source -c 'import sys; print(sys.version.split()[0])' 2>$null
        if ($LASTEXITCODE -eq 0 -and "$probe" -match '^3\.14\.') {
            return @{ Executable = $pythonCommand.Source; Prefix = @(); Version = "$probe" }
        }
    }

    throw 'Python 3.14 was not found. Install 64-bit Python 3.14 from https://www.python.org/downloads/windows/ and reopen PowerShell.'
}

try {
    if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
        if ($CheckOnly) {
            throw "Project environment not found at '$venvPython'. Run this script without -CheckOnly to create it."
        }

        $python = Get-Python314
        Write-Host "Creating Ai/.venv with Python $($python.Version)..."
        Invoke-Checked -Executable $python.Executable -Arguments ($python.Prefix + @('-m', 'venv', $venvPath)) -Purpose 'Creating the virtual environment'
    }

    $venvVersion = & $venvPython -c 'import sys; print(sys.version.split()[0])'
    if ($LASTEXITCODE -ne 0 -or "$venvVersion" -notmatch '^3\.14\.') {
        throw "Ai/.venv must use Python 3.14; found '$venvVersion'. The script will not replace an existing environment."
    }

    if (-not $CheckOnly) {
        Write-Host "Installing the CPU PyTorch build for Python $venvVersion (CUDA is optional)..."
        Invoke-Checked -Executable $venvPython -Arguments @('-m', 'pip', 'install', '--no-deps', '--index-url', 'https://download.pytorch.org/whl/cpu', 'torch==2.14.1') -Purpose 'Installing CPU PyTorch'
        Invoke-Checked -Executable $venvPython -Arguments @('-m', 'pip', 'install', '-r', (Join-Path $repoRoot 'requirements.lock.txt')) -Purpose 'Installing the pinned project dependencies'
        Invoke-Checked -Executable $venvPython -Arguments @('-m', 'pip', 'install', '--no-deps', '--no-build-isolation', '--editable', $repoRoot) -Purpose 'Installing the project package'
    }

    Write-Host 'Checking Python packages, SUMO, configuration files, and project scripts...'
    Invoke-Checked -Executable $venvPython -Arguments @($checkerPath) -Purpose 'Environment check'
    Write-Host 'Windows environment setup is ready.'
}
catch {
    Write-Error "STMS setup failed: $($_.Exception.Message)"
    exit 1
}
