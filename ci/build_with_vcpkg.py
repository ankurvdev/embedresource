import argparse
import os
import pathlib
import pprint
import shutil
import subprocess
import sys

import externaltools


def _find_from_path(name: str):
    return pathlib.Path(shutil.which(name) or "")


def _find_from_vcpkg(name: str):
    if not VCPKG_EXE.exists():
        return pathlib.Path()
    try:
        if sys.platform == "win32":
            return pathlib.Path(subprocess.check_output([VCPKG_EXE, "env", f"where {name}"], text=True).splitlines()[0])
        else:
            return pathlib.Path(subprocess.check_output([VCPKG_EXE, "env", f"which {name}"], text=True).splitlines()[0])
    except subprocess.CalledProcessError:
        return pathlib.Path()


def _find_from_vs_win(name: str):
    if sys.platform != "win32":
        return pathlib.Path()
    vs_path = subprocess.run(
        [
            pathlib.Path("C:/Program Files (x86)/Microsoft Visual Studio/Installer/vswhere.exe").as_posix(),
            "-prerelease",
            "-version",
            "16.0",
            "-property",
            "installationPath",
            "-products",
            "*",
            "-requires",
            "Microsoft.VisualStudio.Component.VC.CMake.Project",
        ],
        check=True,
        capture_output=True,
        universal_newlines=True,
    ).stdout.splitlines()[-1]
    return pathlib.Path(list(pathlib.Path(vs_path).rglob(f"{name}.exe"))[0])


CACHED_PATHS: dict[str, pathlib.Path] = {}
VCPKG_EXE = pathlib.Path()


def _find_cached_paths(name: str):
    if name in CACHED_PATHS:
        return CACHED_PATHS[name]
    return pathlib.Path()


def find_binary(name: str):
    for fn in [
        _find_cached_paths,
        _find_from_path,
        _find_from_vcpkg,
        _find_from_vs_win,
    ]:
        pth: pathlib.Path = fn(name)
        if pth != pathlib.Path():
            CACHED_PATHS[name] = pth.absolute()
            print(f"{name} => {pth}")
            return pth.absolute().as_posix()
    raise Exception(f"Cannot find {name}")


parser = argparse.ArgumentParser(description="Test VCPKG Workflow")
parser.add_argument("--workdir", type=str, default=".", help="Root")
parser.add_argument("--clean", action="store_true", help="Clean")
parser.add_argument("--quiet", action="store_true", help="Quiet")
parser.add_argument("--host-triplet", type=str, default=None, help="Triplet")
parser.add_argument("--runtime-triplet", type=str, default=None, help="Triplet")
args = parser.parse_args()
scriptdir = pathlib.Path(__file__).parent.absolute()
portname = "ankurvdev-embedresource"
workdir = pathlib.Path(args.workdir).absolute()
workdir.mkdir(exist_ok=True)
vcpkgroot = workdir / "vcpkg"
vcpkgportfile = vcpkgroot / "ports" / portname / "portfile.cmake"
androidroot = workdir / "android"

if not vcpkgroot.exists():
    subprocess.check_call(
        [
            find_binary("git"),
            "clone",
            "-q",
            "https://github.com/ankurvdev/vcpkg.git",
            "--branch",
            "lkg_patched",
            "--depth",
            "1",
        ],
        cwd=workdir.as_posix(),
    )

bootstrapscript = "bootstrap-vcpkg.bat" if sys.platform == "win32" else "bootstrap-vcpkg.sh"
defaulttriplet = f"{externaltools.DefaultArch}-windows-static" if sys.platform == "win32" else f"{externaltools.DefaultArch}-linux"
host_triplet = args.host_triplet or defaulttriplet
runtime_triplet = args.runtime_triplet or defaulttriplet

for portdir in (scriptdir / "vcpkg-additional-ports").glob("*"):
    dst = vcpkgroot / "ports" / portdir.name
    shutil.rmtree(dst.as_posix(), ignore_errors=True)
    shutil.copytree(portdir.as_posix(), dst)

vcpkgportfile.write_text(vcpkgportfile.read_text().replace("SOURCE_PATH ${SOURCE_PATH}", f'SOURCE_PATH "{scriptdir.parent.as_posix()}"'))

myenv = os.environ.copy()
myenv["VCPKG_ROOT"] = vcpkgroot.as_posix()
myenv["VCPKG_BINARY_SOURCES"] = "clear"
myenv["VCPKG_KEEP_ENV_VARS"] = "ANDROID_NDK_HOME"
myenv["VERBOSE"] = "1"
if "android" in host_triplet or "android" in runtime_triplet:
    paths = externaltools.download_android_to((workdir / "android"))
    myenv["ANDROID_NDK_HOME"] = paths["ndk"].as_posix()
if "wasm32" in host_triplet or "wasm32" in runtime_triplet:
    info = externaltools.download_emscripten_info_to(workdir / "emsdk")
    alreadypaths = set([pathlib.Path(onepath).absolute() for onepath in myenv["PATH"].split(os.pathsep)])
    appendpaths = list([onepath.as_posix() for onepath in info.paths if onepath.absolute() not in alreadypaths])
    appendpathsstr = os.pathsep.join(appendpaths)
    myenv["VCPKG_KEEP_ENV_VARS"] += ";EMSDK;PATH;EMSCRIPTEN_ROOT"
    if len(appendpathsstr) > 0:
        newpath = os.pathsep.join([appendpathsstr, myenv["PATH"]])
        myenv["PATH"] = newpath
        sys.stderr.write(f"PATH += {appendpathsstr}\n")
        sys.stderr.write(f"PATH = {newpath}\n")
    for envvarname, envvarval in info.envvars.items():
        sys.stderr.write(f"{envvarname} = {envvarval}\n")
        myenv[envvarname] = envvarval

subprocess.check_call((vcpkgroot / bootstrapscript).as_posix(), shell=True, cwd=workdir, env=myenv)
vcpkgexe = pathlib.Path(shutil.which("vcpkg", path=vcpkgroot) or "")
VCPKG_EXE = vcpkgexe


def vcpkg_remove(port: str):
    cmd = [vcpkgexe.as_posix(), f"--host-triplet={host_triplet}", "remove", port, "--recurse"]
    print(" ".join(cmd))
    subprocess.check_call(cmd, env=myenv, cwd=vcpkgroot)


def vcpkg_install(port: str):
    cmd = [vcpkgexe.as_posix(), f"--host-triplet={host_triplet}", "install", port]
    print(" ".join(cmd))
    subprocess.check_call(cmd, env=myenv, cwd=vcpkgroot)


print(f"VCPKG_ROOT = {vcpkgroot}")

try:
    for log in pathlib.Path(vcpkgroot / "buildtrees").rglob("*.log"):
        if log.parent.parent.name == "buildtrees":
            log.unlink()
    pprint.pprint(myenv)
    if args.clean:
        vcpkg_remove(portname + ":" + host_triplet)
        vcpkg_remove(portname + ":" + runtime_triplet)
    vcpkg_install(portname + ":" + host_triplet)
    if host_triplet != runtime_triplet:
        vcpkg_install(portname + ":" + runtime_triplet)
except subprocess.CalledProcessError:
    if not args.quiet:
        logs = list(pathlib.Path(vcpkgroot / "buildtrees").rglob("*.log"))
        for log in logs:
            if log.parent.parent.name == "buildtrees":
                print(f"\n\n ========= START: {log} ===========")
                print(log.read_text())
                print(f" ========= END: {log} =========== \n\n")
    raise


def test_vcpkg_build(config: str, host_triplet: str, runtime_triplet: str):
    testdir = workdir / f"{runtime_triplet}_Test_{config}"
    if testdir.exists():
        shutil.rmtree(testdir.as_posix())
    testdir.mkdir()
    cmakebuildextraargs = ["--config", config] if sys.platform == "win32" else []
    cmakeconfigargs: list[str] = []
    if "android" in runtime_triplet:
        cmakeconfigargs += [
            "-DCMAKE_TOOLCHAIN_FILE:PATH=" + myenv["ANDROID_NDK_HOME"] + "/build/cmake/android.toolchain.cmake",
            "-DANDROID=1",
            "-DANDROID_NATIVE_API_LEVEL=26",
            "-DANDROID_ABI=arm64-v8a",
        ]
        if runtime_triplet == "arm64-android":
            cmakeconfigargs += ["-DANDROID_ABI=arm64-v8a"]
        else:
            cmakeconfigargs += ["-DANDROID_ABI=armeabi-v7a"]
        if shutil.which("make") is not None:
            cmakeconfigargs += ["-G", "Unix Makefiles"]
        else:
            cmakeconfigargs += [
                "-G",
                "Ninja",
                f"-DCMAKE_MAKE_PROGRAM:FILEPATH={find_binary('ninja')}",
            ]
    if "wasm32" in runtime_triplet:
        cmakeconfigargs += [
            f"-DCMAKE_TOOLCHAIN_FILE:PATH={(vcpkgroot / 'scripts' / 'toolchains' / 'emscripten.cmake').as_posix()}",
        ]
        if sys.platform == "win32":
            if shutil.which("make") is not None:
                cmakeconfigargs += ["-G", "MinGW Makefiles"]
            else:
                cmakeconfigargs += [
                    "-G",
                    "Ninja",
                    f"-DCMAKE_MAKE_PROGRAM:FILEPATH={find_binary('ninja')}",
                ]

    if "windows" in runtime_triplet:
        cmakeconfigargs += [
            "-G",
            "Visual Studio 17 2022",
            "-A",
            ("Win32" if "x86" in runtime_triplet else externaltools.DefaultArch),
        ]
    ctestextraargs = ["-C", config] if sys.platform == "win32" else []
    cmd: list[str] = (
        [
            find_binary("cmake"),
            f"-DCMAKE_BUILD_TYPE:STR={config}",
            f"-DVCPKG_ROOT:PATH={vcpkgroot.as_posix()}",
            f"-DVCPKG_TARGET_TRIPLET:STR={runtime_triplet}",
            "-DVCPKG_VERBOSE:BOOL=ON",
        ]
        + cmakeconfigargs
        + [(scriptdir / "sample").as_posix()]
    )
    subprocess.check_call(cmd, cwd=testdir.as_posix(), env=myenv)
    subprocess.check_call(
        [find_binary("cmake"), "--build", ".", "--verbose", "-j"] + cmakebuildextraargs,
        cwd=testdir,
    )
    if runtime_triplet == host_triplet:
        subprocess.check_call(
            [find_binary("ctest"), ".", "--output-on-failure"] + ctestextraargs,
            cwd=testdir,
        )


test_vcpkg_build(
    "Debug",
    host_triplet,
    runtime_triplet,
)
test_vcpkg_build("Release", host_triplet, runtime_triplet)
