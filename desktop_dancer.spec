# PyInstaller spec for desktop-dancer.
# Build:  pyinstaller desktop_dancer.spec
# Output: dist/desktop-dancer.exe (Windows) or dist/desktop-dancer (macOS/Linux)
import os

block_cipher = None

# Bundle every clip we have. Skip ones that haven't been rendered yet so a
# fresh checkout still builds before someone runs the matting pipeline.
_CLIPS = ['dance_loop.webp', 'new_loop.webp', 'sakura_loop.webp']
clip_datas = [(c, '.') for c in _CLIPS if os.path.exists(c)]

a = Analysis(
    ['desktop_dancer.py'],
    pathex=[],
    binaries=[],
    datas=clip_datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'numpy', 'torch', 'torchvision',
        'matplotlib', 'pandas', 'scipy', 'IPython',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='desktop-dancer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
