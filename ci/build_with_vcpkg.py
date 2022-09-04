import argparse
import os
import pathlib
import pprint
import shutil
import subprocess
import sys


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
    except Exception:
        return pathlib.Path()


def _find_from_vs_win(name: str):
    if sys.platform != "win32":
        return pathlib.Path()
    vs_path = subprocess.run([
        pathlib.Path("C:/Program Files (x86)/Microsoft Visual Studio/Installer/vswhere.exe").as_posix(),
        "-prerelease", "-version", "16.0", "-property", "installationPath", "-products", "*", "-requires", "Microsoft.VisualStudio.Component.VC.CMake.Project"
    ], check=True, capture_output=True, universal_newlines=True).stdout.splitlines()[-1]
    return pathlib.Path(list(pathlib.Path(vs_path).rglob(f"{name}.exe"))[0])


CACHED_PATHS: dict[str, pathlib.Path] = {}
VCPKG_EXE = pathlib.Path()


def _find_cached_paths(name: str):
    if name in CACHED_PATHS:
        return CACHED_PATHS[name]
    return pathlib.Path()


def find_binary(name: str):
    for fn in [_find_cached_paths, _find_from_path, _find_from_vcpkg, _find_from_vs_win]:
        pth: pathlib.Path = fn(name)
        if pth != pathlib.Path():
            CACHED_PATHS[name] = pth.absolute()
            print(f"{name} => {pth}")
            return pth.absolute().as_posix()
    raise Exception(f"Cannot find {name}")


parser = argparse.ArgumentParser(description="Test VCPKG Workflow")
parser.add_argument("--workdir", type=str, default=".", help="Root")
parser.add_argument("--host-triplet", type=str, default=None, help="Triplet")
parser.add_argument("--runtime-triplet", type=str, default=None, help="Triplet")
args = parser.parse_args()
workdir = pathlib.Path(args.workdir).absolute()
os.makedirs(workdir, exist_ok=True)
vcpkgroot = (workdir / "vcpkg")
androidroot = (workdir / "android")

if not vcpkgroot.exists():
    subprocess.check_call([find_binary("git"), "clone", "-q", "https://github.com/ankurvdev/vcpkg.git",
                          "--branch", "lkg_patched", "--depth", "1"], cwd=workdir.as_posix())

scriptdir = pathlib.Path(__file__).parent.absolute()
bootstrapscript = "bootstrap-vcpkg.bat" if sys.platform == "win32" else "bootstrap-vcpkg.sh"
defaulttriplet = "x64-windows-static" if sys.platform == "win32" else "x64-linux"
host_triplet = args.host_triplet or defaulttriplet
runtime_triplet = args.runtime_triplet or defaulttriplet

myenv = os.environ.copy()
myenv['VCPKG_OVERLAY_PORTS'] = (scriptdir / 'vcpkg-additional-ports').as_posix()
myenv['VCPKG_KEEP_ENV_VARS'] = 'VCPKG_USE_SRC_DIR;ANDROID_NDK_HOME'
myenv['VCPKG_USE_SRC_DIR'] = scriptdir.parent.as_posix()
myenv['VERBOSE'] = "1"
if "android" in host_triplet or "android" in runtime_triplet:
    import download_android_sdk
    paths = download_android_sdk.DownloadTo((workdir / "android"))
    myenv['ANDROID_NDK_HOME'] = paths['ndk'].as_posix()
subprocess.check_call((vcpkgroot / bootstrapscript).as_posix(), shell=True, cwd=workdir, env=myenv)
vcpkgexe = pathlib.Path(shutil.which("vcpkg", path=vcpkgroot) or "")
VCPKG_EXE = vcpkgexe
try:
    for log in pathlib.Path(vcpkgroot / "buildtrees").rglob('*.log'):
        if log.parent.parent.name == 'buildtrees':
            log.unlink()
    pprint.pprint(myenv)
    cmd1 = [vcpkgexe.as_posix(), f"--host-triplet={host_triplet}", "install", "embedresource:" + host_triplet]
    cmd2 = [vcpkgexe.as_posix(), f"--host-triplet={host_triplet}", "install", "embedresource:" + runtime_triplet]
    print(f"VCPKG_ROOT = {vcpkgroot}")
    print(" ".join(cmd1))
    print(" ".join(cmd2))
    subprocess.check_call(cmd1, env=myenv, cwd=vcpkgroot)
    subprocess.check_call(cmd2, env=myenv, cwd=vcpkgroot)
except Exception:
    logs = list(pathlib.Path(vcpkgroot / "buildtrees").rglob('*.log'))
    for log in logs:
        if log.parent.parent.name == 'buildtrees':
            print(f"\n\n ========= START: {log} ===========")
            print(log.read_text())
            print(f" ========= END: {log} =========== \n\n")
    raise


def test_vcpkg_build(config: str, host_triplet: str, runtime_triplet: str):
    testdir = workdir / f"{runtime_triplet}_Test_{config}"
    if testdir.exists():
        shutil.rmtree(testdir.as_posix())
    testdir.mkdir()
    cmakebuildextraargs = (["--config", config] if sys.platform == "win32" else [])
    cmakeconfigargs: list[str] = []
    if "android" in runtime_triplet:
        subprocess.check_call([vcpkgexe, "install", "catch2:" + runtime_triplet], env=myenv, cwd=vcpkgroot)
        subprocess.check_call([vcpkgexe, "install", "dtl:" + runtime_triplet], env=myenv, cwd=vcpkgroot)

        cmakeconfigargs += [
            "-DCMAKE_TOOLCHAIN_FILE:PATH=" + myenv['ANDROID_NDK_HOME'] + "/build/cmake/android.toolchain.cmake",
            "-DANDROID=1",
            "-DANDROID_NATIVE_API_LEVEL=21",
            "-DANDROID_ABI=arm64-v8a"
        ]
        if runtime_triplet == "arm64-android":
            cmakeconfigargs += ["-DANDROID_ABI=arm64-v8a"]
        else:
            cmakeconfigargs += ["-DANDROID_ABI=armeabi-v7a"]
        if sys.platform == "win32":
            cmakeconfigargs += ["-G", "Ninja", f"-DCMAKE_MAKE_PROGRAM:FILEPATH={find_binary('ninja')}"]
    if "windows" in runtime_triplet:
        cmakeconfigargs += ["-G", "Visual Studio 17 2022", "-A", ("Win32" if "x86" in runtime_triplet else "x64")]
    ctestextraargs = (["-C", config] if sys.platform == "win32" else [])
    cmd: list[str] = [find_binary("cmake"),
                      f"-DCMAKE_BUILD_TYPE:STR={config}",
                      f"-DVCPKG_ROOT:PATH={vcpkgroot.as_posix()}",
                      f"-DVCPKG_HOST_TRIPLET:STR={host_triplet}",
                      f"-DVCPKG_TARGET_TRIPLET:STR={runtime_triplet}",
                      "-DVCPKG_VERBOSE:BOOL=ON"] + cmakeconfigargs + [
        (scriptdir / "sample").as_posix()]
    subprocess.check_call(cmd, cwd=testdir.as_posix())
    subprocess.check_call([find_binary("cmake"), "--build", ".", "-j"] + cmakebuildextraargs, cwd=testdir)
    if runtime_triplet == host_triplet:
        subprocess.check_call([find_binary("ctest"), ".", "--output-on-failure"] + ctestextraargs, cwd=testdir)


test_vcpkg_build("Debug", host_triplet, runtime_triplet, )
test_vcpkg_build("Release", host_triplet, runtime_triplet)
