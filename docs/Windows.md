# Get Started

## Verified File Types

1. pptx/ppt
2. docx/doc
3. xlsx/xls
4. xml
5. csv
6. eml
7. epub
8. html
9. jpg
10. json
11. md
12. msg
13. odt
14. rst
15. rtf
16. txt
17. tsv

## Setup Python

1. Install Ananconda or Install Python

2. Install LibreOffice

    - Install the full LibreOffice
    - Add the program to PATH. `Press "Windows" Key > Edit the system environment > Environment Variables > User variables > PATH > New > C:\Program Files\LibreOffice\program`

3. Install Pandoc on Windows 11, you can follow these steps:
    - Visit the official Pandoc download page: https://pandoc.org/installing.html
    - Scroll down to the "Windows" section and click on the latest installer link (it should be an .msi file).

    - Once the installer is downloaded, double-click on it to run it.

    - Follow the installation wizard, accepting the default options unless you have a specific reason to change them.

    - Add the program to PATH. `Press "Windows" Key > Edit the system environment > Environment Variables > User variables > PATH > New > C:\Program Files\Pandoc` (typically `C:\Program Files\Pandoc`)

    - To verify the installation, open a new Command Prompt and type: pandoc --version

    If Pandoc is correctly installed and added to your PATH, you should see version information displayed.

    After completing these steps, Pandoc should be properly installed and accessible from your system, resolving the error you encountered.

4. Install Tesseract

    - Go to [link](https://github.com/UB-Mannheim/tesseract/wiki) to download the exe.
    - Add the program to PATH. `Press "Windows" Key > Edit the system environment > Environment Variables > User variables > PATH > New > C:\Program Files\Tesseract-OCR`

5. Setup python dependencies

    ```
    cd <path/to/repo/>
    python -m pip install -r requirements/win-base.txt // uvloop does not support Windows
    python -c "import nltk; nltk.download('punkt', download_dir='nltk_data')"
    python -c "import nltk; nltk.download('averaged_perceptron_tagger', download_dir='nltk_data')"
    pip install httpx htmlBuilder pydantic_settings
    ```

6. Launch the app
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
    pip install httpx htmlBuilder pydantic_settings python-magic-bin
    ```
4. Download `sqlite3.dll` as a patch from [link](https://www.sqlite.org/download.html). Download [sqlite-dll-win-x64-3460000.zip](https://www.sqlite.org/2024/sqlite-dll-win-x64-3460000.zip). Somehow python native `sqlite3` does not work. Place it at the root of repository. Unzip the zip file.
5. Convert the unstructuredioapi repo into a python package by updating the `pyproject.toml`

    <details>
    <summary>pyproject.toml</summary>
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
    version="0.0.72-post1"

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
    </details>
    
6. Install the repo as a package. `python -m pip install -e . `
7. Create a pyinstaller spec file called `unstructured_api.spec` with following content. Modify the variables based on the comments found in the spec file.

    <details>
    <summary>unstructuredio_api.spec</summary>
        ```unstructuredio_api.spec
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
        ```
    </details>

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

10. Install pyinstaller. `pip install pyinstaller`
11. Start packaging. `pyinstaller .\unstructuredio_api.spec`

### Validate the packaged environment
1. Run the executable:
    `cd dist/unstructuredio_api; .\unstructuredio_api.exe`.
2. Run local test `python test_scripts/test_app.py`.


## FAQ
<details>
<summary>1. Why unstructured cannot load pdf?</summary>
    ```
    2024-07-10 20:59:51,313 127.0.0.1:60143 POST /general/v0/general HTTP/1.1 - 500 Internal Server Error
    2024-07-10 20:59:51,313 uvicorn.error ERROR Exception in ASGI application
    Traceback (most recent call last):
    File "C:\Users\ryzz\anaconda3\envs\unstwin\lib\site-packages\pdf2image\pdf2image.py", line 581, in pdfinfo_from_path
        proc = Popen(command, env=env, stdout=PIPE, stderr=PIPE)
    File "C:\Users\ryzz\anaconda3\envs\unstwin\lib\subprocess.py", line 971, in __init__
        self._execute_child(args, executable, preexec_fn, close_fds,
    File "C:\Users\ryzz\anaconda3\envs\unstwin\lib\subprocess.py", line 1456, in _execute_child
        hp, ht, pid, tid = _winapi.CreateProcess(executable, args,
    FileNotFoundError: [WinError 2] The system cannot find the file specified

    During handling of the above exception, another exception occurred:

    Traceback (most recent call last):
    File "C:\Users\ryzz\anaconda3\envs\unstwin\lib\site-packages\uvicorn\protocols\http\httptools_impl.py", line 399, in run_asgi
        result = await app(  # type: ignore[func-returns-value]
    File "C:\Users\ryzz\anaconda3\envs\unstwin\lib\site-packages\uvicorn\middleware\proxy_headers.py", line 70, in __call__
        return await self.app(scope, receive, send)
    File "C:\Users\ryzz\anaconda3\envs\unstwin\lib\site-packages\fastapi\applications.py", line 1054, in __call__
        await super().__call__(scope, receive, send)
    File "C:\Users\ryzz\anaconda3\envs\unstwin\lib\site-packages\starlette\applications.py", line 123, in __call__
        await self.middleware_stack(scope, receive, send)
    File "C:\Users\ryzz\anaconda3\envs\unstwin\lib\site-packages\starlette\middleware\errors.py", line 186, in __call__
        raise exc
    File "C:\Users\ryzz\anaconda3\envs\unstwin\lib\site-packages\starlette\middleware\errors.py", line 164, in __call__
        await self.app(scope, receive, _send)
    File "C:\Users\ryzz\anaconda3\envs\unstwin\lib\site-packages\starlette\middleware\exceptions.py", line 65, in __call__
        await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
    File "C:\Users\ryzz\anaconda3\envs\unstwin\lib\site-packages\starlette\_exception_handler.py", line 64, in wrapped_app
        raise exc
    File "C:\Users\ryzz\anaconda3\envs\unstwin\lib\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
        await app(scope, receive, sender)
    File "C:\Users\ryzz\anaconda3\envs\unstwin\lib\site-packages\starlette\routing.py", line 756, in __call__
        await self.middleware_stack(scope, receive, send)
    File "C:\Users\ryzz\anaconda3\envs\unstwin\lib\site-packages\starlette\routing.py", line 776, in app
        await route.handle(scope, receive, send)
    File "C:\Users\ryzz\anaconda3\envs\unstwin\lib\site-packages\starlette\routing.py", line 297, in handle
        await self.app(scope, receive, send)
    File "C:\Users\ryzz\anaconda3\envs\unstwin\lib\site-packages\starlette\routing.py", line 77, in app
        await wrap_app_handling_exceptions(app, request)(scope, receive, send)
    File "C:\Users\ryzz\anaconda3\envs\unstwin\lib\site-packages\starlette\_exception_handler.py", line 64, in wrapped_app
        raise exc
    File "C:\Users\ryzz\anaconda3\envs\unstwin\lib\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
        await app(scope, receive, sender)
    File "C:\Users\ryzz\anaconda3\envs\unstwin\lib\site-packages\starlette\routing.py", line 72, in app
        response = await func(request)
    File "C:\Users\ryzz\anaconda3\envs\unstwin\lib\site-packages\fastapi\routing.py", line 278, in app
        raw_response = await run_endpoint_function(
    File "C:\Users\ryzz\anaconda3\envs\unstwin\lib\site-packages\fastapi\routing.py", line 193, in run_endpoint_function
        return await run_in_threadpool(dependant.call, **values)
    File "C:\Users\ryzz\anaconda3\envs\unstwin\lib\site-packages\starlette\concurrency.py", line 42, in run_in_threadpool
        return await anyio.to_thread.run_sync(func, *args)
    File "C:\Users\ryzz\anaconda3\envs\unstwin\lib\site-packages\anyio\to_thread.py", line 56, in run_sync
        return await get_async_backend().run_sync_in_worker_thread(
    File "C:\Users\ryzz\anaconda3\envs\unstwin\lib\site-packages\anyio\_backends\_asyncio.py", line 2177, in run_sync_in_worker_thread
        return await future
    File "C:\Users\ryzz\anaconda3\envs\unstwin\lib\site-packages\anyio\_backends\_asyncio.py", line 859, in run
        result = context.run(func, *args)
    File "C:\Users\ryzz\VDrive\git\unstructured-api-executable\prepline_general\api\general.py", line 788, in general_partition
        list(response_generator(is_multipart=False))[0]
    File "C:\Users\ryzz\VDrive\git\unstructured-api-executable\prepline_general\api\general.py", line 723, in response_generator
        response = pipeline_api(
    File "C:\Users\ryzz\VDrive\git\unstructured-api-executable\prepline_general\api\general.py", line 420, in pipeline_api
        elements = partition(**partition_kwargs)  # type: ignore # pyright: ignore[reportGeneralTypeIssues]
    File "C:\Users\ryzz\anaconda3\envs\unstwin\lib\site-packages\unstructured\partition\auto.py", line 426, in partition
        elements = _partition_pdf(
    File "C:\Users\ryzz\anaconda3\envs\unstwin\lib\site-packages\unstructured\documents\elements.py", line 591, in wrapper
        elements = func(*args, **kwargs)
    File "C:\Users\ryzz\anaconda3\envs\unstwin\lib\site-packages\unstructured\file_utils\filetype.py", line 618, in wrapper
        elements = func(*args, **kwargs)
    File "C:\Users\ryzz\anaconda3\envs\unstwin\lib\site-packages\unstructured\file_utils\filetype.py", line 582, in wrapper
        elements = func(*args, **kwargs)
    File "C:\Users\ryzz\anaconda3\envs\unstwin\lib\site-packages\unstructured\chunking\dispatch.py", line 74, in wrapper
        elements = func(*args, **kwargs)
    File "C:\Users\ryzz\anaconda3\envs\unstwin\lib\site-packages\unstructured\partition\pdf.py", line 192, in partition_pdf
        return partition_pdf_or_image(
    File "C:\Users\ryzz\anaconda3\envs\unstwin\lib\site-packages\unstructured\partition\pdf.py", line 288, in partition_pdf_or_image
        elements = _partition_pdf_or_image_local(
    File "C:\Users\ryzz\anaconda3\envs\unstwin\lib\site-packages\unstructured\utils.py", line 245, in wrapper
        return func(*args, **kwargs)
    File "C:\Users\ryzz\anaconda3\envs\unstwin\lib\site-packages\unstructured\partition\pdf.py", line 591, in _partition_pdf_or_image_local
        inferred_document_layout = process_data_with_model(
    File "C:\Users\ryzz\anaconda3\envs\unstwin\lib\site-packages\unstructured_inference\inference\layout.py", line 334, in process_data_with_model
        layout = process_file_with_model(
    File "C:\Users\ryzz\anaconda3\envs\unstwin\lib\site-packages\unstructured_inference\inference\layout.py", line 371, in process_file_with_model
        else DocumentLayout.from_file(
    File "C:\Users\ryzz\anaconda3\envs\unstwin\lib\site-packages\unstructured_inference\inference\layout.py", line 62, in from_file
        _image_paths = convert_pdf_to_image(
    File "C:\Users\ryzz\anaconda3\envs\unstwin\lib\site-packages\unstructured_inference\inference\layout.py", line 395, in convert_pdf_to_image
        images = pdf2image.convert_from_path(
    File "C:\Users\ryzz\anaconda3\envs\unstwin\lib\site-packages\pdf2image\pdf2image.py", line 127, in convert_from_path
        page_count = pdfinfo_from_path(
    File "C:\Users\ryzz\anaconda3\envs\unstwin\lib\site-packages\pdf2image\pdf2image.py", line 607, in pdfinfo_from_path
        raise PDFInfoNotInstalledError(
    pdf2image.exceptions.PDFInfoNotInstalledError: Unable to get page count. Is poppler installed and in PATH?

    ```
</details>

Answer:

- Go to `C:\Users\ryzz\anaconda3\envs\unstwin\Lib\site-packages\unstructured\partition\pdf_image\ocr.py`
    Modify the function `process_data_with_ocr` to 
    ```python
        with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_file_path = os.path.join(tmp_dir, 'temp_file')

        with open(tmp_file_path, 'wb') as tmp_file:
            data_bytes = data if isinstance(data, bytes) else data.read()
            tmp_file.write(data_bytes)

        merged_layouts = process_file_with_ocr(
            filename=tmp_file_path,
            out_layout=out_layout,
            extracted_layout=extracted_layout,
            is_image=is_image,
            infer_table_structure=infer_table_structure,
            ocr_languages=ocr_languages,
            ocr_mode=ocr_mode,
            pdf_image_dpi=pdf_image_dpi,
        )
        return merged_layouts
    ```
- Go to `C:\Users\ryzz\anaconda3\envs\unstwin\Lib\site-packages\unstructured_inference\inference\layout.py`
    Modify the function `process_data_with_model` to 
    ```python
    def process_data_with_model(
        data: BinaryIO,
        model_name: Optional[str],
        **kwargs,
    ) -> DocumentLayout:
        """Processes pdf file in the form of a file handler (supporting a read method) into a
        DocumentLayout by using a model identified by model_name."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_file_path = os.path.join(tmp_dir, 'temp_file')

            with open(tmp_file_path, 'wb') as tmp_file:
                tmp_file.write(data.read())

            layout = process_file_with_model(
                tmp_file_path,
                model_name,
                **kwargs,
            )

        return layout
    ```
- Download poppler from `https://github.com/oschwartz10612/poppler-windows`'s Releases.
    - Unzip Poppler.
    - Add the program to PATH. `Press "Windows" Key > Edit the system environment > Environment Variables > User variables > PATH > New > C:\path\to\poppler-23.08.0\Library\bin`

<details>
<summary>2. tesseract not found.</summary>
</details>

Answer: 
- Go to [link](https://github.com/UB-Mannheim/tesseract/wiki) to download the exe.
- Add the program to PATH. `Press "Windows" Key > Edit the system environment > Environment Variables > User variables > PATH > New > C:\Program Files\Tesseract-OCR`



<details>
<summary>3. Pandoc is not installed error </summary>
2024-07-10 21:32:05,126 unstructured_api ERROR No pandoc was found: either install pandoc and add it
to your PATH or or call pypandoc.download_pandoc(...) or
install pypandoc wheels with included pandoc.
2024-07-10 21:32:05,126 127.0.0.1:60824 POST /general/v0/general HTTP/1.1 - 500 Internal Server Error
</details>

Answer:
- Install Pandoc on Windows 11, you can follow these steps:
    - Visit the official Pandoc download page: https://pandoc.org/installing.html
    - Scroll down to the "Windows" section and click on the latest installer link (it should be an .msi file).

- Once the installer is downloaded, double-click on it to run it.

- Follow the installation wizard, accepting the default options unless you have a specific reason to change them.

- After the installation is complete, you need to add Pandoc to your system's PATH. To do this: a. Press the Windows key and search for "Environment Variables" b. Click on "Edit the system environment variables" c. In the System Properties window, click on "Environment Variables" d. Under "System variables", find and select the "Path" variable, then click "Edit" e. Click "New" and add the path to the Pandoc installation directory (typically C:\Program Files\Pandoc) f. Click "OK" to close all the windows

- To verify the installation, open a new Command Prompt and type: pandoc --version

If Pandoc is correctly installed and added to your PATH, you should see version information displayed.

After completing these steps, Pandoc should be properly installed and accessible from your system, resolving the error you encountered.

<details>
<summary>4. Pandoc RuntimeError.</summary>
RuntimeError: Pandoc died with exitcode "1" during conversion: pandoc: C:\Users\ryzz\AppData\Local\Temp\tmp3u5zs1yq: withBinaryFile: permission denied (Permission denied)
</details>

Answer:
- Go to `C:\Users\ryzz\anaconda3\envs\unstwin\Lib\site-packages\unstructured\file_utils\file_conversion.py`
- Modify the function `convert_file_to_html_text` to 
    ```python
    def convert_file_to_html_text(
        source_format: str,
        filename: Optional[str] = None,
        file: Optional[IO[bytes]] = None,
    ) -> str:
        """Converts a document to HTML raw text. Enables the document to be
        processed using the partition_html function."""
        exactly_one(filename=filename, file=file)

        if file is not None:
            with tempfile.TemporaryDirectory() as temp_dir:
                import os
                temp_file_path = os.path.join(temp_dir, "temp_file")
                with open(temp_file_path, 'wb') as tmp:
                    tmp.write(file.read())

                html_text = convert_file_to_text(
                    filename=temp_file_path,
                    source_format=source_format,
                    target_format="html",
                )
        elif filename is not None:
            html_text = convert_file_to_text(
                filename=filename,
                source_format=source_format,
                target_format="html",
            )

        return html_text
    ```