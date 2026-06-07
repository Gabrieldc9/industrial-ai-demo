@echo off
echo ============================================
echo  Industrial AI Demo — Iniciando servidor
echo ============================================

set "ROOT=%~dp0"

:: Verificar .env
if not exist "%ROOT%.env" (
  echo [!] No hay .env. Copiando .env.example...
  copy "%ROOT%.env.example" "%ROOT%.env" >nul
  echo     Edita %ROOT%.env y agrega ANTHROPIC_API_KEY
  echo.
)

:: Verificar que hay frontend compilado
if not exist "%ROOT%frontend\dist\index.html" (
  echo [!] Frontend no compilado. Ejecutando build...
  call "%ROOT%build-frontend.bat"
  if errorlevel 1 (
    echo [ERROR] Build del frontend fallo
    pause
    exit /b 1
  )
)

:: Crear script Python launcher con PYTHONPATH correcto
set "LAUNCHER=C:\temp-industrial-build\run_server.py"
if not exist "C:\temp-industrial-build" mkdir "C:\temp-industrial-build"

echo import sys > "%LAUNCHER%"
echo import os >> "%LAUNCHER%"
echo if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8') >> "%LAUNCHER%"
echo if hasattr(sys.stderr, 'reconfigure'): sys.stderr.reconfigure(encoding='utf-8') >> "%LAUNCHER%"
echo sys.path.insert(0, r'%ROOT%backend') >> "%LAUNCHER%"
echo # Load .env >> "%LAUNCHER%"
echo try: >> "%LAUNCHER%"
echo     from dotenv import load_dotenv >> "%LAUNCHER%"
echo     load_dotenv(r'%ROOT%.env') >> "%LAUNCHER%"
echo except ImportError: pass >> "%LAUNCHER%"
echo import uvicorn >> "%LAUNCHER%"
echo port = int(os.environ.get('PORT', 8000)) >> "%LAUNCHER%"
echo print(f'Starting on http://localhost:{port}') >> "%LAUNCHER%"
echo print(f'API docs: http://localhost:{port}/docs') >> "%LAUNCHER%"
echo uvicorn.run('main:app', host='0.0.0.0', port=port, reload=True, reload_dirs=[r'%ROOT%backend']) >> "%LAUNCHER%"

echo.
echo Servidor en http://localhost:8000
echo API docs: http://localhost:8000/docs
echo.
echo Para detener: Ctrl+C
echo.

python "%LAUNCHER%"
pause
