#!/usr/bin/python3
# cppforge-sync
import argparse
import contextlib
import datetime
import hashlib
import html.parser
import io
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
import zipfile
from collections.abc import Generator
from os import _Environ
from pathlib import Path
from typing import Any, Callable, Optional

EMSDK_VERSION = "latest"
# EMSDK_VERSION = "3.1.67"  # Fmt fails to compile with 3.1.68+" https://github.com/emscripten-core/emsdk/issues/1480
# ANDROID_NDK_VERSION = "27.2.12479018" LTS
ANDROID_NDK_VERSION = "28.2.13676358"
ANDROID_SDK_VERSION = 36
NODE_LATEST = "latest"  # latest-v20.x
DefaultArch = {"amd64": "x64", "x86_64": "x64", "aarch64": "arm64"}.get(platform.machine().lower(), platform.machine().lower())

URLS = {}

URLS["cmake_Windows_x64"] = {
    "downloadpage": "https://cmake.org/download/",
    "urlpattern": "https://github.com/Kitware/CMake/releases/download/v.*/cmake-[0-9\\.]*-windows-x86_64.zip",
}

URLS["cmake_Windows_arm64"] = {
    "downloadpage": "https://cmake.org/download/",
    "urlpattern": "https://github.com/Kitware/CMake/releases/download/v.*/cmake-[0-9\\.]*-windows-arm64.zip",
}

URLS["patch_Windows_x64"] = ""
URLS["gradle_Linux_x64"] = URLS["gradle_Windows_x64"] = "https://services.gradle.org/distributions/gradle-8.14.2-bin.zip"
URLS["flexbison_Windows_x64"] = "https://github.com/lexxmark/winflexbison/releases/download/v2.5.25/win_flex_bison-2.5.25.zip"
URLS["ninja_Windows_x64"] = "https://github.com/ninja-build/ninja/releases/latest/download/ninja-win.zip"
URLS["ninja_Windows_arm64"] = "https://github.com/ninja-build/ninja/releases/latest/download/ninja-winarm64.zip"
URLS["ninja_Linux_x64"] = "https://github.com/ninja-build/ninja/releases/latest/download/ninja-linux.zip"
URLS["rclone_Windows_x64"] = "https://downloads.rclone.org/v1.54.1/rclone-v1.54.1-windows-amd64.zip"
URLS["rclone_Linux_x64"] = "https://downloads.rclone.org/v1.54.1/rclone-v1.54.1-linux-amd64.zip"

URLS["node_Windows_arm64"] = {
    "downloadpage": f"https://nodejs.org/dist/{NODE_LATEST}/",
    "urlpattern": f"https://nodejs.org/dist/{NODE_LATEST}/node-.*-win-arm64.zip",
}
URLS["node_Windows_x64"] = {
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
URLS["magick_Windows_x64"] = {
    "downloadpage": "https://imagemagick.org/download/binaries/",
    "urlpattern": "https://imagemagick.org/download/binaries/ImageMagick-7.*-portable-Q16-x64.zip",
}

URLS["magick_Linux_x64"] = {
    "downloadpage": "https://imagemagick.org/script/download.php#linux",
    "urlpattern": "https://download.imagemagick.org/ImageMagick/download/binaries/magick",
    "archiveext": "bin",
}
URLS["msys2_Windows_x64"] = "https://github.com/msys2/msys2-installer/releases/download/nightly-x86_64/msys2-base-x86_64-latest.tar.xz"
URLS["msys2_Windows_arm64"] = URLS["msys2_Windows_x64"]  # Sadly
URLS["rsvg-convert_Linux_x64"] = {
    "url": "https://github.com/ankurvdev/binaries/raw/main/rsvg-convert",
    "archiveext": "bin",
}
URLS["typesense-server_Linux_x64"] = "https://dl.typesense.org/releases/26.0/typesense-server-26.0-linux-amd64.tar.gz"
URLS["typesense-server_Linux_arm64"] = "https://dl.typesense.org/releases/26.0/typesense-server-26.0-linux-arm64.tar.gz"
URLS["rsvg-convert_Windows_x64"] = "https://github.com/ankurvdev/binaries/raw/main/rsvg-convert.exe"
URLS["resvg_Windows_x64"] = "https://github.com/ankurvdev/resvg/releases/latest/download/resvg-windows-x86_64.zip"
URLS["resvg_Windows_arm64"] = "https://github.com/ankurvdev/resvg/releases/latest/download/resvg-windows-arm64.zip"
URLS["resvg_Linux_x64"] = "https://github.com/ankurvdev/resvg/releases/latest/download/resvg-linux-x86_64.zip"
URLS["resvg_Linux_arm64"] = "https://github.com/ankurvdev/resvg/releases/latest/download/resvg-linux-aarch64.zip"
URLS["deno_Windows_x64"] = "https://github.com/denoland/deno/releases/latest/download/deno-x86_64-pc-windows-msvc.zip"
URLS["deno_Linux_x64"] = "https://github.com/denoland/deno/releases/latest/download//deno-x86_64-unknown-linux-gnu.zip"
URLS["deno_Linux_arm64"] = "https://github.com/LukeChannings/deno-arm64/releases/latest/download/deno-linux-arm64.zip"
URL_NOTEPAD = "http://download.notepad-plus-plus.org/repository/7.x/7.8.1/npp.7.8.1.bin.x64.zip"
URL_VSWHERE = "https://github.com/Microsoft/vswhere/releases/download/2.6.7/vswhere.exe"


class ExternalToolsDownloadError(Exception):
    pass


TOOL_PATH: set[Path] = set()
TOOL_PATHS: dict[str, Path] = {}


class CustomEncoder(json.JSONEncoder):
    def default(self, o: any) -> any:
        if isinstance(o, Path):
            if get_bin_path() in o.parents:
                o = o.relative_to(get_bin_path())
            return o.as_posix()
        # Let the base class default method raise the TypeError
        return super().default(o)


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
        self.urls: dict[str, str] = {}
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

    def handle_endtag(self, _tag: str) -> None:
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
    if not bindir.exists():
        return Path()
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


DEVEL_BINPATH: Path | None = None
VCPKG_ROOT: Path | None = None


def get_env_config_var(name: str, default_val: str | None = None) -> str | None:
    name = name.upper()
    if name in globals() and globals()[name] is not None:
        return globals()[name]
    if name in os.environ:
        return os.environ[name]
    try:
        import configenv  # noqa: ignore, pylint: disable=import-outside-toplevel  # noqa: PLC0415

        return configenv.ConfigEnv(None).GetConfigStr(name, default=default_val)
    except ImportError:
        return default_val


def get_path_var(name: str, default_path: Path | None = Path().absolute()) -> Path | None:  # noqa: B008
    val = get_env_config_var(name, default_path.as_posix())
    if val:
        return Path(os.path.expandvars(val)).expanduser()
    return default_path


def get_bin_path(default_path: Path | None = Path().absolute()) -> Path | None:  # noqa: B008
    return get_path_var("DEVEL_BINPATH", default_path)


def get_vcpkg_root(default_path: Path | None = Path().absolute() / "vcpkg") -> Path | None:  # noqa: B008
    return get_path_var("VCPKG_ROOT", default_path)


def get_vcpkg_port_tool(vcpkg_root: Path, packname: str, binname: str) -> Path | None:
    try:
        import vcpkg  # noqa: ignore, pylint: disable=import-outside-toplevel  # noqa: PLC0415

        vcpkgobj = vcpkg.Vcpkg(vcpkg_root)
        host_triplet = vcpkgobj.detect_host_triplet()
        vcpkgobj.download([f"{packname}:{host_triplet}"])
        installed_tool = vcpkg_root / "installed" / host_triplet / "tools" / packname
        if installed_tool.exists():
            return search_executable(installed_tool, binname)
    except ImportError:
        return None


def _download_or_get_binary(binname: str, bindir: Path, download_callback: Callable[[Path], None] | None = None) -> Path:
    bindir.mkdir(exist_ok=True, parents=True)
    exe = search_executable(bindir, binname)
    if exe.is_file():
        add_to_path([exe.parent])
        return exe
    if download_callback:
        download_callback(bindir)
        return _download_or_get_binary(binname, bindir, download_callback=None)
    raise ExternalToolsDownloadError(f"Cannot find or download {binname} in {bindir}")


def download_android_sdk_manager(sdk_root: Path) -> None:
    sdk_root.mkdir(exist_ok=True)
    urls = HTMLUrlExtractor("https://developer.android.com/studio").urls
    ossuffix = {"linux": "linux", "win32": "win"}[sys.platform]
    pattern = f"https://dl.google.com/android/repository/commandlinetools-{ossuffix}.*.zip"
    url = next(u for u in urls if re.match(pattern, u))
    downloadtofile = sdk_root.parent / "downloads" / "commandlinetools.zip"
    if not downloadtofile.exists():
        urllib.request.urlretrieve(url, downloadtofile)
    shutil.unpack_archive(downloadtofile, sdk_root)


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


binarycache: dict[str, Path] = {}


def get_binary(
    packname: str,
    binname: Optional[str] = None,
    search_paths: list[Path] | None = None,
    binpath: Path | str | None = None,
) -> Path:
    if packname in binarycache:
        return binarycache[packname]
    rslt = binarycache[packname] = _get_binary(packname, binname=binname, binpath=binpath, search_paths=search_paths).absolute()
    TOOL_PATHS[packname] = rslt
    TOOL_PATH.add(rslt.parent)
    add_to_path([rslt.parent])
    return rslt


def _get_binary(  # noqa: PLR0912, PLR0915, C901
    packname: str,
    binname: Optional[str] = None,
    search_paths: list[Path] | None = None,
    binpath: Path | str | None = None,
    which: bool = True,
) -> Path:
    binname = binname or packname
    for search_path in search_paths or []:
        exe = Path(shutil.which(binname, path=str(search_path)) or "") if which else Path()
        if exe.is_file():
            return exe
    exe = Path(shutil.which(binname) or "") if which else Path()
    if exe.is_file():
        if exe.name != "system32":
            return Path(exe).absolute()
        return Path(exe).absolute()
    bindir = (binpath and Path(binpath)) or get_bin_path()
    localexe = search_executable(bindir, binname, recursive=False)
    if localexe.is_file():
        return localexe
    bindir = (binpath and Path(binpath)) or get_bin_path() / packname
    localexe = search_executable(bindir, binname)
    if localexe.is_file():
        return localexe

    vcpkg_root = get_vcpkg_root()
    if vcpkg_root:
        toolsdir = vcpkg_root / "downloads" / "tools"
        portsdir = vcpkg_root / "ports"
        for searchdir in toolsdir.glob(f"{packname}*"):
            localexe = search_executable(searchdir, binname)
            if localexe.is_file():
                return localexe
        if (portsdir / packname).exists():
            return get_vcpkg_port_tool(vcpkg_root, packname, binname)

    bindir.mkdir(exist_ok=True, parents=True)
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
        elif str(url).endswith(".exe"):
            archiveext = "bin"
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
        return localexe
    raise ExternalToolsDownloadError(f"Cannot find or download {packname} in {bindir}")


def get_notepad_plus_plus() -> Path:
    return get_binary("notepad") / "notepad++.exe"


def get_vswhere() -> Path:
    binpath = get_bin_path() / "vswhere.exe"
    if binpath.exists():
        return str(binpath)
    urllib.request.urlretrieve(URL_VSWHERE, str(binpath))
    return binpath


def init_envvars_from_dict(
    toolchain: str,
    info: dict[str, str],
    envvarsbase: dict[str, str] | _Environ[str] | None = None,
) -> dict[str, str | Path | _Environ[str] | dict[str, Path]]:
    info["environ"] = append_envvars(envvarsbase or os.environ.copy(), info.get("env", {}))
    info["host_arch"] = DefaultArch
    info["toolchain"] = toolchain
    return info


def init_envvars_from_file(
    toolchain: str,
    fpath: Path,
    envvarsbase: dict[str, str] | _Environ[str] | None = None,
) -> dict[str, str | Path | _Environ[str] | dict[str, Path]]:
    envvars = envvarsbase or os.environ.copy()
    info = recursive_deserialize({}, json.loads(fpath.read_text()))
    return init_envvars_from_dict(toolchain, info, envvars)


def deserialize_from_str(v: str) -> Path | str:
    fpath = Path(v)
    fpath = fpath if fpath.is_absolute() else get_bin_path() / fpath
    if fpath.exists():
        return fpath
    return v


def recursive_deserialize(outinfo: dict[str, str] | _Environ[str], info: dict[str, str]) -> dict[str, Path | str]:
    for k, v in info.items():
        if isinstance(v, str):
            outinfo[k] = deserialize_from_str(v)
        elif isinstance(v, (Path, int)):
            outinfo[k] = v
        elif isinstance(v, list):
            outinfo[k] = [deserialize_from_str(onev) for onev in v]
        elif isinstance(v, dict):
            outinfo.setdefault(k, {})
            outinfo[k] = recursive_deserialize(outinfo[k], v)
        else:
            raise ExternalToolsDownloadError(f"Invalid value in {info} for {k} => {v}")
    return outinfo


def append_envvars(
    envvars: dict[str, str] | _Environ[str],
    appendenv: dict[str, str] | _Environ[str] | None,
) -> dict[str, str] | _Environ[str]:
    if not appendenv:
        return envvars
    for k, v in appendenv.items():
        if isinstance(v, list):
            add_to_env_path_list(k, [Path(fpath) for fpath in v], envvars)
        else:
            fpath = Path(v)
            fpath = fpath if fpath.is_absolute() else get_bin_path() / fpath
            envvars[k] = fpath.as_posix() if fpath.exists() else v
            sys.stderr.write(f"{k} = {envvars[k]}\n")
    return envvars


def detect_toolchain(environ: dict[str, str] | _Environ[str] | None = None) -> dict[str, str | Path | _Environ[str] | dict[str, Path]]:
    if hasattr(detect_toolchain, "cache"):
        return detect_toolchain.cache
    cached = _detect_toolchain(environ)
    if cached["toolchain"] == "visualstudio":
        get_binary("cmake", search_paths=[cached["environ"]["PATH"]])
        get_binary("ninja", search_paths=[cached["environ"]["PATH"]])
    detect_toolchain.cache = cached
    return cached


def _detect_toolchain(
    environ: dict[str, str] | _Environ[str] | None = None,
) -> dict[str, str | Path | _Environ[str] | dict[str, Path]]:
    environ = environ or os.environ.copy()
    for toolchain in ["msvc", "mingw", "visualstudio"]:
        envvarsf = get_bin_path() / f"toolchain_{toolchain}.json"
        if envvarsf.exists():
            return init_envvars_from_file(toolchain, envvarsf, environ)
        envvarsf = get_bin_path().parent / f"toolchain_{toolchain}.json"
        if envvarsf.exists():
            return init_envvars_from_file(toolchain, envvarsf, environ)
    if sys.platform == "win32":
        info = get_visualstudio_toolchain()
        if info:
            (get_bin_path() / "toolchain_visualstudio.json").write_text(json.dumps(info, cls=CustomEncoder, indent=2))
            return _detect_toolchain(environ)
    return {"toolchain": None, "environ": environ}


def get_visualstudio_toolchain(_expiry: int = 30) -> dict[str, str] | _Environ[str] | None:
    if sys.platform != "win32":
        return None
    vswhere = Path("C:/Program Files (x86)/Microsoft Visual Studio/Installer/vswhere.exe")
    if not vswhere.exists():
        return None

    def envvartopathset(env: dict[str, str] | _Environ[str]) -> dict[str, set[Path]]:
        return {k.upper(): {Path(p).absolute() for p in v.split(os.pathsep)} for k, v in env.items()}

    def diffenviron(envbase: dict[str, str] | _Environ[str], env: dict[str, str] | _Environ[str]) -> dict[str, str]:
        baseenvset = envvartopathset(envbase)
        newenvset = envvartopathset(env)
        diffenv = {k: {p.as_posix() for p in v.difference(baseenvset.get(k, set()))} for k, v in newenvset.items()}
        return {k: list(v) if len(v) > 1 else env[k] for k, v in diffenv.items() if len(v)}

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
    vsarch = platform.machine().lower()
    script = (
        "& { "
        f' &"{vspath}/Common7/Tools/Launch-VsDevShell.ps1"'
        f' -SkipAutomaticLocation -VsInstallationPath "{vspath}" -Arch "{vsarch}" -HostArch "{vsarch}"'
        ";gci env:/ | %{$_.Name+'='+$_.Value} }"
    )
    rslt = subprocess.run(
        [shutil.which("powershell"), "-NoProfile", "-Command", "-"],
        input=script,
        capture_output=True,
        text=True,
        check=False,
        env=os.environ.copy(),
    )
    if rslt.returncode != 0:
        return None
    commandout = rslt.stdout.splitlines()[4:]
    localvars = dict(line.strip().split("=") for line in commandout)
    vsvars = {k.upper(): v for k, v in localvars.items()}
    build_root = get_env_config_var("DEVEL_BUILDPATH", None)
    if build_root:
        tmp = Path(build_root) / "tmp"
        tmp.mkdir(exist_ok=True, parents=True)
        vsvars["TMP"] = vsvars["TEMP"] = str(tmp)
    diffenv = diffenviron(os.environ.copy(), vsvars)
    llvm = Path(f"{vspath}/VC/Tools/Llvm/x64/bin").absolute()
    if llvm.exists() and llvm not in diffenv.get("PATH", []):
        diffenv["PATH"] = [llvm, *diffenv.get("PATH", [])]
    return {"env": diffenv}


def get_cmake() -> Path:
    return get_binary("cmake")


def get_clang_format() -> Path:
    return get_binary("clang-format")


def get_ninja() -> Path:
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
    return get_binary("magick")


def get_win_flexbison() -> Path:
    return get_binary("flexbison", binname="win_flex").parent


def get_rclone() -> Path:
    return get_binary("rclone")


def get_nodejs() -> Path:
    return get_binary("node")


def get_deno() -> Path:
    return get_binary("deno")


def get_typesense_server() -> Path:
    return get_binary("typesense-server")


def get_npm() -> Path:
    if sys.platform == "win32":
        npm = Path(shutil.which("npm.cmd", path=get_nodejs().parent))
    else:
        npm = Path(shutil.which("npm", path=get_nodejs().parent))  # noqa: type: ignore
    add_to_path([npm.parent])
    return npm


def add_to_env_path_list(
    envvar: str,
    paths: list[Path],
    environ: dict[str, str] | _Environ[str] | None = None,
) -> dict[str, str] | _Environ[str]:
    paths = [fpath if fpath.is_absolute() else get_bin_path() / fpath for fpath in paths]
    environ = environ or os.environ.copy()
    alreadypaths = {Path(onepath or ".").absolute() for onepath in environ.get(envvar, "").split(os.pathsep)}
    appendpaths = [onepath.as_posix() for onepath in paths if onepath.absolute() not in alreadypaths]
    appendpathsstr = os.pathsep.join(appendpaths)
    if len(appendpathsstr) > 0:
        newpath = os.pathsep.join([appendpathsstr, environ.get(envvar, "")])
        environ[envvar] = newpath
        sys.stderr.write(f"{envvar} += {appendpathsstr}\n")
        sys.stderr.write(f"{envvar} = {newpath}\n")
    return environ


def add_to_path(paths: list[Path], environ: dict[str, str] | _Environ[str] | None = None) -> dict[str, str] | _Environ[str]:
    return add_to_env_path_list("PATH", paths, environ=environ)


def get_patch() -> Path:
    return get_binary("patch")


def acquire_tool(name: str, extra: list[str] | None = None) -> Path:
    if name == "ImageMagick":
        return get_imagemagick_convert()
    if name == "flexbison":
        return get_win_flexbison()
    if "toolchain:" in name:
        args = {"toolchain": name.split(":", maxsplit=1)[-1]}
        if extra and "--update" in extra:
            args["expiry"] = 0
        return init_toolchain(**args)
    return get_binary(name)


def get_android_toolchain(_expiry: int = 30) -> dict[str, str | Path | _Environ[str] | dict[str, Path]]:
    sdkpath = get_bin_path() / "android"
    sdk_root = sdkpath / "sdk"
    if "JAVA_HOME" in os.environ:
        os.environ.pop("JAVA_HOME")
    studiobin = _download_or_get_binary("studio", sdkpath, download_android_studio)
    sdkmanager = _download_or_get_binary("sdkmanager", sdk_root, download_android_sdk_manager)
    java = _download_or_get_binary("java", sdkpath)

    runenv = os.environ.copy()
    runenv["PATH"] = os.pathsep.join([str(java.parent), str(sdkmanager.parent), runenv["PATH"]])
    runenv["ANDROID_SDK_HOME"] = (sdk_root / "tmp").as_posix()
    runenv["ANDROID_USER_HOME"] = (sdk_root / "tmp").as_posix()
    runenv["JAVA_HOME"] = java.parent.parent.as_posix()

    dirs = {d.name for d in os.scandir(sdkpath)}
    packages = [
        # "ndk-bundle",
        f"ndk;{ANDROID_NDK_VERSION}",
        f"build-tools;{ANDROID_SDK_VERSION}.0.0",
        "platform-tools",
        f"platforms;android-{ANDROID_SDK_VERSION}",
    ]

    def accept_sdk_licenses(sdkmanager: Path, sdk_root: Path) -> None:
        # print(shlex.join([sdkmanager.as_posix(), f"--sdk_root={sdk_root}", "--licenses"]))
        proc = subprocess.Popen([sdkmanager.as_posix(), f"--sdk_root={sdk_root}", "--licenses"], stdin=subprocess.PIPE, env=runenv)
        while proc.poll() is None:
            time.sleep(1)
            proc.communicate(input=b"y\ny\ny\ny\ny\ny\ny\ny\ny\ny\ny\ny\ny\ny\ny\ny\ny\ny\n")

    accept_sdk_licenses(sdkmanager, sdk_root)

    if any(p.split(";", maxsplit=1)[0] not in dirs for p in packages):
        # print(shlex.join([sdkmanager.as_posix(), f"--sdk_root={sdk_root.as_posix()}", *packages]))
        subprocess.check_call([sdkmanager.as_posix(), f"--sdk_root={sdk_root.as_posix()}", *packages], env=runenv)
        accept_sdk_licenses(sdkmanager, sdk_root)

    ndk_home = (sorted((sdk_root / "ndk").glob("*"))[-1]).absolute()
    return {
        "env": {
            "PATH": [java.parent],
            "ANDROID_HOME": sdk_root.as_posix(),
            "ANDROID_SDK_ROOT": sdk_root.as_posix(),
            "ANDROID_NDK_HOME": ndk_home.as_posix(),
            "JAVA_HOME": java.parent.parent.as_posix(),
        },
        "ndk": ndk_home,
        "ndk_version": ANDROID_NDK_VERSION,
        "sdk_version": ANDROID_SDK_VERSION,
        "java_home": java.parent.parent,
        "sdk_root": sdk_root,
        "jarsigner": _download_or_get_binary("jarsigner", sdkpath),
        "java": java,
        "studio": studiobin,
        "sdkmanager": sdkmanager,
        "cmake_toolchain_file": ndk_home / "build/cmake/android.toolchain.cmake",
    }


def get_emscripten_toolchain(_expiry: int = 30) -> dict[str, str | Path | _Environ[str] | dict[str, Path]]:
    sdkpath = get_bin_path() / "emsdk"
    sdkpath.mkdir(exist_ok=True, parents=True)
    emconfig = sdkpath / ".emscripten"
    if not emconfig.exists():
        script = sdkpath / "emsdk.bat" if sys.platform == "win32" else sdkpath / "emsdk"
        if not script.exists():
            subprocess.check_call(
                [get_git().as_posix(), "clone", "https://github.com/emscripten-core/emsdk.git", sdkpath.as_posix()],
            )
        subprocess.check_call([f"{script.as_posix()}", "install", EMSDK_VERSION], cwd=sdkpath)
        subprocess.check_call([f"{script.as_posix()}", "activate", EMSDK_VERSION], cwd=sdkpath)
        lines = emconfig.read_text(encoding="utf-8").splitlines()
        newlines = [line if line.split("=")[0].strip() != "NODE_JS" else f"NODE_JS = '{get_nodejs().as_posix()}'" for line in lines]
        emconfig.write_text("\n".join(newlines), encoding="utf-8")
    os.environ["EM_CONFIG"] = emconfig.as_posix()
    _globals = {}
    _locals = {}
    exec(emconfig.read_text(encoding="utf-8"), _globals, _locals)  # noqa: S102, pylint: disable=exec-used
    return {
        "env": {
            "EM_CONFIG": emconfig.as_posix(),
            "PATH": [sdkpath, _locals["LLVM_ROOT"], _locals["BINARYEN_ROOT"], _locals["EMSCRIPTEN_ROOT"]],
            "EMSDK": sdkpath.as_posix(),
            "EMSDK_NODE": _locals["NODE_JS"],
        },
        "cmake_toolchain_file": sdkpath / "upstream" / "emscripten" / "cmake" / "Modules" / "Platform" / "Emscripten.cmake",
    }


def init_toolchain(
    toolchain: str,
    environ: dict[str, str] | _Environ[str] | None = None,
    expiry: int = 30,
) -> dict[str, str | Path | _Environ[str] | dict[str, Path]]:
    mapping = {
        "and": "android",
        "android": "android",
        "mingw": "mingw",
        "msvc": "msvc",
        "ms": "msvc",
        "vs": "visualstudio",
        "uwp": "visualstudio",
        "visualstudio": "visualstudio",
        "wasm": "emscripten",
        "emscripten": "emscripten",
    }
    toolchain = mapping.get(toolchain, toolchain)
    envvarsf = get_bin_path() / f"toolchain_{toolchain}.json"
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    if not envvarsf.exists() or (now - datetime.datetime.fromtimestamp(envvarsf.stat().st_mtime, tz=datetime.timezone.utc)).days > expiry:
        func_map = {
            "mingw": get_win_mingw_toolchain,
            "android": get_android_toolchain,
            "emscripten": get_emscripten_toolchain,
            "msvc": get_portable_msvc_toolchain,
            "visualstudio": get_visualstudio_toolchain,
        }
        info = func_map[toolchain](expiry)
        envvarsf.write_text(json.dumps(info, cls=CustomEncoder, indent=2))
    return init_envvars_from_file(toolchain, envvarsf, environ)


def get_win_mingw_toolchain(_expiry: int = 30) -> Path:
    msys2 = get_binary("msys2")
    msysbash = msys2.parent / "usr/bin/bash.exe"
    if not msysbash.exists():
        subprocess.check_call([msys2.as_posix(), "-y", f"-o{msys2.parent.as_posix()}"])
    if not msysbash.exists():
        raise ExternalToolsDownloadError("Bash from Msys2 not found")
    # Run for the first time
    subprocess.check_call([msysbash.as_posix(), "-lc", " "])
    # Core update (in case any core packages are outdated)
    subprocess.check_call([msysbash.as_posix(), "-lc", "pacman --noconfirm -Syuu"])
    # Normal update
    subprocess.check_call([msysbash.as_posix(), "-lc", "pacman --noconfirm -Syuu"])
    mingwarch = {"x64": "mingw-w64-ucrt-x86_64", "arm64": "mingw-w64-clang-aarch64"}[DefaultArch]

    packages = ["base-devel", f"{mingwarch}-toolchain", f"{mingwarch}-clang", f"{mingwarch}-clang-tools-extra"]
    subprocess.check_call([msysbash.as_posix(), "-lc", f"pacman --noconfirm -S --needed {' '.join(packages)}"])
    return {"env": {"PATH": [msys2.parent / "usr/bin", msys2.parent / "ucrt64/bin"]}}


def get_portable_msvc_toolchain(  # noqa: PLR0912, PLR0915, C901
    expiry: int = 30,
) -> dict[str, str | Path | _Environ[str] | dict[str, Path]]:
    manifest_url = "https://aka.ms/vs/17/release/channel"
    output_dir = get_bin_path() / "msvc"
    now = datetime.datetime.now(tz=datetime.timezone.utc)

    # other architectures may work or may not - not really tested
    host = platform.machine().lower()  # or x86
    target_arch = platform.machine().lower()  # or x86, arm, arm64
    download_cache = output_dir / "download_cache"
    download_cache.mkdir(exist_ok=True, parents=True)
    for file in download_cache.rglob("*"):
        if not file.is_dir() and (now - datetime.datetime.fromtimestamp(file.stat().st_mtime, tz=datetime.timezone.utc)).days > expiry:
            file.unlink(missing_ok=True)
    msiexec = shutil.which("msiexec")

    # shutil.rmtree(output_dir / "VC", ignore_errors=True)
    # shutil.rmtree(output_dir / "VC", ignore_errors=True)

    def msiextract(msi: Path, out: Path) -> None:
        subprocess.check_call([msiexec, "/a", str(msi), "/quiet", "/qn", f"TARGETDIR={out!s}"])
        return out

    def download(url: str, fname: str | None = None) -> bytes:
        fname = fname or hashlib.sha256(url.encode("utf-8")).hexdigest()
        cache = download_cache / fname
        if cache.exists():
            return cache.read_bytes()
        with urllib.request.urlopen(url) as res:
            cache.write_bytes(res.read())
            return cache.read_bytes()

    def download_progress(url: str, check: str, fname: str | None = None) -> Path:
        data = io.BytesIO()
        fname = fname or hashlib.sha256(url.encode("utf-8")).hexdigest()
        cache = download_cache / fname
        cache.parent.mkdir(exist_ok=True, parents=True)
        if cache.exists():
            return cache
        cache_tmp = cache.with_suffix(".tmp")
        cache_tmp.unlink(missing_ok=True)
        with cache_tmp.open("wb") as f, urllib.request.urlopen(url) as res:
            while True:
                block = res.read(1 << 20)
                if not block:
                    break
                f.write(block)
                data.write(block)
        data = data.getvalue()
        digest = hashlib.sha256(data).hexdigest()
        if check.lower() != digest:
            raise ValueError(f"checksum mismatch: {url}")
        cache_tmp.rename(cache)
        return cache

    # super crappy msi format parser just to find required .cab files
    def get_msi_cabs(msi_file: Path) -> Generator[any, any, None]:
        msi = msi_file.read_bytes()
        index = 0
        while True:
            index = msi.find(b".cab", index + 4)
            if index < 0:
                return
            yield msi[index - 32 : index + 4].decode("ascii")

    def first(items: any, cond: Optional[any] = None) -> any:
        return next(item for item in items if not cond or cond(item))

    ### download VS manifest
    manifest = json.loads(download(manifest_url, fname="manifest.json"))
    vs = first(
        manifest["channelItems"],
        lambda x: x["id"] == "Microsoft.VisualStudio.Manifests.VisualStudio",
    )
    payload = vs["payloads"][0]["url"]
    vsmanifest = json.loads(download(payload, fname="vsmanifest.json"))
    ### find MSVC & WinSDK versions

    packages = {}
    for pkg in vsmanifest["packages"]:
        packages.setdefault(pkg["id"].lower(), []).append(pkg)

    msvc = {}
    sdk = {}

    for pid in packages:
        if pid.startswith("Microsoft.VisualStudio.Component.VC.".lower()) and pid.endswith(
            ".x86.x64".lower(),
        ):
            pver = ".".join(pid.split(".")[4:6])
            if pver[0].isnumeric():
                msvc[pver] = pid
        elif pid.startswith(
            ("Microsoft.VisualStudio.Component.Windows10SDK.".lower(), "Microsoft.VisualStudio.Component.Windows11SDK.".lower()),
        ):
            pver = pid.split(".")[-1]
            if pver.isnumeric():
                sdk[pver] = pid
    sdk_ver = max(sorted(sdk.keys()))
    sdk_pid = sdk[sdk_ver]
    msvc_ver = ".".join(msvc[max(sorted(msvc.keys()))].split(".")[4:-2])
    output_dir.mkdir(exist_ok=True)
    ### download MSVC

    msvc_packages = [
        # MSVC binaries
        f"microsoft.vc.{msvc_ver}.tools.host{host}.target{target_arch}.base",
        f"microsoft.vc.{msvc_ver}.tools.host{host}.target{target_arch}.res.base",
        # MSVC headers
        f"microsoft.vc.{msvc_ver}.crt.headers.base",
        # MSVC libs
        f"microsoft.vc.{msvc_ver}.crt.{target_arch}.desktop.base",
        f"microsoft.vc.{msvc_ver}.crt.{target_arch}.store.base",
        # MSVC runtime source
        f"microsoft.vc.{msvc_ver}.crt.source.base",
        # ASAN
        f"microsoft.vc.{msvc_ver}.asan.headers.base",
        # f"microsoft.vc.{msvc_ver}.asan.{target_arch}.base",
        # MSVC redist
        # f"microsoft.vc.{msvc_ver}.crt.redist.x64.base",
        # LLVM
        "microsoft.visualstudio.vc.llvm.base",  # clang-format
        "microsoft.visualstudio.vc.llvm.clang",
        # "microsoft.visualStudio.vc.msbuild.llvm",
        # "microsoft.visualStudio.vc.msbuild.llvm",
    ]

    for pkg in msvc_packages:
        p = first(packages[pkg], lambda p: p.get("language") in (None, "en-US"))
        for payload in p["payloads"]:
            with zipfile.ZipFile(download_progress(payload["url"], payload["sha256"], fname=pkg + "_" + payload["fileName"])) as z:
                for name in z.namelist():
                    if name.startswith("Contents/"):
                        out = output_dir / Path(name).relative_to("Contents")
                        out.parent.mkdir(parents=True, exist_ok=True)
                        out.write_bytes(z.read(name))

    ### download Windows SDK

    sdk_packages = [
        # Windows SDK tools (like rc.exe & mt.exe)
        "Windows SDK for Windows Store Apps Tools-x86_en-us.msi",
        # Windows SDK headers
        "Windows SDK for Windows Store Apps Headers OnecoreUap-x86_en-us.msi",
        "Windows SDK for Windows Store Apps Headers-x86_en-us.msi",
        f"Windows SDK OnecoreUap Headers {target_arch}-x86_en-us.msi",
        "Windows SDK Desktop Headers x86-x86_en-us.msi",  # needed for dbghelp.h abseil
        # Windows SDK libs
        "Windows SDK for Windows Store Apps Libs-x86_en-us.msi",
        f"Windows SDK Desktop Libs {target_arch}-x86_en-us.msi",
        # CRT headers & libs
        "Universal CRT Headers Libraries and Sources-x86_en-us.msi",
        # CRT redist
        # "Universal CRT Redistributable-x86_en-us.msi",
    ]

    sdk_pkg = packages[sdk_pid][0]
    sdk_pkg = packages[first(sdk_pkg["dependencies"]).lower()][0]

    msi: list[Path] = []
    cabs: list[str] = []

    # download msi files
    for pkg in sdk_packages:
        payload = first(sdk_pkg["payloads"], lambda p, pkg=pkg: p["fileName"] == f"Installers\\{pkg}")
        f = download_progress(payload["url"], payload["sha256"], fname=pkg)
        msi.append(f)
        cabs += list(get_msi_cabs(f))

    # download .cab files
    for pkg in cabs:
        payload = first(sdk_pkg["payloads"], lambda p, pkg=pkg: p["fileName"] == f"Installers\\{pkg}")
        download_progress(payload["url"], payload["sha256"], fname=pkg)

    # run msi installers
    for m in msi:
        msiextract(m, output_dir)

    ### versions

    msvcv = next(iter((output_dir / "VC/Tools/MSVC").glob("*"))).name
    sdkv = next(iter((output_dir / "Windows Kits/10/bin").glob("*"))).name

    # place debug CRT runtime files into MSVC folder (not what real Visual Studio installer does... but is reasonable)
    pkg = "microsoft.visualcpp.runtimedebug.14"
    dbg = first(vsmanifest["packages"], lambda p: p["id"].lower().startswith(pkg) and p.get("machineArch", p["chip"]) == host)
    payload = first(dbg["payloads"], lambda p: p["fileName"].endswith(".msi"))
    msi = None
    for payload in dbg["payloads"]:
        f = download_progress(payload["url"], payload["sha256"], fname=Path(pkg) / payload["fileName"])
        msi = f if payload["fileName"].endswith(".msi") else msi
    msi_dir = msiextract(msi, output_dir / "temp")
    dst = output_dir / "VC/Tools/MSVC" / msvcv / f"bin/Host{host}/{target_arch}"
    for f in first(Path(msi_dir).glob("System*")).iterdir():
        f.replace(dst / f.name)
    shutil.rmtree(msi_dir, ignore_errors=True)

    if False:  # pylint: disable=using-constant-test
        # download DIA SDK and put msdia140.dll file into MSVC folder
        pkg = "microsoft.visualc.140.dia.sdk.msi"
        dia = packages[pkg][0]
        msi = None

        for payload in dia["payloads"]:
            f = download_progress(payload["url"], payload["sha256"], fname=Path(pkg) / payload["fileName"])
            msi = f if payload["fileName"].endswith(".msi") else msi
        msi_dir = msiextract(msi, output_dir / "temp")
        msdia = {"x86": "msdia140.dll", "x64": "amd64/msdia140.dll", "arm64": "arm/msdia140.dll"}[host]
        src = msi_dir / "Program Files" / "Microsoft Visual Studio 14.0" / "DIA SDK" / "bin" / msdia
        src.replace(dst / "msdia140.dll")
        shutil.rmtree(msi_dir, ignore_errors=True)

    ### cleanup
    shutil.rmtree(output_dir / "Common7", ignore_errors=True)
    for f in ["Auxiliary", f"lib/{target_arch}/store", f"lib/{target_arch}/uwp"]:
        shutil.rmtree(output_dir / "VC/Tools/MSVC" / msvcv / f)
    for f in output_dir.glob("*.msi"):
        f.unlink()
    for f in ["Catalogs", "DesignTime", f"bin/{sdkv}/chpe", f"Lib/{sdkv}/ucrt_enclave"]:
        shutil.rmtree(output_dir / "Windows Kits/10" / f, ignore_errors=True)
    for arch in ["x86", "x64", "arm", "arm64"]:
        if arch != target_arch:
            shutil.rmtree(output_dir / "VC/Tools/MSVC" / msvcv / f"bin/Host{arch}", ignore_errors=True)
            shutil.rmtree(output_dir / "Windows Kits/10/bin" / sdkv / arch, ignore_errors=True)
            shutil.rmtree(output_dir / "Windows Kits/10/Lib" / sdkv / "ucrt" / arch, ignore_errors=True)
            shutil.rmtree(output_dir / "Windows Kits/10/Lib" / sdkv / "um" / arch, ignore_errors=True)
    shutil.rmtree(msi_dir, ignore_errors=True)
    shutil.rmtree(msi_dir, ignore_errors=True)
    msvc_root = output_dir / "VC/Tools/MSVC" / msvcv
    sdk_root = output_dir / "Windows Kits/10"
    mt_exe = Path(shutil.which("mt", path=sdk_root / "bin" / sdkv / target_arch))
    rc_exe = Path(shutil.which("rc", path=sdk_root / "bin" / sdkv / target_arch))
    cl_exe = Path(shutil.which("cl", path=msvc_root / "bin" / f"Host{host}" / target_arch))
    clang_cl_exe = Path(shutil.which("clang-cl", path=msvc_root / f"../../Llvm/{host}/bin"))

    if not cl_exe.is_file():
        raise ExternalToolsDownloadError("Cannot find cl.exe")
    if not mt_exe.is_file():
        raise ExternalToolsDownloadError("Cannot find mt.exe")
    if not rc_exe.is_file():
        raise ExternalToolsDownloadError("Cannot find rc.exe")
    envvars = {
        "MSVC_VERSION": msvcv,
        "MSVC_ARCH": target_arch,
        "SDK_VERSION": sdkv,
        "SDK_ARCH": target_arch,
        "MSVC_ROOT": msvc_root,
        "SDK_INCLUDE": sdk_root / "Include" / sdkv,
        "SDK_LIBS": sdk_root / "Lib" / sdkv,
        "VCTOOLSINSTALLDIR": msvc_root,
        "PATH": [cl_exe.parent, clang_cl_exe.parent, mt_exe.parent, mt_exe.parent / "ucrt"],
        "INCLUDE": [
            msvc_root / "include",
            sdk_root / "Include" / sdkv / "ucrt",
            sdk_root / "Include" / sdkv / "shared",
            sdk_root / "Include" / sdkv / "um",
            sdk_root / "Include" / sdkv / "winrt",
            sdk_root / "Include" / sdkv / "cppwinrt",
        ],
        "LIB": [
            msvc_root / "lib" / target_arch,
            sdk_root / "Lib" / sdkv / "ucrt" / target_arch,
            sdk_root / "Lib" / sdkv / "um" / target_arch,
        ],
        "CL": " -FS /D_WIN32_WINNT=0x0A00",
    }
    ### setup.bat
    batlines = [
        f"set {k}={';'.join([str(val) for val in v])};%{k}%" if isinstance(v, list) else f"set {k}={v!s}" for k, v in envvars.items()
    ]
    ps1lines = [
        f'$env:{k}="{";".join([str(val) for val in v])};$env:{k}"' if isinstance(v, list) else f'$env:{k}="{v!s}"'
        for k, v in envvars.items()
    ]

    (output_dir / "setup.bat").write_text("\n".join(batlines))
    (output_dir / "setup.ps1").write_text("\n".join(ps1lines))

    return {"env": envvars, "cl": cl_exe, "mt": mt_exe, "rc": rc_exe, "clang-cl": clang_cl_exe}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--bin-dir", type=Path, default=None, help="Location of bin directory")
    parser.add_argument("tool", type=str, nargs="*")
    args, extra = parser.parse_known_args()
    if args.bin_dir:
        DEVEL_BINPATH = Path(args.bin_dir).absolute()
    for tool in args.tool:
        acquire_tool(tool, extra)
