@echo off
call conda.bat activate app || exit /b 1
start "" /B /MIN pythonw.exe main.py
