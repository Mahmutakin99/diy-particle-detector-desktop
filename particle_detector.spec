# PyInstaller entry point; build it on each target OS/CPU, never cross-compile.
a = Analysis(["desktop_app.py"], pathex=["."], binaries=[], datas=[], hiddenimports=["sounddevice"], hookspath=[])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, name="DIY Particle Detector", console=False)
