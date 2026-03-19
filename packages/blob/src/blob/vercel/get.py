"""Vercel Blob get function.

Fetches blob metadata from Vercel Blob storage via the vercel-blob library.
"""

import vercel_blob
from core.config import get_settings
from vercel_blob import blob_store


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


def get_bytes(url: str, *, token: str | None = None, timeout: int = 30) -> bytes:
    """Download blob contents in-memory using the vercel-blob client internals.

    This avoids the current `vercel_blob.download_file()` behavior that writes to
    disk and does not return the file bytes.
    """
    resolved_token = token or get_settings().blob_read_write_token

    headers = {"x-api-version": blob_store._API_VERSION}
    if resolved_token:
        headers["authorization"] = f"Bearer {resolved_token}"

    resp = blob_store._request_factory(
        f"{url}?download=1",
        "GET",
        headers=headers,
        timeout=timeout,
    )

    if resp is None:
        raise vercel_blob.BlobRequestError("Request failed after retries. Please try again.")

    if resp.status_code != 200:
        raise vercel_blob.BlobRequestError(
            f"Failed to download file from {url}. HTTP status: {resp.status_code}"
        )

    return resp.content
