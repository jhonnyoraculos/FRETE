@echo off
setlocal

REM Executa o aplicativo Tkinter sem precisar de .exe
pushd "%~dp0"

REM Sincroniza os arquivos do app com a outra pasta
set "PATH_A=C:\Users\jrferragens\OneDrive - JR Ferragens & Madeiras\Arquivos de Gabriela Costa - Transportes\ARQUIVOS TRANSPORTE\FRETE"
set "PATH_B=C:\Users\jrferragens\OneDrive - JR Ferragens & Madeiras\01\HTML\FRETE"
set "CURRENT=%~dp0"
if "%CURRENT:~-1%"=="\" set "CURRENT=%CURRENT:~0,-1%"
set "OTHER="
if /I "%CURRENT%"=="%PATH_A%" set "OTHER=%PATH_B%"
if /I "%CURRENT%"=="%PATH_B%" set "OTHER=%PATH_A%"
if defined OTHER if exist "%OTHER%" (
  for %%F in (app_frete.py frete_calculo.py frete_dados.py placas_permitidas.txt logo-jr.png run_app_frete.bat) do (
    if exist "%CURRENT%\%%F" copy /Y "%CURRENT%\%%F" "%OTHER%\%%F" >nul
  )
  if exist "%CURRENT%\data" xcopy "%CURRENT%\data" "%OTHER%\data\" /E /I /Y /D >nul
)

REM Tenta primeiro com o launcher do Python (py), depois python direto
py -3 app_frete.py >nul 2>&1
if %errorlevel% equ 0 goto done

python app_frete.py
if %errorlevel% equ 0 goto done

echo Nao foi possivel iniciar o aplicativo.
echo Verifique se o Python esta instalado e disponivel no PATH.
echo Tente executar: py --version ou python --version
pause

:done
popd
endlocal
