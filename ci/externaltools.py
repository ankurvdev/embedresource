#!/usr/bin/python3
import html.parser
import os
import pathlib
import platform
import re
import shutil
import stat
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from typing import Any, Callable, Dict, Optional

# EMSDK_VERSION = "3.1.14"  #This is what qt likes
EMSDK_VERSION = "latest"
ANDROID_NDK_VERSION = "26.0.10792818"

URLS = {}
URLS["cmake_Windows_amd64"] = {
    "downloadpage": "https://cmake.org/download/",
    "urlpattern": "https://github.com/Kitware/CMake/releases/download/v.*/cmake-.*-windows-x86_64.zip",
}

URLS["patch_Windows_amd64"] = ""
URLS["gradle_Linux_x86_64"] = URLS["gradle_Windows_amd64"] = "https://services.gradle.org/distributions/gradle-8.0-bin.zip"
URLS["flexbison_Windows_amd64"] = "https://github.com/lexxmark/winflexbison/releases/download/v2.5.25/win_flex_bison-2.5.25.zip"
URLS["ninja_Windows_amd64"] = "https://github.com/ninja-build/ninja/releases/download/v1.11.1/ninja-win.zip"
URLS["ninja_Linux_x86_64"] = "https://github.com/ninja-build/ninja/releases/download/v1.11.1/ninja-linux.zip"
URLS["rclone_Windows_amd64"] = "https://downloads.rclone.org/v1.54.1/rclone-v1.54.1-windows-amd64.zip"
URLS["rclone_Linux_x86_64"] = "https://downloads.rclone.org/v1.54.1/rclone-v1.54.1-linux-amd64.zip"
URLS["node_Windows_arm64"] = {
    "downloadpage": "https://nodejs.org/dist/latest-v20.x/",
    "urlpattern": "https://nodejs.org/dist/latest-v20.x/node-.*-win-arm64.zip",
}
URLS["node_Windows_amd64"] = {
    "downloadpage": "https://nodejs.org/dist/latest-v20.x/",
    "urlpattern": "https://nodejs.org/dist/latest-v20.x/node-.*-win-x64.zip",
}

URLS["node_Linux_x86_64"] = {
    "downloadpage": "https://nodejs.org/dist/latest-v20.x/",
    "urlpattern": "https://nodejs.org/dist/latest-v20.x/node-.*-linux-x64.tar.xz",
}
URLS["magick_Windows_amd64"] = {
    "downloadpage": "https://imagemagick.org/download/binaries/",
    "urlpattern": "https://imagemagick.org/download/binaries/ImageMagick-7.*-portable-Q16-x64.zip",
}

URLS["magick_Linux_x86_64"] = {
    "downloadpage": "https://imagemagick.org/script/download.php#linux",
    "urlpattern": "https://download.imagemagick.org/ImageMagick/download/binaries/magick",
    "archiveext": "bin",
}
URLS["rsvg-convert_Linux_x86_64"] = {
    "url": "https://github.com/ankurvdev/binaries/raw/main/rsvg-convert",
    "archiveext": "bin",
}
URLS["typesense-server_Linux_x86_64"] = {
    "url":"https://dl.typesense.org/releases/0.25.1/typesense-server-0.25.1-linux-amd64.tar.gz",
    "archiveext": "bin"
}
URLS["typesense-server_Linux_arm64"] = {
    "url":"https://dl.typesense.org/releases/0.25.1/typesense-server-0.25.1-linux-arm64.tar.gz",
    "archiveext": "bin"
}
URLS["rsvg-convert_Windows_amd64"] = "https://github.com/ankurvdev/binaries/raw/main/rsvg-convert.exe"
URLS["resvg_Windows_arm64"] = "https://github.com/RazrFalcon/resvg/releases/latest/download/resvg-win64.zip"
URLS["resvg_Windows_amd64"] = "https://github.com/RazrFalcon/resvg/releases/latest/download/resvg-win64.zip"
URLS["resvg_Linux_x86_64"] = "https://github.com/RazrFalcon/resvg/releases/latest/download/resvg-linux-x86_64.tar.gz"
URL_NOTEPAD = "http://download.notepad-plus-plus.org/repository/7.x/7.8.1/npp.7.8.1.bin.x64.zip"
URL_VSWHERE = "https://github.com/Microsoft/vswhere/releases/download/2.6.7/vswhere.exe"


class ExternalToolsDownloadError(Exception):
    pass


class HTMLUrlExtractor(html.parser.HTMLParser):
    def __init__(self, url: str):
        opener = urllib.request.URLopener()
        opener.addheader("User-Agent", "whatever")
        text = opener.open(url).read().decode("utf-8")
        self.baseurl = url
        self.urls: Dict[str, str] = {}
        self.href: Optional[str] = None
        self.text: Optional[str] = None
        super(HTMLUrlExtractor, self).__init__()
        self.feed(text)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        if tag == "a":
            self.text = ""
            self.href = next(
                (urllib.parse.urljoin(self.baseurl, attr[1]) for attr in attrs if attr[0] == "href"),
                None,
            )

    def handle_endtag(self, tag: str):
        if self.href is not None:
            # print(self.href, self.text)
            self.urls[self.href or ""] = self.text or ""
        self.href = None
        self.text = None

    def handle_data(self, data: str):
        if self.href is not None:
            self.text = data


def SearchFilename(sdir: pathlib.Path, name: str) -> pathlib.Path:
    for p in sdir.rglob(name):
        if p.is_file():
            return p
    return pathlib.Path()


def SearchExecutable(bindir: pathlib.Path, binname: str) -> pathlib.Path:
    if sys.platform == "win32":
        path = SearchFilename(bindir, binname + ".exe")
        path = SearchFilename(bindir, binname + ".bat") if not path.is_file() else path
        path = SearchFilename(bindir, binname + ".cmd") if not path.is_file() else path
    elif sys.platform == "linux":
        path = SearchFilename(bindir, binname)
        path = SearchFilename(bindir, binname + ".sh") if not path.is_file() else path
        if path.is_file():
            try:
                os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)
            except PermissionError:
                pass
    return path


def MoveUp(path: pathlib.Path):
    for p in path.iterdir():
        shutil.move(p, path.parent)
    path.rmdir()


def GetBinPath():
    try:
        import configenv  # pylint: ignore

        return pathlib.Path(configenv.ConfigEnv(None).GetConfigPath("DEVEL_BINPATH", make=True))
    except ImportError:
        return pathlib.Path().absolute()


class EmscriptenInfo:
    def __init__(
        self,
        sdkpath: pathlib.Path,
        envvars: dict[str:str],
        paths: list[str | pathlib.Path],
    ):
        self.sdkpath = sdkpath
        self.envvars = envvars
        self.paths = set([pathlib.Path(pathlike).absolute() for pathlike in paths])
        self.cmake_toolchain_file = sdkpath / "upstream" / "emscripten" / "cmake" / "Modules" / "Platform" / "Emscripten.cmake"


def DownloadEmscriptenInfoTo(path: pathlib.Path):
    path.mkdir(exist_ok=True, parents=True)
    sdkpath = path
    emconfig = sdkpath / ".emscripten"
    if not emconfig.exists():
        script = sdkpath / "emsdk.bat" if sys.platform == "win32" else sdkpath / "emsdk"
        if not script.exists():
            subprocess.check_call(
                [
                    "git",
                    "clone",
                    "https://github.com/emscripten-core/emsdk.git",
                    sdkpath,
                ]
            )
        subprocess.check_call(f"{script.as_posix()} install {EMSDK_VERSION}", shell=True, cwd=sdkpath)
        subprocess.check_call(f"{script.as_posix()} activate  {EMSDK_VERSION}", shell=True, cwd=sdkpath)
        lines = emconfig.read_text(encoding="utf-8").splitlines()
        newlines = [line if not line.split("=")[0].strip() == "NODE_JS" else f"NODE_JS = '{GetNodeJS().as_posix()}'" for line in lines]
        emconfig.write_text("\n".join(newlines), encoding="utf-8")
    os.environ["EM_CONFIG"] = emconfig.as_posix()
    _globals = {}
    _locals = {}
    exec(emconfig.read_text(encoding="utf-8"), _globals, _locals)  # pylint: disable=exec-used
    return EmscriptenInfo(
        sdkpath,
        {
            "EMSDK": sdkpath.as_posix(),
            "EMSDK_NODE": _locals["NODE_JS"],
        },
        [  # pathlib.Path(_locals["NODE_JS"]).parent,
            sdkpath,
            _locals["LLVM_ROOT"],
            _locals["BINARYEN_ROOT"],
            _locals["EMSCRIPTEN_ROOT"],
        ],
    )


def _download_or_get_Binary(binname: str, bindir: pathlib.Path, downloadFn: Callable[[pathlib.Path], None]) -> pathlib.Path:
    bindir.mkdir(exist_ok=True)
    exe = SearchExecutable(bindir, binname)
    if exe.is_file():
        AddToPath([exe.parent])
        return exe
    downloadFn(bindir)
    exe = SearchExecutable(bindir, binname)
    if exe.is_file():
        AddToPath([exe.parent])
        return exe
    raise ExternalToolsDownloadError(f"Cannot find or download {binname} in {bindir}")


def DownloadSdkManager(path: pathlib.Path):
    sdkpath = path / "sdk"
    sdkpath.mkdir(exist_ok=True)
    urls = HTMLUrlExtractor("https://developer.android.com/studio").urls
    ossuffix = {"linux": "linux", "win32": "win"}[sys.platform]
    pattern = f"https://dl.google.com/android/repository/commandlinetools-{ossuffix}.*.zip"
    url = [u for u in urls if re.match(pattern, u)][0]
    downloadtofile = path / "downloads" / "commandlinetools.zip"
    if not downloadtofile.exists():
        print(f"Download {url} to {downloadtofile}")
        urllib.request.urlretrieve(url, downloadtofile)
    shutil.unpack_archive(downloadtofile, sdkpath)
    AcceptSDKLicenses(path)


def DownloadAndroidStudio(path: pathlib.Path):
    ossuffix = {"linux": "linux", "win32": "win"}[sys.platform]
    ext = {"linux": "tar.gz", "win32": "zip"}[sys.platform]
    urls = HTMLUrlExtractor("https://developer.android.com/studio").urls
    ossuffix = {"linux": "linux", "win32": "windows"}[sys.platform]
    pattern = f"https://redirector.gvt1.com/edgedl/android/studio/.*/android-studio-.*-{ossuffix}.{ext}"
    url = [u for u in urls if re.match(pattern, u)][0]
    downloadtofile = path / "downloads" / f"studio.{ext}"
    downloadtofile.parent.mkdir(exist_ok=True)
    if not downloadtofile.exists():
        print(f"Download {url} to {downloadtofile}")
        urllib.request.urlretrieve(url, downloadtofile)
    shutil.unpack_archive(downloadtofile, path)


def AcceptSDKLicenses(path: pathlib.Path):
    sdkpath = path / "sdk"
    cmd = [
        str(_download_or_get_Binary("sdkmanager", path, DownloadSdkManager)),
        f"--sdk_root={sdkpath}",
        "--licenses",
    ]
    sys.stderr.write(" ".join(cmd) + "\n")
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    while proc.poll() is None:
        time.sleep(1)
        proc.communicate(input=b"y\ny\ny\ny\ny\ny\ny\ny\ny\ny\ny\ny\ny\ny\ny\ny\ny\ny\n")


def GetAndroidSdkManager(path: pathlib.Path) -> pathlib.Path:
    return _download_or_get_Binary("sdkmanager", path, DownloadSdkManager)


def DownloadAndroidStudioAt(path: pathlib.Path) -> pathlib.Path:
    return _download_or_get_Binary("studio", path, DownloadAndroidStudio)


def DownloadJava(path: pathlib.Path):
    return DownloadAndroidStudio(path)  # Just use java from android studio


def AndroidGetJavaAt(path: pathlib.Path) -> pathlib.Path:
    if "JAVA_HOME" in os.environ:
        os.environ.pop("JAVA_HOME")
    return _download_or_get_Binary("java", path, DownloadJava)


def AndroidGetJarSignerAt(path: pathlib.Path) -> pathlib.Path:
    return _download_or_get_Binary("jarsigner", path, DownloadJava)


def DownloadAndroidTo(path: pathlib.Path) -> dict[str, str | pathlib.Path]:
    java = AndroidGetJavaAt(path)
    sdkmanager = GetAndroidSdkManager(path)
    sdkpath = path / "sdk"
    runenv = os.environ.copy()
    runenv["PATH"] = os.pathsep.join([str(java.parent), str(sdkmanager.parent), runenv["PATH"]])
    runenv["ANDROID_SDK_HOME"] = (path / "tmp").as_posix()
    runenv["ANDROID_USER_HOME"] = (path / "tmp").as_posix()

    dirs = {""}
    for d in os.scandir(sdkpath):
        dirs.add(d.name)
    packages = [
        # "ndk-bundle",
        f"ndk;{ANDROID_NDK_VERSION}",
        "build-tools;34.0.0",
        "platform-tools",
        "platforms;android-34",
    ]

    def IsNeeded():
        for p in packages:
            if p.split(";", maxsplit=1)[0] not in dirs:
                return True
        return False

    if IsNeeded():
        cmd = [str(sdkmanager), f"--sdk_root={sdkpath}"] + packages
        sys.stderr.write(" ".join(cmd) + "\n")
        subprocess.check_call(cmd, env=runenv)
        AcceptSDKLicenses(path)
    return {
        "ndk": (sorted(list((sdkpath / "ndk").glob("*")))[-1]).absolute(),
        "ndk_version": ANDROID_NDK_VERSION,
        "sdk_version": "34",
        "java_home": java.parent.parent,
        "sdk_root": sdkpath,
    }


binarycache: Dict[str, pathlib.Path] = {}


def GetBinary(
    packname: str,
    urldir: Optional[str] = None,
    binname: Optional[str] = None,
    binpath: Optional[str] = None,
) -> pathlib.Path:
    if packname in binarycache:
        return binarycache[packname]
    rslt = binarycache[packname] = _GetBinary(packname, urldir, binname, binpath)
    return rslt


def _GetBinary(
    packname: str,
    _urldir: Optional[str] = None,
    binname: Optional[str] = None,
    binpath: Optional[str] = None,
    which=True,
) -> pathlib.Path:
    binname = binname or packname
    exe = pathlib.Path(shutil.which(binname) or "") if which else pathlib.Path()
    if exe.is_file():
        if exe.name != "system32":
            return pathlib.Path(exe)
        else:
            return pathlib.Path(exe)
    bindir = (binpath and pathlib.Path(binpath)) or GetBinPath() / packname
    bindir.mkdir(exist_ok=True)
    localexe = SearchExecutable(bindir, binname)
    if localexe.is_file():
        return localexe

    urlinfo: Any = URLS["_".join([packname, platform.system(), platform.machine().lower()])]

    archiveext = None
    if not isinstance(urlinfo, str):
        archiveext = archiveext or urlinfo.get("archiveext", None)
        if "url" in urlinfo:
            url = urlinfo["url"]
        elif "downloadpage" in urlinfo:
            downloadpage = urlinfo["downloadpage"]
            urls = HTMLUrlExtractor(downloadpage).urls
            url = [u for u in urls if re.match(urlinfo["urlpattern"], u)][0]
        else:
            raise ExternalToolsDownloadError("Invalid URL Declaration")
    else:
        url = urlinfo

    # archiveext = archiveext or os.path.splitext(urllib.parse.urlparse(url).path)[1]
    if not archiveext:
        if str(url).endswith(".zip"):
            archiveext = ".zip"
        elif str(url).endswith(".tar.gz"):
            archiveext = ".tar.gz"
        elif str(url).endswith(".tar.xz"):
            archiveext = ".tar.xz"
        else:
            raise ExternalToolsDownloadError(f"Unrecognized Archive format:{archiveext} in url{url}")
    downloadtofile = bindir.parent / f"tmp_{packname}{(archiveext or '')}"
    if (not bindir.exists()) or (not SearchExecutable(bindir, binname).is_file()):
        if not downloadtofile.is_file():
            urllib.request.urlretrieve(url, downloadtofile)
        if archiveext != "bin":
            shutil.unpack_archive(downloadtofile, bindir)
        else:
            binext = ".exe" if sys.platform == "win32" else ""
            shutil.copyfile(downloadtofile, bindir / (packname + binext))
        downloadtofile.unlink(missing_ok=True)
        subdir = list(os.scandir(bindir))
        while len(subdir) == 1 and os.path.isdir(subdir[0].path):
            MoveUp(pathlib.Path(subdir[0].path))
            subdir = list(os.scandir(bindir))

    if not isinstance(urlinfo, str) and "postdownloadrun" in urlinfo:
        subprocess.check_call((bindir / urlinfo["postdownloadrun"]).as_posix())

    return SearchExecutable(bindir, binname)


def GetNotepadPlusPlus():
    return GetBinary("notepad", URL_NOTEPAD) / "notepad++.exe"


def GetVSWhere():
    binpath = GetBinPath() / "vswhere.exe"
    if binpath.exists():
        return str(binpath)
    urllib.request.urlretrieve(URL_VSWHERE, str(binpath))
    return binpath


vsvars: Optional[Dict[str, str]] = None


def GetVSVars() -> dict[str, str]:
    global vsvars
    if vsvars is not None:
        return vsvars
    if sys.platform != "win32":
        return {}
    vswhere = pathlib.Path("C:/Program Files (x86)/Microsoft Visual Studio/Installer/vswhere.exe")
    if not vswhere.exists():
        return {}
    vspath = subprocess.check_output(
        [
            vswhere.as_posix(),
            "-version",
            "16.0",
            "-property",
            "installationpath",
            "-prerelease",
            "-all",
            "-latest",
            "-property",
            "installationpath",
        ],
        text=True,
    ).splitlines()[-1]
    # script = pathlib.Path(__file__).parent / "run_in_devenv.ps1"
    command = [
        "Import-Module",
        f'"{vspath}/Common7/Tools/Microsoft.VisualStudio.DevShell.dll"',
        ";",
        "Enter-VsDevShell",
        "-VsInstallPath",
        f'"{vspath}"',
        "-SkipAutomaticLocation",
        "-DevCmdArguments",
        "'-host_arch=amd64 -arch=x64 -no_logo'",
        ";",
        "gci env:/ | %{$_.Name+'='+$_.Value}",
    ]
    # command = ["powershell", script.as_posix(), "x64", ";", "gci env:/ | %{$_.Name+'='+$_.Value}"]
    rslt = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        shell=True,
        executable=shutil.which("powershell"),
    )
    if rslt.returncode != 0:
        return {}
    commandout = rslt.stdout.splitlines()[4:]
    localvars = dict(line.strip().split("=") for line in commandout)
    captureset = {"PATH", "INCLUDE", "LIB", "LIBPATH"}
    vsvars = {k.upper(): v for k, v in localvars.items() if k.upper() in captureset}
    vsvars["PATH"] += f";{vspath}/VC/Tools/Llvm/x64/bin"
    return vsvars


def DetectVSPath(name: str, excpt: bool = False) -> pathlib.Path | None:
    command = ["powershell", f"(Get-Command {name}).Path"]
    envvars = os.environ.copy() | GetVSVars()
    output = subprocess.check_output(command, env=envvars)
    p = pathlib.Path(output.splitlines()[-1].decode()).absolute()
    if not p.is_file():
        if excpt:
            raise ExternalToolsDownloadError(f"Cannot find {name} : {p} \nenv = {envvars} \n output = {output}")
        return None
    return p


def GetCMAKE() -> pathlib.Path:
    if sys.platform == "win32":
        return DetectVSPath("cmake") or GetBinary("cmake")
    return GetBinary("cmake")


def GetClangFormat() -> pathlib.Path:
    if sys.platform == "win32":
        return DetectVSPath("clang-format") or GetBinary("clang-format")
    return GetBinary("clang-format")


def GetMSVCCompiler():
    return DetectVSPath("cl", excpt=True)


def GetNinja():
    if sys.platform == "win32":
        return DetectVSPath("ninja") or GetBinary("ninja")
    return GetBinary("ninja")


def GetRSVGConvert() -> pathlib.Path:
    return GetBinary("rsvg-convert")


def GetRESVG() -> pathlib.Path:
    return GetBinary("resvg")


def GetCTEST() -> pathlib.Path:
    cmake = GetCMAKE().parent.as_posix()
    ctest = shutil.which("ctest", path=cmake)
    if not ctest:
        raise ExternalToolsDownloadError(f"Cannot find ctest in {cmake}")
    return pathlib.Path(ctest)


def GetGit() -> pathlib.Path:
    git = shutil.which("git")
    if git is None:
        raise ExternalToolsDownloadError("Cannot find Git")
    return pathlib.Path(git)


def GetReSVG() -> pathlib.Path:
    return GetBinary("resvg")


def GetImageMagickConvert() -> pathlib.Path:
    if sys.platform == "win32":
        return GetBinary("magick")
    else:
        return GetBinary("magick")


def GetWinFlexBison() -> pathlib.Path:
    return GetBinary("flexbison", binname="win_flex").parent


def GetJava() -> pathlib.Path:
    return pathlib.Path(AndroidGetJavaAt(GetBinPath() / "android"))


def GetJavaHome() -> pathlib.Path:
    return pathlib.Path(DownloadAndroidTo(GetBinPath() / "android")["java_home"])


def GetJarSigner() -> pathlib.Path:
    return AndroidGetJarSignerAt(GetBinPath() / "android")


def GetGradle() -> pathlib.Path:
    return GetBinary("gradle")


def GetRclone() -> pathlib.Path:
    return GetBinary("rclone")


def GetNodeJS():
    return GetBinary("node")


def GetTypesense() -> pathlib.Path:
    return GetBinary("typesense")


def GetNPM():
    if sys.platform == "win32":
        npm = pathlib.Path(shutil.which("npm.cmd", path=GetNodeJS().parent))
    else:
        npm = pathlib.Path(shutil.which("npm", path=GetNodeJS().parent))
    AddToPath([npm.parent])
    return npm


def AddToPath(paths: list[pathlib.Path], environ=None):
    environ = environ or os.environ
    alreadypaths = set([pathlib.Path(onepath).absolute() for onepath in environ["PATH"].split(os.pathsep)])
    appendpaths = list([onepath.as_posix() for onepath in paths if onepath.absolute() not in alreadypaths])
    appendpathsstr = os.pathsep.join(appendpaths)
    if len(appendpathsstr) > 0:
        newpath = os.pathsep.join([appendpathsstr, environ["PATH"]])
        environ["PATH"] = newpath
        sys.stderr.write(f"PATH += {appendpathsstr}\n")
        sys.stderr.write(f"PATH = {newpath}\n")
    return environ


def GetPatch():
    return GetBinary("patch")


def GetAndroidSdkRoot() -> pathlib.Path:
    return pathlib.Path(DownloadAndroidTo(GetBinPath() / "android")["sdk_root"])


def GetAndroidNDKRoot() -> pathlib.Path:
    return pathlib.Path(DownloadAndroidTo(GetBinPath() / "android")["ndk"])


def GetAndroidStudio():
    return DownloadAndroidStudioAt(GetBinPath() / "android")


def GetAndroidTools() -> dict[str, str | pathlib.Path]:
    return DownloadAndroidTo(GetBinPath() / "android")


def GetEmscripten():
    return DownloadEmscriptenInfoTo(GetBinPath() / "emsdk")


def GetEmscriptenVars():
    return GetEmscripten().envvars


def GetEmscriptenPaths():
    return GetEmscripten().paths


def AcquireTool(name: str) -> pathlib.Path:
    if name == "ImageMagick":
        return GetImageMagickConvert()
    elif name == "flexbison":
        return GetWinFlexBison()
    else:
        return GetBinary(name)
