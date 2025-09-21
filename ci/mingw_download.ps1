# cppforge-sync
param ($msysdir)
$msysurl = 'https://github.com/msys2/msys2-installer/releases/download/nightly-x86_64/msys2-base-x86_64-latest.sfx.exe'
$ErrorActionPreference = "Stop"
if (!(Test-Path -Path $msysdir)) { New-Item -Path $msysdir -ItemType directory }
$msysdir = Resolve-Path $msysdir
$msysexe = "$msysdir/msys2.exe"
$bashexe = "$msysdir/msys64/usr/bin/bash.exe"
if (!(Test-Path -Path $bashexe)) {
    if (!(Test-Path -Path $msysexe)) { (New-Object System.Net.WebClient).DownloadFile($msysurl, $msysexe) }
    $msysexe = Resolve-Path $msysexe
    &$msysexe -y -o"$msysdir"
}

$bashexe = Resolve-Path $bashexe
# Run for the first time
&$bashexe -lc ' '
# Update MSYS2
&$bashexe -lc 'pacman --noconfirm -Syuu'  # Core update (in case any core packages are outdated)
&$bashexe -lc 'pacman --noconfirm -Syuu'  # Normal update
&$bashexe -lc 'pacman --noconfirm -S --needed base-devel mingw-w64-x86_64-toolchain'

Write-Output "##vso[task.prependpath]$msysdir\msys64\usr\bin"
Write-Output "##vso[task.prependpath]$msysdir\msys64\mingw64\bin"
Write-Output "`$env:PATH+=';${msysdir}\msys64\usr\bin;${msysdir}\msys64\mingw64\bin'"