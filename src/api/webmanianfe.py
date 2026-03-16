import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.config import settings
from util.webmania_nfe import (
    WebmaniaNfeClient,
    WebmaniaAuthError,
    WebmaniaNetworkError,
    WebmaniaNfeError,
    WebmaniaNotFoundError,
    WebmaniaValidationError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webmanianfe", tags=["NFe - WebmaniaNFe"])


def _get_client() -> WebmaniaNfeClient:
    if not settings.NF_API_KEY:
        raise HTTPException(status_code=500, detail="NF_API_KEY not configured in .env")
    return WebmaniaNfeClient(
        base_url=settings.NF_BASE_API,
        token=settings.NF_API_KEY,
    )


def _handle_error(e: Exception):
    """Convert WebmaniaNFe exceptions into HTTPException."""
    if isinstance(e, WebmaniaAuthError):
        raise HTTPException(status_code=401, detail=str(e))
    if isinstance(e, WebmaniaNotFoundError):
        raise HTTPException(status_code=404, detail=str(e))
    if isinstance(e, WebmaniaValidationError):
        raise HTTPException(status_code=422, detail=str(e))
    if isinstance(e, WebmaniaNetworkError):
        raise HTTPException(status_code=502, detail=str(e))
    raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------------
# Request Bodies
# ------------------------------------------------------------------

class ValidateImageBody(BaseModel):
    imagens: list[str]
    modelo: str = "nfe"
    antifraude: bool = False


class ValidateXmlBody(BaseModel):
    xml: str


class SerproBody(BaseModel):
    consumer_key: str
    consumer_secret: str


# ------------------------------------------------------------------
# DFe Validation
# ------------------------------------------------------------------

@router.post("/validar/imagem", summary="Validar DFe por imagem")
def validate_dfe_image(body: ValidateImageBody):
    """Envia URLs de imagens para validação de DFe na API WebmaniaNFe."""
    logger.info("POST /validar/imagem -> %s/valida/dfe/imagem", settings.NF_BASE_API)
    try:
        client = _get_client()
        result = client.validate_image(
            image_urls=body.imagens,
            modelo=body.modelo,
            antifraude=body.antifraude,
        )
        logger.info("[DEBUG] Resposta Webmania: %s", result)
        return result
    except WebmaniaNfeError as e:
        logger.error("[DEBUG] Erro Webmania: %s", e)
        _handle_error(e)


@router.post("/validar/xml", summary="Validar DFe por XML")
async def validate_dfe_xml(body: ValidateXmlBody):
    """Envia conteúdo XML para validação de DFe."""
    logger.info("POST /validar/xml -> %s/valida/xml", settings.NF_BASE_API)
    try:
        client = _get_client()
        return client.validate_xml(body.xml)
    except WebmaniaNfeError as e:
        _handle_error(e)


# ------------------------------------------------------------------
# SERPRO Connections
# ------------------------------------------------------------------

@router.post("/serpro", summary="Criar conexão SERPRO")
async def create_serpro(body: SerproBody):
    """Registra credenciais SERPRO na WebmaniaNFe."""
    logger.info("POST /serpro -> %s/valida/conexoes/serpro", settings.NF_BASE_API)
    try:
        client = _get_client()
        return client.create_serpro_connection(body.consumer_key, body.consumer_secret)
    except WebmaniaNfeError as e:
        _handle_error(e)


@router.get("/serpro", summary="Verificar conexão SERPRO")
async def get_serpro():
    """Verifica status da conexão SERPRO."""
    logger.info("GET /serpro -> %s/valida/conexoes/serpro", settings.NF_BASE_API)
    try:
        client = _get_client()
        return client.get_serpro_connection()
    except WebmaniaNfeError as e:
        _handle_error(e)


@router.delete("/serpro", summary="Remover conexão SERPRO")
async def delete_serpro():
    """Remove a conexão SERPRO registrada."""
    logger.info("DELETE /serpro -> %s/valida/conexoes/serpro", settings.NF_BASE_API)
    try:
        client = _get_client()
        return client.delete_serpro_connection()
    except WebmaniaNfeError as e:
        _handle_error(e)


# ------------------------------------------------------------------
# Logs
# ------------------------------------------------------------------

@router.get("/logs/{uuid}", summary="Consultar log de validação")
async def get_validation_log(uuid: str):
    """Retorna o log de uma validação pelo UUID."""
    logger.info("GET /logs/%s -> %s/valida/logs/%s", uuid, settings.NF_BASE_API, uuid)
    try:
        client = _get_client()
        return client.get_log(uuid)
    except WebmaniaNfeError as e:
        _handle_error(e)


# ------------------------------------------------------------------
# Credits
# ------------------------------------------------------------------

@router.get("/creditos", summary="Consultar saldo de créditos")
async def get_credits():
    """Retorna o saldo de créditos disponíveis."""
    logger.info("GET /creditos -> %s/creditos", settings.NF_BASE_API)
    try:
        client = _get_client()
        return client.get_credits()
    except WebmaniaNfeError as e:
        _handle_error(e)


@router.get("/creditos/recargas", summary="Histórico de recargas")
async def get_credit_recharges():
    """Retorna o histórico de recargas de créditos."""
    logger.info("GET /creditos/recargas -> %s/creditos/recargas", settings.NF_BASE_API)
    try:
        client = _get_client()
        return client.get_credit_recharges()
    except WebmaniaNfeError as e:
        _handle_error(e)
