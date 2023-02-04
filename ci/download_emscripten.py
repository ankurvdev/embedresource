import pathlib
import shutil
import sys
import subprocess
import os


class Info:
    def __init__(self, sdkpath: pathlib.Path, envvars:  dict[str: str], paths: list[str | pathlib.Path]):
        self.sdkpath = sdkpath
        self.envvars = envvars
        self.paths = set([pathlib.Path(pathlike).absolute() for pathlike in paths])
        self.cmake_toolchain_file = sdkpath/"upstream"/"emscripten"/"cmake"/"Modules"/"Platform"/"Emscripten.cmake"


def DownloadTo(path: pathlib.Path):
    path.mkdir(exist_ok=True, parents=True)
    sdkpath = path
    emconfig = sdkpath / ".emscripten"
    git = shutil.which('git')
    if not emconfig.exists():
        script = sdkpath/"emsdk.bat" if sys.platform == "win32" else sdkpath/"emsdk"
        if not script.exists():
            subprocess.check_call(["git", "clone", "https://github.com/emscripten-core/emsdk.git", sdkpath])
        subprocess.check_call(f"{script.as_posix()} install latest", shell=True, cwd=sdkpath)
        subprocess.check_call(f"{script.as_posix()} activate latest", shell=True, cwd=sdkpath)
    os.environ['EM_CONFIG'] = emconfig.as_posix()
    _globals = {}
    _locals = {}
    exec(emconfig.read_text(encoding='utf-8'), _globals, _locals)
    return Info(sdkpath,
                {"EMSDK": sdkpath.as_posix(), "EMSDK_NODE": _locals["NODE_JS"], },
                [pathlib.Path(_locals["NODE_JS"]).parent, sdkpath, _locals["LLVM_ROOT"], _locals["BINARYEN_ROOT"], _locals["EMSCRIPTEN_ROOT"]])


if __name__ == "__main__":
    DownloadTo(pathlib.Path(sys.argv[1]))
