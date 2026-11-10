import sys


def close_splash():
    """Close the splash screen of the packaged .exe (does nothing when run with Python)."""
    try:
        import pyi_splash
        pyi_splash.close()
    except ImportError:
        pass


if len(sys.argv) >= 3 and sys.argv[1] == "--selftest":
    close_splash()
    from src.selftest import run_selftest
    run_selftest(sys.argv[2])
    sys.exit()

from src.gui.app import PDFToolApp

app = PDFToolApp()
close_splash()
app.run()
