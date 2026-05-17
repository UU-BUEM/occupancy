param(
    [string]$EnvName = "occupancy_env",
    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "================================================================"
Write-Host "  Occupancy Pipeline - Environment Setup"
Write-Host "  Environment : $EnvName"
Write-Host "  Date        : $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Host "================================================================"

$condaCmd = Get-Command conda -ErrorAction SilentlyContinue
if (-not $condaCmd) {
    Write-Error @"
conda not found in PATH.
Install Miniconda from https://docs.conda.io/en/latest/miniconda.html
then restart this terminal and rerun setup.ps1.
"@
    exit 1
}

$repoRoot = $PSScriptRoot
$envYml = Join-Path $repoRoot "infrastructure\env\occupancy_env.yml"
if (-not (Test-Path $envYml)) {
    Write-Error "occupancy_env.yml not found at: $envYml"
    exit 1
}

$envExists = conda env list | Select-String -SimpleMatch $EnvName
if ($envExists -and -not $Force) {
    Write-Host "Environment '$EnvName' exists - updating..."
    conda env update -n $EnvName -f $envYml --prune
} else {
    if ($Force -and $envExists) {
        conda env remove -n $EnvName -y
    }
    Write-Host "Creating conda environment '$EnvName'..."
    conda env create -f $envYml
}

$srcPath = Join-Path $repoRoot "src"
$outputDir = Join-Path $repoRoot "outputs"
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

conda env config vars set -n $EnvName OCCUPANCY_OUTPUT_DIR=$outputDir PYTHONPATH=$srcPath

# Create the 'occupancy' console entry point.
# conda develop src is NOT used here (requires conda-build which has known
# libarchive issues on Windows). A lightweight .bat wrapper achieves the same.
Write-Host "Creating 'occupancy' console entry point..."
$envPrefix = (conda run -n $EnvName python -c "import sys; print(sys.prefix)").Trim()
if ($envPrefix) {
    $wrapperPath = Join-Path $envPrefix "Scripts\occupancy.bat"
    "@python -m occupancy %*" | Set-Content -Path $wrapperPath -Encoding ASCII
    Write-Host "  Console script  : $wrapperPath" -ForegroundColor Green
} else {
    Write-Warning "Could not locate env prefix; skipping console script."
}

Write-Host ""
Write-Host "================================================================"
Write-Host "  Setup complete."
Write-Host "  Reactivate: conda deactivate; conda activate $EnvName"
Write-Host "  Verify:     python -m occupancy --help"
Write-Host "================================================================"
