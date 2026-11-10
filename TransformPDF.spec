# PyInstaller recipe for TransformPDF.exe. Use build_exe.py to run it.
import os
from PyInstaller.utils.hooks import collect_all, collect_data_files

DEBUG = os.environ.get("TRANSFORMPDF_DEBUG") == "1"
NAME = "TransformPDF-debug" if DEBUG else "TransformPDF"

datas = [
    ("images/logoTU.png", "images"),
    ("images/logoTU_icon.ico", "images"),
]
binaries = []
hiddenimports = []

datas += collect_data_files("customtkinter")
for package in ("tkinterdnd2", "pillow_heif"):
    d, b, h = collect_all(package)
    datas, binaries, hiddenimports = datas + d, binaries + b, hiddenimports + h

a = Analysis(
    ["main.py"],
    datas=datas,
    binaries=binaries,
    hiddenimports=hiddenimports,
    excludes=[
        # big packages in the .venv that the program doesn't use
        "matplotlib", "pandas", "numpy", "IPython", "jupyter_client", "ipykernel",
        "onnxruntime", "pymupdf4llm", "pymupdf_layout", "networkx",
    ],
    noarchive=False,
)

# Leave out pymupdf's developer files and layout models (~55 MB, not needed to render pages)
def needed(entry):
    path = entry[0].replace("\\", "/")
    return "pymupdf/mupdf-devel" not in path and "pymupdf/layout" not in path

a.datas = [entry for entry in a.datas if needed(entry)]
a.binaries = [entry for entry in a.binaries if needed(entry)]

pyz = PYZ(a.pure)

if DEBUG:
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name=NAME,
              icon="images/logoTU_icon.ico", console=True)
    coll = COLLECT(exe, a.binaries, a.datas, name=NAME)
else:
    # Splash screen: shown at once, while the .exe unpacks itself (takes a few seconds)
    splash = Splash("images/splash.png", binaries=a.binaries, datas=a.datas, text_pos=None, always_on_top=False)
    exe = EXE(pyz, a.scripts, splash, splash.binaries, a.binaries, a.datas, [], name=NAME,
              icon="images/logoTU_icon.ico", console=False, upx=False)
