"""Vercel Blob get function.

Fetches blob metadata from Vercel Blob storage via the vercel-blob library.
"""

import vercel_blob
from core.config import get_settings


def get(url: str, *, token: str | None = None) -> dict:  # type: ignore[type-arg]
    """Retrieve blob metadata for the given Vercel Blob URL.

    Args:
        url:   The publicly accessible Vercel Blob URL to look up.
        token: Optional explicit token. Falls back to BLOB_READ_WRITE_TOKEN
               from settings / .env, then to the vercel-blob library default.

    Returns:
        A dict containing blob metadata (url, downloadUrl, pathname,
        contentType, contentDisposition, size, uploadedAt, ...).

    Raises:
        vercel_blob.BlobRequestError: if the API returns an error response.
    """
    resolved_token = token or get_settings().blob_read_write_token
    options = {"token": resolved_token} if resolved_token else {}
    return vercel_blob.head(url, options=options)  # type: ignore[no-any-return]
