# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path
import sys
import unstructured
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_dynamic_libs

binaries_list = [
    ('C:\\Program Files\\LibreOffice\\program', 'libreoffice'), # modify this to point to where the LibreOffice is installed
    ('C:\\path\\to\\poppler-24.02.0\\Library\\bin', 'poppler/bin'), # modify this to point to where the poppler is installed
    ('C:\\Program Files\\Tesseract-OCR', 'tesseract'), # modify this to point to where the tesseract is installed
    ('C:\\Users\\ryzz\\AppData\\Local\\Pandoc', 'pandoc'), # modify this to point to where the pandoc is installed
    (Path('sqlite-dll-win-x64-3460000/sqlite3.dll').as_posix(), '.'), # modify this to point to where you unzip the sqlite3.dll
    (Path('sqlite-dll-win-x64-3460000/sqlite3.def').as_posix(), '.'), # modify this to point to where you unzip the sqlite3.def

]

datas_list = [
    (Path('logger_config.yaml').as_posix(), 'config'), # modify this to point to where the repo is
    (Path('nltk_data').as_posix(), 'nltk_data') # modify this to point to where nltk download the nltk data
]

# datas_list.extend(collect_data_files('unstructured'))
datas_list.extend(collect_data_files('pytesseract'))
# hiddenimports_list = ['unstructured']
hiddenimports_list = []

def add_package(package_name):
    print(f"Add Package {package_name}")
    datas, binaries, hiddenimports = collect_all(package_name)
    datas_list.extend(datas)
    binaries_list.extend(binaries)
    hiddenimports_list.extend(hiddenimports)

# Collect all resources from the package_name
add_package('unstructured')
add_package('effdet')
add_package('onnxruntime')
add_package('encodings')
add_package('prepline_general')
binaries_list.extend(collect_dynamic_libs('pdf2image'))
binaries_list.extend(collect_dynamic_libs('pytesseract'))

print(len(datas_list))

a = Analysis(
    [Path('unstructuredio_api.py').as_posix()],
    pathex=[],
    binaries=binaries_list,
    datas=datas_list,
    hiddenimports=hiddenimports_list,
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
    name='unstructuredio_api',
    debug=True,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
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
    name='unstructuredio_api',
)