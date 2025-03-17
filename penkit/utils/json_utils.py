"""JSON utilities for PenKit."""

import json
import datetime
from typing import Any


class PenKitJSONEncoder(json.JSONEncoder):
    """JSON encoder that can handle datetime objects."""

    def default(self, obj: Any) -> Any:
        """Handle special objects like datetime.

        Args:
            obj: Object to encode

        Returns:
            JSON-serializable representation
        """
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        elif isinstance(obj, datetime.date):
            return obj.isoformat()
        return super().default(obj)
