@echo off
::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
::                                                                            ::
::                    SOCIETY-PANEL Unified Startup Script                    ::
::                            (Windows Version)                               ::
::                                                                            ::
::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
::
:: Description:
::   This script automates the setup and launch of both the backend and frontend
::   services for the SOCIETY-PANEL. It handles dependency checks, virtual 
::   environment management, and graceful shutdown.
::
:: Usage:
::   start_society_panel.bat
::
:: Requirements:
::   - Python 3.11 or higher
::   - Node.js and npm
::   - Internet connection (for package installation)
::
:: Author:  SOCIETY-PANEL Team
:: Version: 3.0
::
::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

setlocal EnableDelayedExpansion

:: ==============================================================================
:: Global Configuration
:: ==============================================================================

:: Directory Paths
set "ROOT_DIR=%CD%"
set "BACKEND_DIR=society-panel\backend"
set "FRONTEND_DIR=society-panel\frontend"

:: Server Ports
set "BACKEND_PORT=8001"
set "FRONTEND_PORT=5174"

:: Python Version Requirements
set "REQUIRED_PYTHON_MAJOR=3"
set "REQUIRED_PYTHON_MINOR=11"

:: PyPI Mirror Configuration (Chinese mirror for faster downloads)
set "PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/"
set "PIP_TRUSTED_HOST=mirrors.aliyun.com"

:: ==============================================================================
:: Utility Subroutines
:: ==============================================================================

GOTO :main

:: ------------------------------------------------------------------------------
:: @brief Print an info message with [INFO] prefix
:: @param %~1 Message to print
:: ------------------------------------------------------------------------------
:print_info
    echo [INFO] %~1
    GOTO :EOF

:: ------------------------------------------------------------------------------
:: @brief Print a warning message with [WARN] prefix
:: @param %~1 Message to print
:: ------------------------------------------------------------------------------
:print_warn
    echo [WARN] %~1
    GOTO :EOF

:: ------------------------------------------------------------------------------
:: @brief Print an error message with [ERROR] prefix
:: @param %~1 Message to print
:: ------------------------------------------------------------------------------
:print_error
    echo [ERROR] %~1
    GOTO :EOF

:: ------------------------------------------------------------------------------
:: @brief Find a suitable Python interpreter (>= 3.11)
:: @return Sets PYTHON_CMD variable if found, empty if not found
:: ------------------------------------------------------------------------------
:find_python
    for %%P in (python3.11 python3.12 python py) do (
        where %%P >NUL 2>&1
        if !ERRORLEVEL! EQU 0 (
            for /f "tokens=2 delims= " %%V in ('%%P --version 2^>^&1') do (
                for /f "tokens=1,2 delims=." %%A in ("%%V") do (
                    if %%A GEQ %REQUIRED_PYTHON_MAJOR% (
                        if %%B GEQ %REQUIRED_PYTHON_MINOR% (
                            :: Added check: LSS 13 to exclude Python 3.13
                            if %%B LSS 13 (
                                set "PYTHON_CMD=%%P"
                                GOTO :EOF
                            )
                        )
                    )
                )
            )
        )
    )
    set "PYTHON_CMD="
    GOTO :EOF

:: ------------------------------------------------------------------------------
:: @brief Gracefully shutdown all services and cleanup resources
:: @details Terminates backend/frontend processes and shuts down Ray cluster
:: ------------------------------------------------------------------------------
:cleanup
    CALL :print_info "Shutting down all services..."
    
    :: Terminate backend process on port
    for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":%BACKEND_PORT%" ^| findstr "LISTENING"') do (
        taskkill /F /PID %%a >NUL 2>&1
    )
    
    :: Terminate frontend process on port
    for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":%FRONTEND_PORT%" ^| findstr "LISTENING"') do (
        taskkill /F /PID %%a >NUL 2>&1
    )
    
    :: Shutdown Ray cluster if running
    ray status >NUL 2>&1
    if !ERRORLEVEL! EQU 0 (
        CALL :print_info "Shutting down Ray cluster..."
        ray stop
        CALL :print_info "Ray cluster has been shut down."
    )
    
    echo Cleanup complete!
    GOTO :EOF

:: ==============================================================================
:: Main Entry Point
:: ==============================================================================
:main

:: ==============================================================================
:: Pre-cleanup: Stop Lingering Services
:: ==============================================================================

CALL :print_info "Performing pre-cleanup to stop any lingering services..."

:: Kill processes occupying backend port
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":%BACKEND_PORT%" ^| findstr "LISTENING" 2^>NUL') do (
    taskkill /F /PID %%a >NUL 2>&1
)

:: Kill processes occupying frontend port
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":%FRONTEND_PORT%" ^| findstr "LISTENING" 2^>NUL') do (
    taskkill /F /PID %%a >NUL 2>&1
)

:: Stop Ray cluster if running
ray status >NUL 2>&1
if %ERRORLEVEL% EQU 0 (
    ray stop
)

CALL :print_info "Pre-cleanup finished."

:: ==============================================================================
:: Clean Workspace and Logs
:: ==============================================================================

CALL :print_info "Cleaning backend workspace and logs directories..."

:: Clean entire workspace directory contents
if exist "%BACKEND_DIR%\workspace" (
    del /Q /S "%BACKEND_DIR%\workspace\*" >NUL 2>&1
    for /d %%D in ("%BACKEND_DIR%\workspace\*") do rd /S /Q "%%D" >NUL 2>&1
    CALL :print_info "  - Cleaned: workspace/"
)

:: Clean backend logs directory
if exist "%BACKEND_DIR%\logs" (
    del /Q /S "%BACKEND_DIR%\logs\*" >NUL 2>&1
    for /d %%D in ("%BACKEND_DIR%\logs\*") do rd /S /Q "%%D" >NUL 2>&1
    :: Recreate subdirectory structure
    mkdir "%BACKEND_DIR%\logs\framework" >NUL 2>&1
    mkdir "%BACKEND_DIR%\logs\app" >NUL 2>&1
    CALL :print_info "  - Cleaned: logs/ (framework/, app/)"
)

CALL :print_info "Workspace and logs cleanup finished."

:: ==============================================================================
:: Backend Service Setup and Launch
:: ==============================================================================

CALL :print_info "Preparing backend service..."

if not exist "%BACKEND_DIR%" (
    CALL :print_error "Backend directory not found: %BACKEND_DIR%"
    GOTO :error_exit
)

pushd "%BACKEND_DIR%"

:: Find and validate Python version
CALL :find_python
if "%PYTHON_CMD%"=="" (
    CALL :print_error "Python %REQUIRED_PYTHON_MAJOR%.%REQUIRED_PYTHON_MINOR%+ is required but not found!"
    CALL :print_error "Please install Python 3.11 or higher from https://www.python.org/downloads/"
    popd
    GOTO :error_exit
)

for /f "tokens=*" %%V in ('%PYTHON_CMD% --version 2^>^&1') do set "PYTHON_VERSION=%%V"
CALL :print_info "Using Python: %PYTHON_CMD% (%PYTHON_VERSION%)"

:: Create or activate virtual environment
if not exist ".venv" (
    CALL :print_warn "Backend virtual environment not found. Creating with %PYTHON_CMD%..."
    %PYTHON_CMD% -m venv .venv
    if !ERRORLEVEL! NEQ 0 (
        CALL :print_error "Failed to create virtual environment."
        popd
        GOTO :error_exit
    )
    CALL ".venv\Scripts\activate.bat"
    CALL :print_info "Installing SSL certificates (certifi)..."
    pip install --trusted-host %PIP_TRUSTED_HOST% -i %PIP_INDEX_URL% certifi
) else (
    CALL ".venv\Scripts\activate.bat"
)

:: Install/update backend dependencies
if not exist ".venv\pip_installed_reqs" (
    CALL :print_info "Upgrading pip to latest version..."
    pip install --trusted-host %PIP_TRUSTED_HOST% -i %PIP_INDEX_URL% --upgrade pip
    CALL :print_info "Backend dependencies need to be installed/updated. Running pip install..."
    pip install --trusted-host %PIP_TRUSTED_HOST% -i %PIP_INDEX_URL% -r requirements.txt
    if !ERRORLEVEL! EQU 0 (
        copy requirements.txt .venv\pip_installed_reqs >NUL
    )
)

:: Launch backend server
CALL :print_info "Starting FastAPI backend (Port: %BACKEND_PORT%)..."
start "Backend" cmd /c "cd /d %CD% && .venv\Scripts\activate.bat && uvicorn app.main:app --reload --host 0.0.0.0 --port %BACKEND_PORT%"

popd

:: ==============================================================================
:: Frontend Service Setup and Launch
:: ==============================================================================

CALL :print_info "Preparing frontend service..."

if not exist "%FRONTEND_DIR%" (
    CALL :print_error "Frontend directory not found: %FRONTEND_DIR%"
    GOTO :error_exit
)

pushd "%FRONTEND_DIR%"

:: Verify npm is available
where npm >NUL 2>&1
if %ERRORLEVEL% NEQ 0 (
    CALL :print_error "npm is not installed. Please install Node.js from https://nodejs.org/"
    popd
    GOTO :error_exit
)

:: Install/update frontend dependencies
if not exist "node_modules" (
    CALL :print_info "Frontend dependencies need to be installed. Running npm install..."
    npm install
)

:: Launch frontend dev server
CALL :print_info "Starting Vite frontend dev server (Port: %FRONTEND_PORT%)..."
start "Frontend" cmd /c "cd /d %CD% && npm run dev -- --port %FRONTEND_PORT% --host"

popd

:: ==============================================================================
:: Startup Complete - Wait for Termination
:: ==============================================================================

echo.
CALL :print_info "=================================================="
CALL :print_info "SOCIETY-PANEL has been launched!"
CALL :print_info "  - Backend API available at: http://localhost:%BACKEND_PORT%"
CALL :print_info "  - Frontend UI accessible at: http://localhost:%FRONTEND_PORT%"
CALL :print_info "Press any key to shut down all services..."
CALL :print_info "=================================================="
echo.

pause >NUL

:: Cleanup on exit
CALL :cleanup
exit /b 0

:: ==============================================================================
:: Error Handler
:: ==============================================================================
:error_exit
CALL :print_error "Script terminated due to an error."
CALL :cleanup
exit /b 1
