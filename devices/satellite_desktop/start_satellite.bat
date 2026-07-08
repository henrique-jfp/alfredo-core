@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
echo Iniciando Satelite de Teste (Escritorio) - Alfredo OS
echo ======================================================

:: Verificar se o ambiente virtual existe
if not exist "venv" (
    echo [INFO] Criando ambiente virtual Python (venv)...
    python -m venv venv
    
    echo [INFO] Atualizando pip...
    venv\Scripts\python -m pip install --upgrade pip
    
    echo [INFO] Instalando dependencias (sounddevice, numpy, websockets, vosk, webrtcvad)...
    REM webrtcvad-wheels é a versão pré-compilada para Windows, evita erros de C++ Build Tools
    venv\Scripts\pip install sounddevice numpy websockets vosk requests webrtcvad-wheels playsound==1.2.2
    
    echo [INFO] Dependencias instaladas com sucesso!
)

echo [INFO] Conectando ao servidor central (pvserver)...
venv\Scripts\python main.py

pause
