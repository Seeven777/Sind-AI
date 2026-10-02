@echo off
set "CFG=%LOCALAPPDATA%\JarvisNext\config"
if not exist "%CFG%" mkdir "%CFG%"
start "" explorer "%CFG%"
