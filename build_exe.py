"""
Build PLOOI.exe: one file that runs on Windows without Python.
Needs PyInstaller in the .venv (it is in requirements.txt).

    .venv\\Scripts\\python.exe build_exe.py           -> dist\\PLOOI.exe
    .venv\\Scripts\\python.exe build_exe.py --debug   -> dist\\PLOOI-debug\\ (folder, with console window)

The recipe is in PLOOI.spec. Check a build with:
    dist\\PLOOI.exe --selftest result.txt
"""
import os
import sys

import PyInstaller.__main__

if "--debug" in sys.argv:
    os.environ["TRANSFORMPDF_DEBUG"] = "1"

PyInstaller.__main__.run(["PLOOI.spec", "--noconfirm", "--clean"])
