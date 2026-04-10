@echo off
REM ==========================================
REM SearXNG MCP Server - Config Editor (Windows)
REM ==========================================

set CONFIG_DIR=%USERPROFILE%\.searxng-mcp
set CONFIG_FILE=%CONFIG_DIR%\.env

echo.
echo ==========================================
echo  SearXNG MCP Server - Configuration
echo ==========================================
echo.

if not exist "%CONFIG_DIR%" (
    echo [Error] Config directory not found: %CONFIG_DIR%
    echo.
    echo Please run the following command first:
    echo   npm install @otbossam/searxng-mcp-server
    echo.
    pause
    exit /b 1
)

if not exist "%CONFIG_FILE%" (
    echo [Error] Config file not found: %CONFIG_FILE%
    echo.
    echo Please run the following command first:
    echo   npm install @otbossam/searxng-mcp-server
    echo.
    pause
    exit /b 1
)

echo Config file: %CONFIG_FILE%
echo.
echo Opening in Notepad...
echo.

REM Open config file in Notepad
notepad "%CONFIG_FILE%"

echo.
echo ==========================================
echo  Settings Saved!
echo ==========================================
echo.
echo To apply your changes, restart the server:
echo   npx -y @otbossam/searxng-mcp-server
echo.
echo Note: Docker container restart is NOT required.
echo       Changes are applied when Python server starts.
echo.
pause
