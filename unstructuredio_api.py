import os
import sys
if getattr(sys, 'frozen', False):
    # we are running in a bundle
    bundle_dir = sys._MEIPASS
else:
    # we are running in a normal Python environment
    bundle_dir = os.path.dirname(os.path.abspath(__file__))
os.environ['PATH'] = os.path.join(bundle_dir, 'tesseract') + os.pathsep + os.environ['PATH']
os.environ['PATH'] = os.path.join(bundle_dir, 'poppler', 'bin') + os.pathsep + os.environ['PATH']
os.environ['PATH'] = os.path.join(bundle_dir, 'pandoc') + os.pathsep + os.environ['PATH']
os.environ['PATH'] = os.path.join(bundle_dir, 'libreoffice', 'program') + os.pathsep + os.environ['PATH']
os.environ['PATH'] = os.path.join(bundle_dir, 'libreoffice') + os.pathsep + os.environ['PATH']

from pydantic_settings import BaseSettings, SettingsConfigDict
from prepline_general.api.app import app

class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    unstapi_port: int = 6989
    unstapi_host: str = "0.0.0.0"
    unstapi_workers: int = 1
    log_config: str = os.path.join("_internal", "config", "logger_config.yaml")


config = Config()

if __name__ == "__main__":
    import uvicorn

    # if os.name == "nt":
    from multiprocessing import freeze_support

    freeze_support()
    print("The system is Windows.")
    # else:
    #     print("The system is not Windows.")

    uvicorn.run(
        # "prepline_general.api.app:app",
        app,
        reload=False,
        port=config.unstapi_port,
        host=config.unstapi_host,
        workers=config.unstapi_workers,
        log_config=config.log_config,
    )
