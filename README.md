<p align="center">
  <img src="images/logo/plooi-logo.png" alt="PLOOI" height="64">
</p>

<p align="center"><b>PDF tools</b> · by Jesse Metz</p>

PLOOI is a small Windows program for everyday PDF jobs: merging, rearranging, rotating, splitting and turning images into PDF. Everything happens on your own computer; no files are uploaded anywhere.

## What it can do

**Merge & Edit PDF**
- Add one or more PDFs (button or drag them in from Explorer)
- Drag pages or whole files into a new order
- Rotate, delete or reverse pages; click a page to see it large
- Save as one PDF, every page separately, or a custom split such as `1-3; 4-end`

**Image to PDF**
- JPG, PNG, BMP, GIF, TIF, WEBP, AVIF and HEIC (iPhone photos)
- Rotate and reorder the images, then save as one PDF or one PDF per image

## Using it

The easiest way is the ready-made **PLOOI.exe**: double-click it, no installation or Python needed.
The first time, Windows may say *"Windows protected your PC"* because the program isn't signed. Click **More info** → **Run anyway**.

## Running from the source code

Needs Python 3.12 on Windows.

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python main.py
```

While working on the code, `python dev.py` restarts the program every time you save a `.py` file.

## Making PLOOI.exe

```bash
.venv\Scripts\python build_exe.py
```

After about two minutes the file is in `dist\PLOOI.exe`. Check it with `dist\PLOOI.exe --selftest result.txt` (should end with `OK`).

## Project structure

| Folder / file | What's in it |
|---|---|
| `main.py` | Starts the program |
| `src/gui/` | The window: screens, tiles, page viewer, notifications |
| `src/modify/`, `src/convert/` | The actual PDF and image work |
| `src/utils/` | Page previews and page-range helpers |
| `images/logo/` | Logo and icons; `tools/make_logo.py` makes them from `plooi-design.json` |
| `build_exe.py`, `PLOOI.spec` | Recipe for `PLOOI.exe` |

## License

PLOOI is free to use, share and change, under the [GNU AGPL-3.0](LICENSE).
Two things I ask:

- **Keep my name.** "PLOOI by Jesse Metz" must stay in the program and in its documentation, also in changed versions (see [NOTICE](NOTICE)).
- **Let me know!** Using PLOOI or building on it? I'd love to hear about it — send me a message via [GitHub](https://github.com/Jezzerrr).

Built with [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter), [pypdf](https://github.com/py-pdf/pypdf), [PyMuPDF](https://github.com/pymupdf/PyMuPDF) and [Pillow](https://python-pillow.org/).
