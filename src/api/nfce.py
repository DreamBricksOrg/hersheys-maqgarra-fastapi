import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from util.nfce_scrapper import NfceScrapper
from util.translators.nfce_to_webmania import NfceToWebmaniaTranslator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/nfce", tags=["NFCe - Scrapper"])

scrapper = NfceScrapper(timeout=30)
translator = NfceToWebmaniaTranslator()


class ScrapeRequest(BaseModel):
    url: str


@router.post("/scrape", summary="Scrape e traduz NFC-e a partir de URL")
async def scrape_nfce(body: ScrapeRequest):
    """Recebe uma URL de NFC-e, faz scraping e retorna no formato Webmania."""
    logger.info("Scraping NFC-e: %s", body.url[:80])

    data, status = scrapper.scrape(body.url)

    if status != "OK":
        logger.warning("Scrape failed: %s", status)
        raise HTTPException(status_code=422, detail=status)

    result = translator.translate(data)
    logger.info("Scrape OK — Chave: %s", result.get("chave", "?")[:20])
    return result
