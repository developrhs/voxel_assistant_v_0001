@echo off
chcp 65001 > nul
echo ========================================
echo    Intranet Local - Assistant
echo ========================================
echo.

cd /d D:\assistant

REM Ativar ambiente virtual
call venv\Scripts\activate.bat

REM Verificar dependências
echo Verificando dependências...
pip install -r intranet\requirements.txt --quiet

REM Criar diretórios necessários
if not exist "intranet\config\log" mkdir "intranet\config\log"
if not exist "intranet\assets\img" mkdir "intranet\assets\img"

echo.
echo ✓ Dependências verificadas
echo ✓ Diretórios criados
echo.
echo ========================================
echo    Servidor iniciando...
echo    URL: http://192.168.2.130:80
echo ========================================
echo.
echo Pressione Ctrl+C para parar o servidor
echo.

python intranet\app.py

pause