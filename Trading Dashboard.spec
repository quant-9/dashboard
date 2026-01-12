# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = ['PyQt6.QtWidgets', 'PyQt6.QtCore', 'PyQt6.QtGui', 'matplotlib.backends.backend_qtagg', 'pandas', 'numpy']
hiddenimports += collect_submodules('matplotlib')
hiddenimports += collect_submodules('pandas')


a = Analysis(
    ['ui_app.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Trading Dashboard',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Trading Dashboard',
)
app = BUNDLE(
    coll,
    name='Trading Dashboard.app',
    icon=None,
    bundle_identifier=None,
)
