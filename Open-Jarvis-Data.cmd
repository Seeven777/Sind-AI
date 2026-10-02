@echo off
set "DATA=%LOCALAPPDATA%\JarvisNext"
if not exist "%DATA%" mkdir "%DATA%"
start "" explorer "%DATA%"
