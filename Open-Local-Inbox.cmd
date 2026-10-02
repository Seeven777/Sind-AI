@echo off
set "INBOX=%LOCALAPPDATA%\JarvisNext\connectors\inbox"
if not exist "%INBOX%" mkdir "%INBOX%"
start "" explorer "%INBOX%"
