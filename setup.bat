@echo off
REM Occupancy Pipeline - Windows Batch Setup
REM Usage: setup.bat [env_name]
REM Default env name: occupancy_env

setlocal enabledelayedexpansion

set "ENV_NAME=%~1"
if "%ENV_NAME%"=="" set "ENV_NAME=occupancy_env"

set "REPO_ROOT=%~dp0"
set "ENV_YML=%REPO_ROOT%infrastructure\env\occupancy_env.yml"
set "SRC_PATH=%REPO_ROOT%src"
set "OUTPUT_DIR=%REPO_ROOT%outputs"

echo ================================================================
echo   Occupancy Pipeline -- Environment Setup
echo   Environment : %ENV_NAME%
echo ================================================================

where conda >nul 2>&1
if errorlevel 1 (
    echo ERROR: conda not found in PATH.
    echo Install Miniconda from https://docs.conda.io/en/latest/miniconda.html
    exit /b 1
)

if not exist "%ENV_YML%" (
    echo ERROR: occupancy_env.yml not found at %ENV_YML%
    exit /b 1
)

conda env list | findstr /C:"%ENV_NAME%" >nul 2>&1
if not errorlevel 1 (
    echo Environment '%ENV_NAME%' exists -- updating...
    conda env update -n "%ENV_NAME%" -f "%ENV_YML%" --prune
) else (
    echo Creating conda environment '%ENV_NAME%'...
    conda env create -f "%ENV_YML%"
)
if errorlevel 1 (
    echo ERROR: conda env create/update failed.
    exit /b 1
)

if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

echo Configuring environment variables...
conda env config vars set -n "%ENV_NAME%" OCCUPANCY_OUTPUT_DIR="%OUTPUT_DIR%"
if errorlevel 1 (
    echo ERROR: failed to configure conda environment variables.
    exit /b 1
)

echo.
echo Installing occupancy package in editable mode...
conda run -n "%ENV_NAME%" pip install -e . --no-deps
if errorlevel 1 (
    echo ERROR: pip install -e . failed.
    exit /b 1
)

echo.
echo Verifying installation...
conda run -n "%ENV_NAME%" python -m occupancy --help

echo.
echo ================================================================
echo   Setup complete.
echo   Reactivate: conda deactivate ^&^& conda activate %ENV_NAME%
echo   Verify:     python -m occupancy --help
echo ================================================================
endlocal
