from __future__ import annotations

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class EmailClient:
    """Simple email client abstraction.

    - Dev: logs instead of sending
    - Prod: replace `send` with provider integration (SES/SendGrid/etc.)
    """

    def __init__(self, provider: str = "dev") -> None:
        self.provider = provider

    def send(self, to: str, subject: str, html: str, *, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if self.provider == "dev":
            logger.info("[DEV EMAIL] to=%s subject=%s meta=%s", to, subject, meta)
            return {"ok": True, "provider": "dev"}
        # Placeholder for real providers
        logger.warning("Email provider '%s' not implemented", self.provider)
        return {"ok": False, "error": "provider_not_implemented", "provider": self.provider}

