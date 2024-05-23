from __future__ import annotations

import logging
from types import TracebackType
from typing import Optional

from fastapi import HTTPException

logger = logging.getLogger("unstructured_api")


is_chipper_processing = False


class ChipperMemoryProtection:
    """Chipper calls are expensive, and right now we can only do one call at a time.

    If the model is in use, return a 503 error. The API should scale up and the user can try again
    on a different server.
    """

    def __enter__(self):
        global is_chipper_processing
        if is_chipper_processing:
            # Log here so we can track how often it happens
            logger.error("Chipper is already is use")
            raise HTTPException(
                status_code=503, detail="Server is under heavy load. Please try again later."
            )

        is_chipper_processing = True

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_value: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ):
        global is_chipper_processing
        is_chipper_processing = False
