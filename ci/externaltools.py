#!/usr/bin/python3
import contextlib
import html.parser
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from os import _Environ
from pathlib import Path
from typing import Any, Callable, Dict, Optional

# EMSDK_VERSION = "3.1.14"  #This is what qt likes
EMSDK_VERSION = "latest"
ANDROID_NDK_VERSION = "26.3.11579264"
NODE_LATEST = "latest"  # latest-v20.x
DefaultArch = {"amd64": "x64", "x86_64": "x64", "aarch64": "arm64"}.get(platform.machine().lower(), platform.machine().lower())

URLS = {}

URLS["cmake_Windows_amd64"] = {
    "downloadpage": "https://cmake.org/download/",
    "urlpattern": "https://github.com/Kitware/CMake/releases/download/v.*/cmake-.*-windows-x86_64.zip",
}

URLS["cmake_Windows_arm64"] = {
    "downloadpage": "https://cmake.org/download/",
    "urlpattern": "https://github.com/Kitware/CMake/releases/download/v.*/cmake-.*-windows-arm64.zip",
}

URLS["patch_Windows_amd64"] = ""
URLS["gradle_Linux_x64"] = URLS["gradle_Windows_amd64"] = "https://services.gradle.org/distributions/gradle-8.0-bin.zip"
URLS["flexbison_Windows_amd64"] = "https://github.com/lexxmark/winflexbison/releases/download/v2.5.25/win_flex_bison-2.5.25.zip"
URLS["ninja_Windows_amd64"] = "https://github.com/ninja-build/ninja/releases/latest/download/ninja-win.zip"
URLS["ninja_Windows_arm64"] = "https://github.com/ninja-build/ninja/releases/latest/download/ninja-winarm64.zip"
URLS["ninja_Linux_x64"] = "https://github.com/ninja-build/ninja/releases/latest/download/ninja-linux.zip"
URLS["rclone_Windows_amd64"] = "https://downloads.rclone.org/v1.54.1/rclone-v1.54.1-windows-amd64.zip"
URLS["rclone_Linux_x64"] = "https://downloads.rclone.org/v1.54.1/rclone-v1.54.1-linux-amd64.zip"

URLS["node_Windows_arm64"] = {
    "downloadpage": f"https://nodejs.org/dist/{NODE_LATEST}/",
    "urlpattern": f"https://nodejs.org/dist/{NODE_LATEST}/node-.*-win-arm64.zip",
}
URLS["node_Windows_amd64"] = {
    "downloadpage": f"https://nodejs.org/dist/{NODE_LATEST}/",
    "urlpattern": f"https://nodejs.org/dist/{NODE_LATEST}/node-.*-win-x64.zip",
}
URLS["node_Linux_x64"] = {
    "downloadpage": f"https://nodejs.org/dist/{NODE_LATEST}/",
    "urlpattern": f"https://nodejs.org/dist/{NODE_LATEST}/node-.*-linux-x64.tar.xz",
}
URLS["node_Linux_arm64"] = {
    "downloadpage": f"https://nodejs.org/dist/{NODE_LATEST}/",
    "urlpattern": f"https://nodejs.org/dist/{NODE_LATEST}/node-.*-linux-arm64.tar.xz",
}
URLS["magick_Windows_amd64"] = {
    "downloadpage": "https://imagemagick.org/download/binaries/",
    "urlpattern": "https://imagemagick.org/download/binaries/ImageMagick-7.*-portable-Q16-x64.zip",
}

URLS["magick_Linux_x64"] = {
    "downloadpage": "https://imagemagick.org/script/download.php#linux",
    "urlpattern": "https://download.imagemagick.org/ImageMagick/download/binaries/magick",
    "archiveext": "bin",
}
URLS["rsvg-convert_Linux_x64"] = {
    "url": "https://github.com/ankurvdev/binaries/raw/main/rsvg-convert",
    "archiveext": "bin",
}
URLS["typesense-server_Linux_x64"] = "https://dl.typesense.org/releases/0.25.1/typesense-server-0.25.1-linux-amd64.tar.gz"
URLS["typesense-server_Linux_arm64"] = "https://dl.typesense.org/releases/0.25.1/typesense-server-0.25.1-linux-arm64.tar.gz"
URLS["rsvg-convert_Windows_amd64"] = "https://github.com/ankurvdev/binaries/raw/main/rsvg-convert.exe"
URLS["resvg_Windows_arm64"] = "https://github.com/ankurvdev/resvg/releases/latest/download/resvg-windows-x86_64.zip"
URLS["resvg_Windows_amd64"] = "https://github.com/ankurvdev/resvg/releases/latest/download/resvg-windows-arm64.zip"
URLS["resvg_Linux_x64"] = "https://github.com/ankurvdev/resvg/releases/latest/download/resvg-linux-x86_64.zip"
URLS["resvg_Linux_arm64"] = "https://github.com/ankurvdev/resvg/releases/latest/download/resvg-linux-aarch64.zip"
URLS["deno_Windows_x64"] = "https://github.com/denoland/deno/releases/latest/download/deno-x86_64-pc-windows-msvc.zip"
URLS["deno_Linux_x64"] = "https://github.com/denoland/deno/releases/latest/download//deno-x86_64-unknown-linux-gnu.zip"
URLS["deno_Linux_arm64"] = "https://github.com/LukeChannings/deno-arm64/releases/latest/download/deno-linux-arm64.zip"
URL_NOTEPAD = "http://download.notepad-plus-plus.org/repository/7.x/7.8.1/npp.7.8.1.bin.x64.zip"
URL_VSWHERE = "https://github.com/Microsoft/vswhere/releases/download/2.6.7/vswhere.exe"


class ExternalToolsDownloadError(Exception):
    pass


class HTMLUrlExtractor(html.parser.HTMLParser):
    def __init__(self, url: str):
        headers = {"User-Agent": "Mozilla/5.0"}
        req = urllib.request.Request(url, data=None, headers=headers)
        try:
            resp = urllib.request.urlopen(req)
        except urllib.error.HTTPError as e:
            if "Location" not in e.headers:
                raise  # not a status code that can be handled here
            redirected_url = urllib.parse.urljoin(url, e.headers["Location"])
            req = urllib.request.Request(redirected_url, data=None, headers=headers)
            resp = urllib.request.urlopen(req)
        text = resp.read().decode("utf-8")
        self.baseurl = url
        self.urls: Dict[str, str] = {}
        self.href: Optional[str] = None
        self.text: Optional[str] = None
        super().__init__()
        self.feed(text)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self.text = ""
            self.href = next(
                (urllib.parse.urljoin(self.baseurl, attr[1]) for attr in attrs if attr[0] == "href"),
                None,
            )

    def handle_endtag(self, tag: str) -> None:
        if self.href is not None:
            # print(self.href, self.text)
            self.urls[self.href or ""] = self.text or ""
        self.href = None
        self.text = None

    def handle_data(self, data: str) -> None:
        if self.href is not None:
            self.text = data


def search_filename(sdir: Path, name: str, recursive: bool = True) -> Path:
    for p in sdir.rglob(name) if recursive else sdir.glob(name):
        if p.is_file():
            return p
    return Path()


def search_executable(bindir: Path, binname: str, recursive: bool = True) -> Path:
    if recursive:
        localexe = search_executable(bindir.parent, binname, recursive=False)
        if localexe.is_file():
            return localexe
    if sys.platform == "win32":
        path = search_filename(bindir, binname + ".exe", recursive=recursive)
        path = search_filename(bindir, binname + ".bat", recursive=recursive) if not path.is_file() else path
        path = search_filename(bindir, binname + ".cmd", recursive=recursive) if not path.is_file() else path
    elif sys.platform == "linux":
        path = search_filename(bindir, binname, recursive=recursive)
        path = search_filename(bindir, binname + ".sh", recursive=recursive) if not path.is_file() else path
        if path.is_file():
            with contextlib.suppress(PermissionError):
                path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path


def move_up(path: Path) -> None:
    tmp_path = path.rename(path.parent / f"tmp_{path.name}")
    for p in tmp_path.iterdir():
        shutil.move(p, path.parent)
    tmp_path.rmdir()


def get_bin_path() -> Path:
    try:
        import configenv  # noqa: ignore

        return Path(configenv.ConfigEnv(None).GetConfigPath("DEVEL_BINPATH", make=True))
    except ImportError:
        return Path().absolute()


class EmscriptenInfo:
    def __init__(
        self,
        sdkpath: Path,
        envvars: dict[str, str],
        paths: list[str | Path],
    ):
        self.sdkpath = sdkpath
        self.envvars = envvars
        self.paths = {Path(pathlike).absolute() for pathlike in paths}
        self.cmake_toolchain_file = sdkpath / "upstream" / "emscripten" / "cmake" / "Modules" / "Platform" / "Emscripten.cmake"


def download_emscripten_info_to(path: Path):
    path.mkdir(exist_ok=True, parents=True)
    sdkpath = path
    emconfig = sdkpath / ".emscripten"
    if not emconfig.exists():
        script = sdkpath / "emsdk.bat" if sys.platform == "win32" else sdkpath / "emsdk"
        if not script.exists():
            subprocess.check_call(
                [get_git().as_posix(), "clone", "https://github.com/emscripten-core/emsdk.git", sdkpath.as_posix()],
            )
        subprocess.check_call(f"{script.as_posix()} install {EMSDK_VERSION}", shell=True, cwd=sdkpath)
        subprocess.check_call(f"{script.as_posix()} activate  {EMSDK_VERSION}", shell=True, cwd=sdkpath)
        lines = emconfig.read_text(encoding="utf-8").splitlines()
        newlines = [line if line.split("=")[0].strip() != "NODE_JS" else f"NODE_JS = '{get_nodejs().as_posix()}'" for line in lines]
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
        [  # Path(_locals["NODE_JS"]).parent,
            sdkpath,
            _locals["LLVM_ROOT"],
            _locals["BINARYEN_ROOT"],
            _locals["EMSCRIPTEN_ROOT"],
        ],
    )


def _download_or_get_binary(binname: str, bindir: Path, downloadFn: Callable[[Path], None]) -> Path:
    bindir.mkdir(exist_ok=True)
    exe = search_executable(bindir, binname)
    if exe.is_file():
        add_to_path([exe.parent])
        return exe
    downloadFn(bindir)
    exe = search_executable(bindir, binname)
    if exe.is_file():
        add_to_path([exe.parent])
        return exe
    raise ExternalToolsDownloadError(f"Cannot find or download {binname} in {bindir}")


def download_android_sdk_manager(path: Path) -> None:
    sdkpath = path / "sdk"
    sdkpath.mkdir(exist_ok=True)
    urls = HTMLUrlExtractor("https://developer.android.com/studio").urls
    ossuffix = {"linux": "linux", "win32": "win"}[sys.platform]
    pattern = f"https://dl.google.com/android/repository/commandlinetools-{ossuffix}.*.zip"
    url = next(u for u in urls if re.match(pattern, u))
    downloadtofile = path / "downloads" / "commandlinetools.zip"
    if not downloadtofile.exists():
        urllib.request.urlretrieve(url, downloadtofile)
    shutil.unpack_archive(downloadtofile, sdkpath)
    accept_sdk_licenses(path)


def download_android_studio(path: Path) -> None:
    ossuffix = {"linux": "linux", "win32": "win"}[sys.platform]
    ext = {"linux": "tar.gz", "win32": "zip"}[sys.platform]
    urls = HTMLUrlExtractor("https://developer.android.com/studio").urls
    ossuffix = {"linux": "linux", "win32": "windows"}[sys.platform]
    pattern = f"https://redirector.gvt1.com/edgedl/android/studio/.*/android-studio-.*-{ossuffix}.{ext}"
    url = next(u for u in urls if re.match(pattern, u))
    downloadtofile = path / "downloads" / f"studio.{ext}"
    downloadtofile.parent.mkdir(exist_ok=True)
    if not downloadtofile.exists():
        urllib.request.urlretrieve(url, downloadtofile)
    shutil.unpack_archive(downloadtofile, path)


def accept_sdk_licenses(path: Path) -> None:
    sdkpath = path / "sdk"
    cmd = [
        str(_download_or_get_binary("sdkmanager", path, download_android_sdk_manager)),
        f"--sdk_root={sdkpath}",
        "--licenses",
    ]
    sys.stderr.write(" ".join(cmd) + "\n")
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    while proc.poll() is None:
        time.sleep(1)
        proc.communicate(input=b"y\ny\ny\ny\ny\ny\ny\ny\ny\ny\ny\ny\ny\ny\ny\ny\ny\ny\n")


def get_android_sdk_manager(path: Path) -> Path:
    return _download_or_get_binary("sdkmanager", path, download_android_sdk_manager)


def download_android_studio_at(path: Path) -> Path:
    return _download_or_get_binary("studio", path, download_android_studio)


def download_java(path: Path):
    return download_android_studio(path)  # Just use java from android studio


def android_get_java_at(path: Path) -> Path:
    if "JAVA_HOME" in os.environ:
        os.environ.pop("JAVA_HOME")
    return _download_or_get_binary("java", path, download_java)


def android_get_jar_signer_at(path: Path) -> Path:
    return _download_or_get_binary("jarsigner", path, download_java)


def download_android_to(path: Path) -> dict[str, str | Path]:
    java = android_get_java_at(path)
    sdkmanager = get_android_sdk_manager(path)
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

    def is_needed():
        return any(p.split(";", maxsplit=1)[0] not in dirs for p in packages)

    if is_needed():
        cmd = [str(sdkmanager), f"--sdk_root={sdkpath}", *packages]
        sys.stderr.write(" ".join(cmd) + "\n")
        subprocess.check_call(cmd, env=runenv)
        accept_sdk_licenses(path)
    return {
        "ndk": (sorted((sdkpath / "ndk").glob("*"))[-1]).absolute(),
        "ndk_version": ANDROID_NDK_VERSION,
        "sdk_version": "34",
        "java_home": java.parent.parent,
        "sdk_root": sdkpath,
    }


binarycache: Dict[str, Path] = {}


def get_binary(
    packname: str,
    urldir: Optional[str] = None,
    binname: Optional[str] = None,
    binpath: Path | str | None = None,
) -> Path:
    if packname in binarycache:
        return binarycache[packname]
    rslt = binarycache[packname] = _get_binary(packname, urldir, binname, binpath)
    return rslt


def _get_binary(  # noqa: PLR0912
    packname: str,
    _urldir: Optional[str] = None,
    binname: Optional[str] = None,
    binpath: Path | str | None = None,
    which: bool = True,
) -> Path:
    binname = binname or packname
    exe = Path(shutil.which(binname) or "") if which else Path()
    if exe.is_file():
        if exe.name != "system32":
            return Path(exe)
        else:
            return Path(exe)

    bindir = (binpath and Path(binpath)) or get_bin_path()
    localexe = search_executable(bindir, binname, recursive=False)
    if localexe.is_file():
        add_to_path([localexe.parent])
        return localexe.absolute()
    bindir = (binpath and Path(binpath)) or get_bin_path() / packname
    bindir.mkdir(exist_ok=True)
    localexe = search_executable(bindir, binname)
    if localexe.is_file():
        add_to_path([localexe.parent])
        return localexe.absolute()

    urlinfo: Any = URLS[f"{packname}_{platform.system()}_{DefaultArch}"]

    archiveext = None
    if not isinstance(urlinfo, str):
        archiveext = archiveext or urlinfo.get("archiveext", None)
        if "url" in urlinfo:
            url = urlinfo["url"]
        elif "downloadpage" in urlinfo:
            downloadpage = urlinfo["downloadpage"]
            urls = HTMLUrlExtractor(downloadpage).urls
            url = next(u for u in urls if re.match(urlinfo["urlpattern"], u))
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
    if (not bindir.exists()) or (not search_executable(bindir, binname).is_file()):
        if not downloadtofile.is_file():
            urllib.request.urlretrieve(url, downloadtofile)
        if archiveext != "bin":
            shutil.unpack_archive(downloadtofile, bindir)
        else:
            binext = ".exe" if sys.platform == "win32" else ""
            shutil.copyfile(downloadtofile, bindir / (packname + binext))
        downloadtofile.unlink(missing_ok=True)
        subdir = list(os.scandir(bindir))
        while len(subdir) <= 2 and Path(subdir[0].path).is_dir():  # noqa: PLR2004
            move_up(Path(subdir[0].path))
            subdir = list(os.scandir(bindir))
        if len(list(Path(bindir).glob("*"))) <= 2:  # noqa: PLR2004
            move_up(bindir)

    if not isinstance(urlinfo, str) and "postdownloadrun" in urlinfo:
        subprocess.check_call((bindir / urlinfo["postdownloadrun"]).as_posix())

    localexe = search_executable(bindir, binname)
    if localexe.is_file():
        add_to_path([localexe.parent])
        return localexe.absolute()
    raise ExternalToolsDownloadError(f"Cannot find or download {packname} in {bindir}")


def get_notepad_plus_plus():
    return get_binary("notepad", URL_NOTEPAD) / "notepad++.exe"


def get_vswhere():
    binpath = get_bin_path() / "vswhere.exe"
    if binpath.exists():
        return str(binpath)
    urllib.request.urlretrieve(URL_VSWHERE, str(binpath))
    return binpath


vsvars: Optional[Dict[str, str]] = None


def get_vsvars() -> dict[str, str]:
    global vsvars  # noqa: PLW0603
    envvarsf = get_bin_path() / "msvc/envvars.json"
    if envvarsf.exists():
        envvars = os.environ.copy()
        for k, v in json.loads(envvarsf.read_text()).items():
            if isinstance(v, list):
                add_to_env_path_list(k, [Path(fpath) for fpath in v], envvars)
            else:
                envvars[k] = v
        return envvars
    if vsvars is not None:
        return vsvars
    if sys.platform != "win32":
        return {}
    vswhere = Path("C:/Program Files (x86)/Microsoft Visual Studio/Installer/vswhere.exe")
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
    # script = Path(__file__).parent / "run_in_devenv.ps1"
    command = [
        "Import-Module",
        f'"{vspath}/Common7/Tools/Microsoft.VisualStudio.DevShell.dll"',
        ";",
        "Enter-VsDevShell",
        "-VsInstallPath",
        f'"{vspath}"',
        "-SkipAutomaticLocation",
        "-DevCmdArguments",
        f"'-arch={DefaultArch} -no_logo'",
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


def detect_vspath(name: str, excpt: bool = False) -> Path | None:
    bin_exe = shutil.which(name)
    if bin_exe and Path(bin_exe).is_file():
        return Path(bin_exe)
    command = ["powershell", f"(Get-Command {name}).Path"]
    envvars = os.environ.copy() | get_vsvars()
    output = subprocess.check_output(command, env=envvars)
    p = Path(output.splitlines()[-1].decode()).absolute()
    if not p.is_file():
        if excpt:
            raise ExternalToolsDownloadError(f"Cannot find {name} : {p} \nenv = {envvars} \n output = {output}")
        return None
    return p


def get_cmake() -> Path:
    if sys.platform == "win32":
        return detect_vspath("cmake") or get_binary("cmake")
    return get_binary("cmake")


def get_clang_format() -> Path:
    if sys.platform == "win32":
        return detect_vspath("clang-format") or get_binary("clang-format")
    return get_binary("clang-format")


def get_msvc_compiler() -> Path | None:
    envvars = get_bin_path() / "msvc/envvars.json"
    if envvars.exists():
        for k, v in json.loads(envvars.read_text()).items():
            if isinstance(v, list):
                add_to_env_path_list(k, [Path(fpath) for fpath in v])
            else:
                os.environ[k] = v
    return detect_vspath("cl", excpt=True)


def get_ninja():
    if sys.platform == "win32":
        return detect_vspath("ninja") or get_binary("ninja")
    return get_binary("ninja")


def get_rsvg_convert() -> Path:
    return get_binary("rsvg-convert")


def get_resvg() -> Path:
    return get_binary("resvg")


def get_ctest() -> Path:
    cmake = get_cmake().parent.as_posix()
    ctest = shutil.which("ctest", path=cmake)
    if not ctest:
        raise ExternalToolsDownloadError(f"Cannot find ctest in {cmake}")
    return Path(ctest)


def get_git() -> Path:
    git = shutil.which("git")
    if git is None:
        raise ExternalToolsDownloadError("Cannot find Git")
    return Path(git)


def get_imagemagick_convert() -> Path:
    if sys.platform == "win32":
        return get_binary("magick")
    else:
        return get_binary("magick")


def get_win_flexbison() -> Path:
    return get_binary("flexbison", binname="win_flex").parent


def get_java() -> Path:
    return Path(android_get_java_at(get_bin_path() / "android"))


def get_java_home() -> Path:
    return Path(download_android_to(get_bin_path() / "android")["java_home"])


def get_jar_signer() -> Path:
    return android_get_jar_signer_at(get_bin_path() / "android")


def get_gradle() -> Path:
    return get_binary("gradle")


def get_rclone() -> Path:
    return get_binary("rclone")


def get_nodejs():
    return get_binary("node")


def get_deno():
    return get_binary("deno")


def get_typesense_server() -> Path:
    return get_binary("typesense-server")


def get_npm():
    if sys.platform == "win32":
        npm = Path(shutil.which("npm.cmd", path=get_nodejs().parent))
    else:
        npm = Path(shutil.which("npm", path=get_nodejs().parent))  # type: ignore
    add_to_path([npm.parent])
    return npm


def add_to_env_path_list(envvar: str, paths: list[Path], environ: dict[str, str] | _Environ[str] | None = None):
    environ = environ or os.environ
    alreadypaths = {Path(onepath or ".").absolute() for onepath in environ.get(envvar, "").split(os.pathsep)}
    appendpaths = [onepath.as_posix() for onepath in paths if onepath.absolute() not in alreadypaths]
    appendpathsstr = os.pathsep.join(appendpaths)
    if len(appendpathsstr) > 0:
        newpath = os.pathsep.join([appendpathsstr, environ.get(envvar, "")])
        environ[envvar] = newpath
        sys.stderr.write(f"{envvar} += {appendpathsstr}\n")
        sys.stderr.write(f"{envvar} = {newpath}\n")
    return environ


def add_to_path(paths: list[Path], environ: dict[str, str] | _Environ[str] | None = None):
    return add_to_env_path_list("PATH", paths, environ=environ)


def get_patch():
    return get_binary("patch")


def get_android_sdk_root() -> Path:
    return Path(download_android_to(get_bin_path() / "android")["sdk_root"])


def get_android_ndk_root() -> Path:
    return Path(download_android_to(get_bin_path() / "android")["ndk"])


def get_android_studio():
    return download_android_studio_at(get_bin_path() / "android")


def get_android_tools() -> dict[str, str | Path]:
    return download_android_to(get_bin_path() / "android")


def get_emscripten():
    return download_emscripten_info_to(get_bin_path() / "emsdk")


def get_emscripten_vars():
    return get_emscripten().envvars


def get_emscripten_paths():
    return get_emscripten().paths


def acquire_tool(name: str) -> Path:
    if name == "ImageMagick":
        return get_imagemagick_convert()
    elif name == "flexbison":
        return get_win_flexbison()
    else:
        return get_binary(name)
