param (
    [ValidateSet("x86", "x64")] $arch
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$PSDefaultParameterValues['*:ErrorAction'] = 'Stop'

if (-not (Get-Command -Name "cmake")) {
    $vspath = (@() + (&"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe" -version 16.0 -prerelease -property installationpath))[-1]
    $cmake_path = $vspath + "Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin"
    $env:PATH += ";$cmake_path"
}

cmake.exe -G "Visual Studio 17 2022", "-A" $(if ($arch -eq "x86") { "Win32" } else { "x64" }) "$PSScriptRoot\.."
cmake.exe --build . --config Debug -j --verbose --target package
ctest.exe -C Debug --output-on-failure
