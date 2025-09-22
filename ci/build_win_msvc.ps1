# cppforge-sync
param (
    [ValidateSet("x86", "x64", "arm64")] $arch
)

if (-not (Get-Command -Name "cmake")) {
    $vspath = (@() + (&"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe" -property installationpath))[-1]
    $cmake_path = $vspath + "Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin"
    $env:PATH += ";$cmake_path"
}

cmake.exe -G "Visual Studio 17 2022", "-A" $(if ($arch -eq "x86") { "Win32" } else { $arch }) "$PSScriptRoot\.."
if (-not $?) {throw "CMake Generate Failed"}
cmake.exe --build . --config Debug -j --verbose --target package
if (-not $?) {throw "CMake Build Failed"}
ctest.exe -C Debug --output-on-failure
if (-not $?) {throw "Ctest Failed"}
