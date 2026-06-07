@echo off
echo Construyendo frontend React...

:: Copiar fuentes a directorio local (evitar conflictos Google Drive + node_modules)
set SRC=%~dp0frontend
set LOCAL=C:\temp-industrial-build\frontend

if exist "%LOCAL%\node_modules" goto build

echo Instalando dependencias...
xcopy "%SRC%\package.json" "%LOCAL%\" /Y /Q
xcopy "%SRC%\vite.config.js" "%LOCAL%\" /Y /Q
xcopy "%SRC%\tailwind.config.js" "%LOCAL%\" /Y /Q
xcopy "%SRC%\postcss.config.js" "%LOCAL%\" /Y /Q
xcopy "%SRC%\index.html" "%LOCAL%\" /Y /Q
xcopy "%SRC%\src" "%LOCAL%\src\" /E /Y /Q
cd /d "%LOCAL%"
npm install
goto build_actual

:build
echo Actualizando fuentes...
xcopy "%SRC%\package.json" "%LOCAL%\" /Y /Q
xcopy "%SRC%\vite.config.js" "%LOCAL%\" /Y /Q
xcopy "%SRC%\tailwind.config.js" "%LOCAL%\" /Y /Q
xcopy "%SRC%\postcss.config.js" "%LOCAL%\" /Y /Q
xcopy "%SRC%\index.html" "%LOCAL%\" /Y /Q
xcopy "%SRC%\src" "%LOCAL%\src\" /E /Y /Q

:build_actual
cd /d "%LOCAL%"
npm run build
if errorlevel 1 goto error

echo Copiando dist al proyecto...
if exist "%SRC%\dist" rd /s /q "%SRC%\dist"
xcopy "%LOCAL%\dist" "%SRC%\dist\" /E /Y /Q

echo.
echo [OK] Frontend compilado en %SRC%\dist
goto end

:error
echo [ERROR] Fallo el build
exit /b 1

:end
