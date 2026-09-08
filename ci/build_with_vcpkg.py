#!/usr/bin/env python3
# cppforge-sync
import argparse
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.append(Path(__file__).parent.parent.as_posix())

import externaltools


def vcpkg_remove(port: str) -> None:
    cmd = [vcpkgexe.as_posix(), f"--host-triplet={host_triplet}", "remove", port, "--recurse"]
    subprocess.check_call(cmd, env=myenv, cwd=vcpkgroot)


def vcpkg_install(port: str) -> None:
    cmd = [vcpkgexe.as_posix(), f"--host-triplet={host_triplet}", "install", "--allow-unsupported", port]
    subprocess.check_call(cmd, env=myenv, cwd=vcpkgroot)


def test_vcpkg_build(config: str, host_triplet: str, runtime_triplet: str, clean: bool = False) -> None:  # noqa: PT028
    testdir = workdir / f"{runtime_triplet}_Test_{config}"
    if clean and testdir.exists():
        shutil.rmtree(testdir.as_posix())
    testdir.mkdir(exist_ok=True)
    cmakebuildextraargs = ["--config", config] if sys.platform == "win32" else []
    cmakeconfigargs: list[str] = []
    if "mingw" in host_triplet or "mingw" in runtime_triplet:
        info = externaltools.init_toolchain("mingw", os.environ)
        cmakeconfigargs += [
            "-G",
            "Ninja",
            f"-DCMAKE_MAKE_PROGRAM:FILEPATH={externaltools.get_ninja().as_posix()}",
        ]
    if "android" in runtime_triplet:
        info = externaltools.init_toolchain("android", os.environ)
        abis = {
            "arm64-android": ["-DANDROID_ABI=arm64-v8a"],
            "arm-neon-android": ["-DANDROID_ABI=armeabi-v7a"],
            "x86-android": ["-DANDROID_ABI=x86"],
            "x64-android": ["-DANDROID_ABI=x86_64"],
        }

        cmakeconfigargs += [
            f"-DCMAKE_TOOLCHAIN_FILE:PATH={info['cmake_toolchain_file'].as_posix()}",
            "-DANDROID=1",
            f"-DANDROID_NATIVE_API_LEVEL={externaltools.ANDROID_MIN_SDK_VERSION}",
        ] + abis[runtime_triplet]

        if shutil.which("make") is not None:
            cmakeconfigargs += ["-G", "Unix Makefiles"]
        else:
            cmakeconfigargs += [
                "-G",
                "Ninja",
                f"-DCMAKE_MAKE_PROGRAM:FILEPATH={externaltools.get_ninja().as_posix()}",
            ]
    if "wasm32" in runtime_triplet:
        info = externaltools.init_toolchain("emscripten", os.environ)
        cmakeconfigargs += [
            f"-DCMAKE_TOOLCHAIN_FILE:PATH={info['cmake_toolchain_file'].as_posix()}",
        ]
        if sys.platform == "win32":
            if shutil.which("make") is not None:
                cmakeconfigargs += ["-G", "MinGW Makefiles"]
            else:
                cmakeconfigargs += [
                    "-G",
                    "Ninja",
                    f"-DCMAKE_MAKE_PROGRAM:FILEPATH={externaltools.get_ninja().as_posix()}",
                ]

    if "windows" in runtime_triplet:
        cmakeconfigargs += [
            "-G",
            "Visual Studio 17 2022",
            "-T",
            f"host={externaltools.DefaultArch}",
            "-A",
            ("Win32" if "x86" in runtime_triplet else externaltools.DefaultArch),
        ]
    if "uwp" in runtime_triplet:
        cmakeconfigargs += [
            "-DCMAKE_SYSTEM_NAME=WindowsStore",
            "-DCMAKE_SYSTEM_VERSION=10.0",
        ]
    ctestextraargs = ["-C", config] if sys.platform == "win32" else []
    cmd: list[str] = [
        externaltools.get_cmake().as_posix(),
        f"-DCMAKE_BUILD_TYPE:STR={config}",
        f"-DVCPKG_ROOT:PATH={vcpkgroot.as_posix()}",
        f"-DVCPKG_TARGET_TRIPLET:STR={runtime_triplet}",
        "-DVCPKG_VERBOSE:BOOL=ON",
        *cmakeconfigargs,
        (scriptdir / "sample").as_posix(),
    ]
    subprocess.check_call(cmd, cwd=testdir.as_posix(), env=myenv)
    subprocess.check_call(
        [externaltools.get_cmake().as_posix(), "--build", ".", "--verbose", "-j", *cmakebuildextraargs],
        cwd=testdir,
    )
    subprocess.check_call(
        [externaltools.get_ctest().as_posix(), ".", "--repeat", "until-fail:10", "--output-on-failure", *ctestextraargs],
        cwd=testdir,
    )


parser = argparse.ArgumentParser(description="Test VCPKG Workflow")
parser.add_argument("--verbose", action="store_true", help="Clean")
parser.add_argument("--reporoot", type=Path, default=None, help="Repository")
parser.add_argument("--vcpkg", type=Path, default=None, help="Repository")
parser.add_argument("--bindir", type=Path, default=None, help="Repository")
parser.add_argument("--workdir", type=Path, default=None, help="Root")

parser.add_argument("--clean", action="store_true", help="Clean")
parser.add_argument("--host-triplet", type=str, default=None, help="Triplet")
parser.add_argument("--runtime-triplets", type=str, default=None, help="Triplet")
args = parser.parse_args()

if args.verbose:
    logging.basicConfig(level=logging.DEBUG)

reporoot = args.reporoot or Path(__file__).parent.parent.absolute()
scriptdir = (reporoot / "ci").absolute()
portname = next((reporoot / "ci" / "vcpkg-additional-ports").glob("*")).name
workdir = Path(args.workdir or ".").absolute()
workdir.mkdir(exist_ok=True)
vcpkgroot = args.vcpkg or externaltools.get_vcpkg_root(Path().absolute() / "vcpkg") or (workdir / "vcpkg")
bindir = externaltools.get_bin_path(workdir / "bin")
externaltools.DEVEL_BINPATH = bindir

vcpkgportfile = vcpkgroot / "ports" / portname / "portfile.cmake"

if not vcpkgroot.exists():
    subprocess.check_call(
        [
            externaltools.get_git().as_posix(),
            "clone",
            "-q",
            "https://github.com/ankurvdev/vcpkg.git",
            "--branch",
            "lkg_patched",
            "--depth",
            "1",
        ],
        cwd=vcpkgroot.parent.as_posix(),
    )

bootstrapscript = "bootstrap-vcpkg.bat" if sys.platform == "win32" else "bootstrap-vcpkg.sh"
defaulttriplet = f"{externaltools.DefaultArch}-windows-static" if sys.platform == "win32" else f"{externaltools.DefaultArch}-linux"
host_triplet = args.host_triplet or defaulttriplet
runtime_triplets = (args.runtime_triplets or defaulttriplet).split(",")

for portdir in (scriptdir / "vcpkg-additional-ports").glob("*"):
    dst = vcpkgroot / "ports" / portdir.name
    shutil.rmtree(dst.as_posix(), ignore_errors=True)
    shutil.copytree(portdir.as_posix(), dst)

vcpkgportfile.write_text(vcpkgportfile.read_text().replace("SOURCE_PATH ${SOURCE_PATH}", f'SOURCE_PATH "{scriptdir.parent.as_posix()}"'))

subprocess.check_call((vcpkgroot / bootstrapscript).as_posix(), shell=True, cwd=vcpkgroot)  # noqa: S602
vcpkgexe = Path(shutil.which("vcpkg", path=vcpkgroot) or "")
VCPKG_EXE = vcpkgexe
if args.clean:
    vcpkg_remove(portname + ":" + host_triplet)
    for runtime_triplet in runtime_triplets:
        vcpkg_remove(portname + ":" + runtime_triplet)

for runtime_triplet in runtime_triplets:
    myenv = os.environ.copy()
    myenv["VCPKG_ROOT"] = vcpkgroot.as_posix()
    myenv["VCPKG_BINARY_SOURCES"] = "clear"
    myenv["VCPKG_KEEP_ENV_VARS"] = "ANDROID_NDK_ROOT"
    myenv["VERBOSE"] = "1"
    if "android" in host_triplet or "android" in runtime_triplet:
        externaltools.init_toolchain("android", myenv)
    if "mingw" in host_triplet or "mingw" in runtime_triplet:
        externaltools.init_toolchain("mingw", myenv)
    if "wasm32" in host_triplet or "wasm32" in runtime_triplet:
        externaltools.init_toolchain("emscripten", myenv)

for runtime_triplet in runtime_triplets:
    myenv = os.environ.copy()
    myenv["VCPKG_ROOT"] = vcpkgroot.as_posix()
    myenv["VCPKG_BINARY_SOURCES"] = "clear"
    myenv["VCPKG_KEEP_ENV_VARS"] = "ANDROID_NDK_ROOT"
    myenv["VERBOSE"] = "1"
    if "android" in host_triplet or "android" in runtime_triplet:
        externaltools.init_toolchain("android", myenv)
    if "mingw" in host_triplet or "mingw" in runtime_triplet:
        externaltools.init_toolchain("mingw", myenv)
    if "wasm32" in host_triplet or "wasm32" in runtime_triplet:
        externaltools.init_toolchain("emscripten", myenv)
    try:
        for log in Path(vcpkgroot / "buildtrees").rglob("*.log"):
            if log.parent.parent.name == "buildtrees":
                log.unlink()
        logging.debug(myenv)  # noqa: LOG015

        vcpkg_install(portname + ":" + host_triplet)
        if host_triplet != runtime_triplet:
            vcpkg_install(portname + ":" + runtime_triplet)
    except subprocess.CalledProcessError:
        if args.verbose:
            logs = list(Path(vcpkgroot / "buildtrees").rglob("*.log"))
            for log in logs:
                if log.parent.parent.name == "buildtrees":
                    logging.debug(f"\n\n ========= START: {log} ===========")  # noqa: LOG015
                    logging.debug(log.read_text())  # noqa: LOG015
                    logging.debug(f" ========= END: {log} =========== \n\n")  # noqa: LOG015
        raise

    test_vcpkg_build("Debug", host_triplet, runtime_triplet, clean=args.clean)
    test_vcpkg_build("Release", host_triplet, runtime_triplet, clean=args.clean)
