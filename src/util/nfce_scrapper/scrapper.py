import json
import logging
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests

from .exceptions import (
    NfceInvalidUrlError,
    NfceNetworkError,
    NfceNotFoundError,
    NfceScrapperError,
)
from .parser import NfceParser

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Set to DEBUG for detailed trace

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Referer": "https://www.nfce.fazenda.sp.gov.br/",
}

_RE_44_DIGITS = re.compile(r"^\d{44}$")


class NfceScrapper:
    def __init__(self, timeout: int = 30, output_dir: str = ""):
        self._timeout = timeout
        self._output_dir = Path(output_dir) if output_dir is not None and len(output_dir) > 0 else None
        self._session = requests.Session()
        self._session.headers.update(_HEADERS)

    def scrape(self, url: str) -> tuple[dict, str]:
        """Scrape an NFC-e public consultation page.

        Returns:
            (data_dict, "OK") on success.
            ({}, error_message) on any failure. Never raises.
        """
        try:
            self._validate_url(url)
            html = self._fetch_html(url)
            parser = NfceParser(html, url)
            data = parser.parse()
            data_dict = json.loads(data.model_dump_json())
            if self._output_dir is not None:
                self._save_json(data_dict)
            return data_dict, "OK"
        except NfceScrapperError as exc:
            logger.warning("NfceScrapperError for %s: %s", url, exc)
            return {}, str(exc)
        except Exception as exc:
            logger.exception("Unexpected error scraping %s", url)
            return {}, f"Unexpected error: {exc}"

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_url(self, url: str) -> None:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise NfceInvalidUrlError(f"Invalid URL (missing scheme or host): {url}")

        qs = parse_qs(parsed.query)
        if "p" not in qs:
            raise NfceInvalidUrlError("URL missing required query param 'p'")

        p_value = qs["p"][0]
        segments = p_value.split("|")
        if len(segments) < 2:
            raise NfceInvalidUrlError(
                f"Param 'p' must have at least 2 pipe-separated segments, got {len(segments)}"
            )

        first_segment = segments[0].strip()
        if not _RE_44_DIGITS.match(first_segment):
            raise NfceInvalidUrlError(
                f"First segment of 'p' must be 44 digits, got: {first_segment!r}"
            )

    # ------------------------------------------------------------------
    # HTTP
    # ------------------------------------------------------------------

    def _fetch_html(self, url: str) -> str:
        try:
            response = self._session.get(url, timeout=self._timeout)
            response.encoding = response.apparent_encoding
            if response.status_code >= 400:
                raise NfceNotFoundError(
                    f"HTTP {response.status_code} for URL: {url}"
                )
            return response.text
        except NfceNotFoundError:
            raise
        except requests.RequestException as exc:
            raise NfceNetworkError(f"Network error fetching {url}: {exc}") from exc

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------

    def _save_json(self, data: dict) -> Path:
        access_key = data.get("access_key", "")
        clean_key = re.sub(r"\s+", "", access_key)

        if clean_key and _RE_44_DIGITS.match(clean_key):
            filename = f"{clean_key}.json"
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"nfce_{timestamp}.json"

        self._output_dir.mkdir(parents=True, exist_ok=True)
        out_path = self._output_dir / filename

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

        logger.info("Saved NFC-e data to %s", out_path)
        return out_path


if __name__ == "__main__":
    # Example: How to use the NfceScrapper class

    # Initialize scraper with output directory
    scraper = NfceScrapper(output_dir="output/nfce", timeout=30)

    # Example NFC-e URLs
    urls = [
        "https://www.nfce.fazenda.sp.gov.br/NFCeConsultaPublica/Paginas/ConsultaQRCode.aspx?p=35260243283811004732650010001055941001056011|2|1|1|311111C4E7BB56B70DD3C25F25F29300E2E6AFB5",
        "https://www.nfce.fazenda.sp.gov.br/qrcode?p=35260347508411227878651020005420661644227626|3|1",
    ]

    # Scrape each URL
    for url in urls:
        print(f"\nScraping: {url[:60]}...")

        # Scrape and get data and status
        data, status = scraper.scrape(url)

        if status == "OK":
            # Display scraped information
            seller = data.get("seller", {})
            print(f"[OK] Seller: {seller.get('name', 'Unknown')}")
            print(f"     CNPJ: {seller.get('cnpj', 'N/A')}")

            invoice = data.get("invoice_number", "N/A")
            series = data.get("series", "N/A")
            print(f"     Invoice: {invoice} | Series: {series}")

            totals = data.get("totals", {})
            print(f"     Total: R$ {totals.get('total', 'N/A')}")

            # Display items
            items = data.get("items", [])
            if items:
                print(f"     Items ({len(items)}):")
                for item in items:
                    qty = item.get("quantity")
                    name = item.get("description", "Unknown")[:40]
                    price = item.get("total_price")
                    unit = item.get("unit", "UN")
                    print(f"       - {qty} {unit} x {name}... = R$ {price}")
        else:
            # Display error
            print(f"[ERROR] {status}")
