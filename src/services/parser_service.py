import requests
from requests.exceptions import RequestException
from pathlib import Path

from util.nfce_scrapper import NfceScrapper
from util.translators import NfceToWebmaniaTranslator


class ParserService:
    def __init__(self):
        self.scrapper = NfceScrapper(output_dir="output/nfce")
        self.translator = NfceToWebmaniaTranslator()

    def parse_qr(self, qr_value: str) -> dict:
        try:
            response = requests.get(qr_value, timeout=15)
            response.raise_for_status()
        except RequestException as exc:
            raise RuntimeError(f"Network error fetching QR URL: {exc}") from exc

        data, status = self.scrapper.scrape(qr_value)
        if status != "OK":
            raise ValueError(status)
        return self.translator.translate(data)

    def parse_image(self, image_path: str) -> dict:
        # Placeholder until third-party provider is integrated.
        return {
            "uuid": None,
            "status": "erro",
            "chave": None,
            "produtos": [],
            "image_path": image_path,
        }
