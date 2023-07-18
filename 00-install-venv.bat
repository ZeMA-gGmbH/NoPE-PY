@echo off
set DIR=%~dp0
cd "%DIR%"

rmdir /s /q venv

python -m venv ./venv
call ./venv/Scripts/activate

pip install -r requirements.txt
