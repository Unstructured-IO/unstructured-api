# Get Started

## Verified File Types
1. pptx/ppt
2. docx/doc
3. xlsx/xls
4. xml

## Setup Python
1. Install Ananconda or Install Python

2. Install LibreOffice
    * Install the full LibreOffice
    * Add the program to PATH. `Press "Windows" Key > Edit the system environment > Environment Variables > System variables > PATH > New > C:\Program Files\LibreOffice\program`

2. Setup python dependencies
    ```
    cd unstructured-api
    python -m pip install -r requirements/base.txt
    python -c "import nltk; nltk.download('punkt')"
    python -c "import nltk; nltk.download('averaged_perceptron_tagger')"
    ```

3. Launch the app
    ```
    python -m uvicorn prepline_general.api.app:app --reload --log-config logger_config.yaml
    ```

## Compile Executable

### Windows

1. Install LibreOffice
    - Install the full LibreOffice
    - Add the program to PATH. `Press "Windows" Key > Edit the system environment > Environment Variables > System variables > PATH > New > C:\Program Files\LibreOffice\program`
2. Create a python virtual environment
3. Run the following commands.
    ```powershell
    cd <path/to/repo/>
    python -m pip install -r requirements/win-base.txt // uvloop does not support Windows
    python -c "import nltk; nltk.download('punkt', download_dir='nltk_data')"
    python -c "import nltk; nltk.download('averaged_perceptron_tagger', download_dir='nltk_data')"
    pip install httpx htmlBuilder
    ```
4. Download `sqlite3.dll` as a patch from [link](https://www.sqlite.org/download.html). Download [sqlite-dll-win-x64-3460000.zip](https://www.sqlite.org/2024/sqlite-dll-win-x64-3460000.zip). Somehow python native `sqlite3` does not work. Place it at the root of repository. Unzip the zip file. 
5.  Convert the unstructuredioapi repo into a python package by updating the `pyproject.toml`
      ```pyproject.toml
      [build-system]
      # setuptools-scm considers all files tracked by git to be data files
      requires = ["setuptools>=62.0", "setuptools-scm"]
      build-backend = "setuptools.build_meta"
      
      [project]
      name = "prepline_general"
      description = "UnstructuredIO API"
      readme = "README.md"
      requires-python = "~=3.10"
      # keywords = ["one", "two"]
      license = { text = "Proprietary" }
      classifiers = [ # https://pypi.org/classifiers/
          "Development Status :: 3 - Alpha",
          "Programming Language :: Python :: 3 :: Only",
          "Intended Audience :: Information Technology",
          "Operating System :: Unix",
      ]
      version="0.0.68"
      
      [tool.black]
      line-length = 100
      
      [tool.pyright]
      pythonPlatform = "Linux"
      pythonVersion = "3.9"
      reportUnnecessaryCast = true
      typeCheckingMode = "strict"
      
      [tool.ruff]
      line-length = 100
      select = [
          "C4",       # -- flake8-comprehensions --
          "COM",      # -- flake8-commas --
          "E",        # -- pycodestyle errors --
          "F",        # -- pyflakes --
          "I",        # -- isort (imports) --
          "PLR0402",  # -- Name compared with itself like `foo == foo` --
          "PT",       # -- flake8-pytest-style --
          "SIM",      # -- flake8-simplify --
          "UP015",    # -- redundant `open()` mode parameter (like "r" is default) --
          "UP018",    # -- Unnecessary {literal_type} call like `str("abc")`. (rewrite as a literal) --
          "UP032",    # -- Use f-string instead of `.format()` call --
          "UP034",    # -- Avoid extraneous parentheses --
      ]
      ignore = [
          "COM812",   # -- over aggressively insists on trailing commas where not desireable --
          "PT011",    # -- pytest.raises({exc}) too broad, use match param or more specific exception --
          "PT012",    # -- pytest.raises() block should contain a single simple statement --
          "SIM117",   # -- merge `with` statements for context managers that have same scope --
      ]
      
      [tool.ruff.lint.isort]
      known-first-party = [
          "unstructured",
          "unstructured_inference",
      ]
      
      [tool.setuptools.packages.find]
      where = ["."]
      ```
6. Install the repo as a package. `python -m pip install -e . `
7. Create a pyinstaller spec file called `unstructured_api.spec` with following content. Modify the variables based on the comments found in the spec file.
    ```unstructuredio_api.spec
    # -*- mode: python ; coding: utf-8 -*-

    import os
    from pathlib import Path
    import sys
    from PyInstaller.utils.hooks import collect_all

    binaries_list = [
        ('C:\\Program Files\\LibreOffice\\program', 'libreoffice'), # modify this to point to where the LibreOffice is installed
        (Path('sqlite-dll-win-x64-3460000/sqlite3.dll').as_posix(), '.'), # modify this to point to where you unzip the sqlite3.dll
        (Path('sqlite-dll-win-x64-3460000/sqlite3.def').as_posix(), '.'), # modify this to point to where you unzip the sqlite3.def

    ]

    datas_list = [
        (Path('logger_config.yaml').as_posix(), 'config'), # modify this to point to where the repo is
        (Path('nltk_data').as_posix(), 'nltk_data') # modify this to point to where nltk download the nltk data
    ]

    hiddenimports_list = []

    def add_package(package_name):
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
        debug=False,
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
    ```
8. Create a `unstructuredio_api.py` file
    ```python
    import uvicorn
    import os
    
    if __name__ == "__main__":
        uvicorn.run(
            "prepline_general.api.app:app",
            port=6989,
            host="0.0.0.0",
            log_config=os.path.join("_internal", "config", "logger_config.yaml")
        )
    ```
9. Remove relative path with absolute path.
   - `prepline_general/api/app.py`
    ```python
    ...

    #from .general import router as general_router
    #from .openapi import set_custom_openapi

    from prepline_general.api.general import router as general_router
    from prepline_general.api.openapi import set_custom_openapi
    ...
    ```
9. Install pyinstaller. `pip install pyinstaller`
10. Start packaging. `pyinstaller .\unstructuredio_api.spec`
