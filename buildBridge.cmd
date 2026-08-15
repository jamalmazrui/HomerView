@echo off
rem buildBridge.cmd -- compile HomerViewBridge.exe
rem
rem Uses csc.exe from the .NET Framework, which is on every Windows 10 and 11
rem machine already. No Visual Studio, no NuGet, no download.
setlocal
pushd "%~dp0"
set "csc=%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if not exist "%csc%" (
  echo The .NET Framework compiler was not found at:
  echo   %csc%
  echo That file ships with Windows, so something is unusual about this machine.
  popd & exit /b 1
)
echo Compiling HomerViewBridge.exe with %csc%
"%csc%" /nologo /target:exe /platform:x64 /out:HomerViewBridge.exe HomerViewBridge.cs
set exitCode=%errorlevel%
if %exitCode%==0 (echo Built HomerViewBridge.exe) else (echo Compilation failed with code %exitCode%)
popd
endlocal & exit /b %exitCode%
