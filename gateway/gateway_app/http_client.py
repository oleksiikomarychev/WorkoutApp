"""Re-export from backend_common for backwards compatibility."""

from backend_common.http_client import ServiceClient, ServiceResponse

__all__ = ["ServiceClient", "ServiceResponse"]
