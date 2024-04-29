param (
    [ValidateSet("x86", "x64")] $arch
)
$vs2019_path = (@() + (&"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe" -version 16.0 -property installationpath -prerelease))[-1]
Import-Module (Join-Path $vs2019_path "Common7\Tools\Microsoft.VisualStudio.DevShell.dll")

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$PSDefaultParameterValues['*:ErrorAction']='Stop'

if (($arch -eq "x86")) {
    Enter-VsDevShell -VsInstallPath $vs2019_path -SkipAutomaticLocation -DevCmdArguments "-arch=x86"
}
elseif (($arch -eq "x64")) {
    Enter-VsDevShell -VsInstallPath $vs2019_path -SkipAutomaticLocation -DevCmdArguments "-arch=amd64"
}
if (!("$args" -eq "")) {
    Invoke-Expression "$args"
}
