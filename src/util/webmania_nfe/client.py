import logging
from typing import Optional

import requests

from .exceptions import (
    WebmaniaAuthError,
    WebmaniaNetworkError,
    WebmaniaNfeError,
    WebmaniaNotFoundError,
    WebmaniaValidationError,
)
from .models import DfeImageRequest

logger = logging.getLogger(__name__)


class WebmaniaNfeClient:
    """Client for the WebmaniaNFe validation API.

    Usage:
        from core.config import settings
        client = WebmaniaNfeClient(
            base_url=settings.NF_BASE_API,
            token=settings.NF_API_KEY,
        )
        result = client.validate_image(["https://example.com/nota.jpg"])
    """

    def __init__(self, base_url: str, token: str, timeout: int = 30):
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({
            "X-Token": self._token,
            "Content-Type": "application/json",
        })

    # ------------------------------------------------------------------
    # DFe Validation
    # ------------------------------------------------------------------

    def validate_image(
        self,
        image_urls: list[str],
        modelo: str = "nfe",
        antifraude: bool = False,
    ) -> dict:
        """POST /valida/dfe/imagem — Validate DFe from image URLs."""
        payload = DfeImageRequest(
            imagens=image_urls,
            modelo=modelo,
            antifraude=antifraude,
        )
        body = payload.model_dump(exclude_none=True)
        return self._post("/valida/dfe/imagem", json=body)

    def validate_xml(self, xml_content: str) -> dict:
        """POST /valida/dfe/xml — Validate DFe from XML."""
        return self._post("/valida/xml", json={"xml": xml_content})

    # ------------------------------------------------------------------
    # SERPRO Connections
    # ------------------------------------------------------------------

    def create_serpro_connection(
        self, consumer_key: str, consumer_secret: str
    ) -> dict:
        """POST /valida/conexoes/serpro — Register SERPRO credentials."""
        return self._post("/valida/conexoes/serpro", json={
            "consumer_key": consumer_key,
            "consumer_secret": consumer_secret,
        })

    def get_serpro_connection(self) -> dict:
        """GET /valida/conexoes/serpro — Check SERPRO connection status."""
        return self._get("/valida/conexoes/serpro")

    def delete_serpro_connection(self) -> dict:
        """DELETE /valida/conexoes/serpro — Remove SERPRO connection."""
        return self._delete("/valida/conexoes/serpro")

    # ------------------------------------------------------------------
    # Logs
    # ------------------------------------------------------------------

    def get_log(self, uuid: str) -> dict:
        """GET /valida/logs/{uuid} — Retrieve validation log by UUID."""
        return self._get(f"/valida/logs/{uuid}")

    # ------------------------------------------------------------------
    # Credits
    # ------------------------------------------------------------------

    def get_credits(self) -> dict:
        """GET /creditos — Check available credits balance."""
        return self._get("/creditos")

    def get_credit_recharges(self) -> dict:
        """GET /creditos/recargas — List credit recharge history."""
        return self._get("/creditos/recargas")

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    def _get(self, path: str) -> dict:
        return self._request("GET", path)

    def _post(self, path: str, json: dict = None) -> dict:
        return self._request("POST", path, json=json)

    def _delete(self, path: str) -> dict:
        return self._request("DELETE", path)

    def _request(self, method: str, path: str, **kwargs) -> dict:
        url = f"{self._base_url}{path}"
        logger.debug("%s %s", method, url)

        try:
            response = self._session.request(
                method, url, timeout=self._timeout, **kwargs
            )
        except requests.RequestException as exc:
            raise WebmaniaNetworkError(
                f"Network error on {method} {url}: {exc}"
            ) from exc

        return self._handle_response(response)

    def _handle_response(self, response: requests.Response) -> dict:
        status = response.status_code

        if status == 401 or status == 403:
            raise WebmaniaAuthError(
                f"Authentication failed ({status}): {response.text}"
            )

        if status == 404:
            raise WebmaniaNotFoundError(
                f"Resource not found: {response.url}"
            )

        try:
            data = response.json()
        except ValueError:
            if status >= 400:
                raise WebmaniaNfeError(
                    f"HTTP {status} with non-JSON body: {response.text[:200]}"
                )
            return {"raw": response.text}

        if status >= 400:
            msg = data.get("message", data.get("error", response.text[:200]))
            raise WebmaniaValidationError(f"API error ({status}): {msg}")

        return data
