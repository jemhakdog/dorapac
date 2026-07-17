@echo off
echo Checking if uv is installed...

where uv >nul 2>nul
if %errorlevel% neq 0 (
    echo uv is not installed. Installing uv...
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    
    REM Add uv to the current session's PATH just in case it's not immediately available
    set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"
) else (
    echo uv is already installed.
)

echo.
echo Installing dependencies and starting the Flask app...
uv run app.py
pause
