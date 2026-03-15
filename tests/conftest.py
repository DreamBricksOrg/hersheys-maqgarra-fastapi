"""Shared pytest fixtures for NFC-e scraper and translator tests."""

import json
from pathlib import Path

import pytest


@pytest.fixture
def sample_nfce_data():
    """Minimal valid NfceData dict for testing translator."""
    return {
        "access_key": "35260243283811004732650010001055941001056011",
        "invoice_number": "105594",
        "series": "1",
        "issue_date": "10/02/2026 14:11:44",
        "authorization_protocol": "135260952993570",
        "authorization_date": "10/02/2026 14:11:46",
        "seller": {
            "name": "Kalunga SA",
            "cnpj": "43.283.811/0047-32",
            "address": "Av Imperatriz Leopoldina , 1170 , NA , Vila Leopoldina , Sao Paulo , SP",
        },
        "buyer": None,
        "items": [
            {
                "code": "038903",
                "description": "Bloco desenho A4 branco 180g 66667164 Canson BL 20 FL",
                "quantity": "1",
                "unit": "BL",
                "unit_price": "13.10",
                "total_price": "13.10",
            },
            {
                "code": "478743",
                "description": "Papel fotografico A4 230g matte dupla face M230-20 Spiral PT 20 FL",
                "quantity": "1",
                "unit": "PT",
                "unit_price": "34.90",
                "total_price": "34.90",
            },
        ],
        "totals": {
            "item_count": 2,
            "subtotal": None,
            "discounts": None,
            "total": "48.00",
            "total_taxes": None,
        },
        "payments": [
            {
                "method": "Cartão de Crédito",
                "amount_paid": "48.00",
                "change": None,
            }
        ],
        "is_cancelled": False,
        "is_denied": False,
        "is_epec_only": False,
        "source_url": "https://www.nfce.fazenda.sp.gov.br/NFCeConsultaPublica/Paginas/ConsultaQRCode.aspx?p=35260243283811004732650010001055941001056011|2|1|1|311111C4E7BB56B70DD3C25F25F29300E2E6AFB5",
        "scraped_at": "2026-03-13T22:11:55.593476+00:00",
    }


@pytest.fixture
def sample_nfce_html():
    """Return path to fixture HTML file."""
    return Path(__file__).parent / "fixtures" / "valid_nfce.html"


@pytest.fixture
def sample_nfce_json_path():
    """Return path to fixture JSON file."""
    return Path(__file__).parent / "fixtures" / "valid_nfce.json"


@pytest.fixture
def load_fixture_json(sample_nfce_json_path):
    """Load the fixture JSON file and return its content."""
    with open(sample_nfce_json_path, encoding="utf-8") as f:
        return json.load(f)
