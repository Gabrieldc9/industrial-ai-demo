@echo off
echo ============================================
echo  Industrial Demo — Iniciando DEV
echo ============================================

set PORT=8000
set "BACKEND=%~dp0backend"

:: Verificar .env
if not exist "%~dp0.env" (
  echo [WARN] No hay .env — copiando .env.example
  copy "%~dp0.env.example" "%~dp0.env" >nul
  echo [!] Edita .env y agrega tu ANTHROPIC_API_KEY
)

:: Cargar .env
for /f "tokens=1,2 delims==" %%a in (%~dp0.env) do (
  if not "%%a"=="" if not "%%b"=="" set %%a=%%b
)

:: Verificar que hay dist
if not exist "%~dp0frontend\dist\index.html" (
  echo [!] Frontend no compilado. Ejecutando build-frontend.bat...
  call "%~dp0build-frontend.bat"
)

:: Iniciar backend
echo.
echo Iniciando backend en http://localhost:%PORT%
echo Panel:    http://localhost:%PORT%/
echo API docs: http://localhost:%PORT%/docs
echo.
cd /d "%BACKEND%"
python -m uvicorn main:app --reload --port %PORT%
