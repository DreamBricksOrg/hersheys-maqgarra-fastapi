"""Tests for NfceToWebmaniaTranslator class."""

import json
import uuid
from pathlib import Path

import pytest

from util.translators.nfce_to_webmania import NfceToWebmaniaTranslator


class TestNfceToWebmaniaTranslatorStatus:
    """Test status field conversion."""

    def test_cancelled_status(self, sample_nfce_data):
        """is_cancelled=True should return 'cancelado'."""
        translator = NfceToWebmaniaTranslator()
        data = sample_nfce_data.copy()
        data["is_cancelled"] = True
        result = translator.translate(data)
        assert result["status"] == "cancelado"

    def test_denied_status(self, sample_nfce_data):
        """is_denied=True should return 'denegado'."""
        translator = NfceToWebmaniaTranslator()
        data = sample_nfce_data.copy()
        data["is_denied"] = True
        result = translator.translate(data)
        assert result["status"] == "denegado"

    def test_approved_status(self, sample_nfce_data):
        """Neither cancelled nor denied should return 'aprovado'."""
        translator = NfceToWebmaniaTranslator()
        data = sample_nfce_data.copy()
        data["is_cancelled"] = False
        data["is_denied"] = False
        result = translator.translate(data)
        assert result["status"] == "aprovado"

    def test_cancelled_takes_precedence(self, sample_nfce_data):
        """If both cancelled and denied, cancelled should take precedence."""
        translator = NfceToWebmaniaTranslator()
        data = sample_nfce_data.copy()
        data["is_cancelled"] = True
        data["is_denied"] = True
        result = translator.translate(data)
        assert result["status"] == "cancelado"


class TestNfceToWebmaniaTranslatorParseAddress:
    """Test address parsing."""

    def test_parse_full_address(self, sample_nfce_data):
        """Full 6-part address should parse correctly."""
        translator = NfceToWebmaniaTranslator()
        result = translator.translate(sample_nfce_data)
        emitente = result["emitente"]

        assert emitente["endereco"] == "Av Imperatriz Leopoldina"
        assert emitente["numero"] == "1170"
        assert emitente["bairro"] == "Vila Leopoldina"
        assert emitente["cidade"] == "Sao Paulo"
        assert emitente["uf"] == "SP"

    def test_parse_partial_address(self):
        """Partial address should fill missing parts with empty strings."""
        translator = NfceToWebmaniaTranslator()
        data = {
            "seller": {
                "name": "Test Company",
                "cnpj": "00.000.000/0000-00",
                "address": "Rua Exemplo , 123",  # Only street and number
            },
            "items": [],
        }
        result = translator.translate(data)
        emitente = result["emitente"]

        assert emitente["endereco"] == "Rua Exemplo"
        assert emitente["numero"] == "123"
        assert emitente["bairro"] == ""
        assert emitente["cidade"] == ""
        assert emitente["uf"] == ""

    def test_parse_empty_address(self):
        """Empty address should return all empty fields."""
        translator = NfceToWebmaniaTranslator()
        data = {
            "seller": {
                "name": "Test Company",
                "cnpj": "00.000.000/0000-00",
                "address": "",
            },
            "items": [],
        }
        result = translator.translate(data)
        emitente = result["emitente"]

        assert emitente["endereco"] == ""
        assert emitente["numero"] == ""
        assert emitente["bairro"] == ""
        assert emitente["cidade"] == ""
        assert emitente["uf"] == ""


class TestNfceToWebmaniaTranslatorConsumidor:
    """Test buyer (consumidor) field building."""

    def test_buyer_with_cpf(self):
        """Buyer with CPF should include CPF in result."""
        translator = NfceToWebmaniaTranslator()
        data = {
            "buyer": {
                "cpf": "123.456.789-10",
                "cnpj": None,
                "name": None,
                "address": None,
            },
            "items": [],
        }
        result = translator.translate(data)
        assert "consumidor" in result
        assert result["consumidor"]["cpf"] == "123.456.789-10"

    def test_buyer_with_cnpj(self):
        """Buyer with CNPJ should include CNPJ in result."""
        translator = NfceToWebmaniaTranslator()
        data = {
            "buyer": {
                "cpf": None,
                "cnpj": "12.345.678/0001-90",
                "name": None,
                "address": None,
            },
            "items": [],
        }
        result = translator.translate(data)
        assert "consumidor" in result
        assert result["consumidor"]["cnpj"] == "12.345.678/0001-90"

    def test_buyer_with_cpf_and_cnpj(self):
        """Buyer with both CPF and CNPJ should include both."""
        translator = NfceToWebmaniaTranslator()
        data = {
            "buyer": {
                "cpf": "123.456.789-10",
                "cnpj": "12.345.678/0001-90",
                "name": None,
                "address": None,
            },
            "items": [],
        }
        result = translator.translate(data)
        assert "consumidor" in result
        assert result["consumidor"]["cpf"] == "123.456.789-10"
        assert result["consumidor"]["cnpj"] == "12.345.678/0001-90"

    def test_buyer_none_returns_no_consumidor(self):
        """buyer=None should not include consumidor in result."""
        translator = NfceToWebmaniaTranslator()
        data = {
            "buyer": None,
            "items": [],
        }
        result = translator.translate(data)
        assert "consumidor" not in result

    def test_buyer_without_cpf_cnpj_returns_no_consumidor(self):
        """Buyer with no CPF/CNPJ should not include consumidor."""
        translator = NfceToWebmaniaTranslator()
        data = {
            "buyer": {
                "cpf": None,
                "cnpj": None,
                "name": "John Doe",
                "address": "123 Main St",
            },
            "items": [],
        }
        result = translator.translate(data)
        assert "consumidor" not in result


class TestNfceToWebmaniaTranslatorParseUnit:
    """Test unit field parsing."""

    def test_parse_unit_with_prefix(self):
        """Unit with 'UN: ' prefix should be stripped."""
        translator = NfceToWebmaniaTranslator()
        assert translator._parse_unit("UN: BL") == "BL"
        assert translator._parse_unit("UN: PT") == "PT"
        assert translator._parse_unit("UN: KG") == "KG"

    def test_parse_unit_without_prefix(self):
        """Unit without prefix should remain unchanged."""
        translator = NfceToWebmaniaTranslator()
        assert translator._parse_unit("BL") == "BL"
        assert translator._parse_unit("UN") == "UN"
        assert translator._parse_unit("KG") == "KG"

    def test_parse_empty_unit(self):
        """Empty unit should return empty string."""
        translator = NfceToWebmaniaTranslator()
        assert translator._parse_unit("") == ""

    def test_parse_none_unit(self):
        """None unit should return empty string."""
        translator = NfceToWebmaniaTranslator()
        assert translator._parse_unit(None) == ""


class TestNfceToWebmaniaTranslatorProdutos:
    """Test products (items) field building."""

    def test_produtos_with_code(self):
        """Items with code should include 'ean' key."""
        translator = NfceToWebmaniaTranslator()
        data = {
            "items": [
                {
                    "code": "038903",
                    "description": "Bloco A4",
                    "quantity": "1",
                    "unit": "BL",
                    "unit_price": "13.10",
                    "total_price": "13.10",
                }
            ]
        }
        result = translator.translate(data)
        produtos = result["produtos"]

        assert len(produtos) == 1
        produto = produtos[0]
        assert "ean" in produto
        assert produto["ean"] == "038903"

    def test_produtos_without_code(self):
        """Items without code should not include 'ean' key."""
        translator = NfceToWebmaniaTranslator()
        data = {
            "items": [
                {
                    "code": None,
                    "description": "Generic Item",
                    "quantity": "2",
                    "unit": "UN",
                    "unit_price": "10.00",
                    "total_price": "20.00",
                }
            ]
        }
        result = translator.translate(data)
        produtos = result["produtos"]

        assert len(produtos) == 1
        produto = produtos[0]
        assert "ean" not in produto

    def test_item_number_is_1_indexed_string(self):
        """Item numbers should be 1-indexed strings."""
        translator = NfceToWebmaniaTranslator()
        data = {
            "items": [
                {
                    "description": "Item 1",
                    "quantity": "1",
                    "unit": "UN",
                    "unit_price": "10.00",
                    "total_price": "10.00",
                },
                {
                    "description": "Item 2",
                    "quantity": "2",
                    "unit": "UN",
                    "unit_price": "20.00",
                    "total_price": "40.00",
                },
            ]
        }
        result = translator.translate(data)
        produtos = result["produtos"]

        assert produtos[0]["item"] == "1"
        assert produtos[1]["item"] == "2"

    def test_produtos_empty_list(self):
        """Empty items list should return empty produtos list."""
        translator = NfceToWebmaniaTranslator()
        data = {"items": []}
        result = translator.translate(data)
        assert result["produtos"] == []


class TestNfceToWebmaniaTranslatorTranslateDict:
    """Test translate method with dict input."""

    def test_translate_dict_returns_webmania_schema(self, sample_nfce_data):
        """Translate dict should return all required Webmania fields."""
        translator = NfceToWebmaniaTranslator()
        result = translator.translate(sample_nfce_data)

        # Check required fields
        required_fields = [
            "uuid",
            "status",
            "chave",
            "protocolo",
            "data_emissao",
            "numero",
            "serie",
            "total",
            "emitente",
            "produtos",
            "pagamento",
        ]
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"

    def test_uuid_is_valid_uuid(self, sample_nfce_data):
        """uuid field should be a valid UUID string."""
        translator = NfceToWebmaniaTranslator()
        result = translator.translate(sample_nfce_data)
        uuid_str = result["uuid"]

        try:
            uuid.UUID(uuid_str)
        except ValueError:
            pytest.fail(f"Invalid UUID: {uuid_str}")

    def test_serie_is_int(self, sample_nfce_data):
        """serie field should be an integer."""
        translator = NfceToWebmaniaTranslator()
        result = translator.translate(sample_nfce_data)
        assert isinstance(result["serie"], int)
        assert result["serie"] == 1

    def test_emitente_has_required_fields(self, sample_nfce_data):
        """Emitente should have all address fields."""
        translator = NfceToWebmaniaTranslator()
        result = translator.translate(sample_nfce_data)
        emitente = result["emitente"]

        required_fields = ["cnpj", "razao_social", "endereco", "numero", "bairro", "cidade", "uf"]
        for field in required_fields:
            assert field in emitente, f"Missing field in emitente: {field}"

    def test_translate_preserves_access_key(self, sample_nfce_data):
        """Chave should match access_key."""
        translator = NfceToWebmaniaTranslator()
        result = translator.translate(sample_nfce_data)
        assert result["chave"] == sample_nfce_data["access_key"]

    def test_translate_preserves_invoice_number(self, sample_nfce_data):
        """numero should match invoice_number."""
        translator = NfceToWebmaniaTranslator()
        result = translator.translate(sample_nfce_data)
        assert result["numero"] == sample_nfce_data["invoice_number"]


class TestNfceToWebmaniaTranslatorTranslateFile:
    """Test translate method with file path input."""

    def test_translate_path_object(self, sample_nfce_json_path):
        """Translate with Path object should work."""
        translator = NfceToWebmaniaTranslator()
        result = translator.translate(sample_nfce_json_path)

        assert "uuid" in result
        assert result["status"] == "aprovado"
        assert result["numero"] == "105594"

    def test_translate_string_path(self, sample_nfce_json_path):
        """Translate with string path should work."""
        translator = NfceToWebmaniaTranslator()
        result = translator.translate(str(sample_nfce_json_path))

        assert "uuid" in result
        assert result["status"] == "aprovado"
        assert result["numero"] == "105594"

    def test_translate_file_has_same_result_as_dict(self, sample_nfce_data, sample_nfce_json_path):
        """Translating file should give same result as translating dict."""
        translator = NfceToWebmaniaTranslator()
        result_dict = translator.translate(sample_nfce_data)
        result_file = translator.translate(sample_nfce_json_path)

        # Check key fields match (uuid will differ due to random generation)
        assert result_dict["status"] == result_file["status"]
        assert result_dict["chave"] == result_file["chave"]
        assert result_dict["numero"] == result_file["numero"]
        assert result_dict["serie"] == result_file["serie"]
        assert len(result_dict["produtos"]) == len(result_file["produtos"])

    def test_translate_file_not_found(self):
        """Translating non-existent file should raise error."""
        translator = NfceToWebmaniaTranslator()
        with pytest.raises(FileNotFoundError):
            translator.translate("/nonexistent/path/file.json")


class TestNfceToWebmaniaTranslatorPagamento:
    """Test payment field building."""

    def test_pagamento_structure(self):
        """Pagamento should have correct structure."""
        translator = NfceToWebmaniaTranslator()
        data = {
            "payments": [
                {
                    "method": "Cartão de Crédito",
                    "amount_paid": "100.00",
                    "change": "10.00",
                }
            ]
        }
        result = translator.translate(data)
        pagamento = result["pagamento"]

        assert len(pagamento) == 1
        assert pagamento[0]["forma_pagamento"] == "Cartão de Crédito"
        assert pagamento[0]["valor_pagamento"] == "100.00"

    def test_multiple_payments(self):
        """Multiple payments should be preserved in list."""
        translator = NfceToWebmaniaTranslator()
        data = {
            "payments": [
                {
                    "method": "Dinheiro",
                    "amount_paid": "50.00",
                    "change": "0.00",
                },
                {
                    "method": "Cartão de Débito",
                    "amount_paid": "50.00",
                    "change": None,
                },
            ]
        }
        result = translator.translate(data)
        pagamento = result["pagamento"]

        assert len(pagamento) == 2
        assert pagamento[0]["forma_pagamento"] == "Dinheiro"
        assert pagamento[1]["forma_pagamento"] == "Cartão de Débito"

    def test_empty_payments(self):
        """Empty payments list should return empty list."""
        translator = NfceToWebmaniaTranslator()
        data = {"payments": []}
        result = translator.translate(data)
        assert result["pagamento"] == []
