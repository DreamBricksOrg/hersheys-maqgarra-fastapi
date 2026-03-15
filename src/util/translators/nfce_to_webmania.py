import json
import uuid
from pathlib import Path
from typing import Union


class NfceToWebmaniaTranslator:
    """Translates NFC-e scraper output to Webmania API format."""

    def translate(self, source: Union[dict, str, Path]) -> dict:
        """
        Translate NFC-e data to Webmania format.

        Args:
            source: dict, file path (str or Path) to JSON, or JSON-like object

        Returns:
            dict with Webmania API schema
        """
        data = self._load_source(source)
        result = {
            "uuid":        str(uuid.uuid4()),
            "status":      self._build_status(data),
            "chave":       data.get("access_key", ""),
            "protocolo":   data.get("authorization_protocol", ""),
            "data_emissao": data.get("issue_date", ""),
            "numero":      data.get("invoice_number", ""),
            "serie":       int(data.get("series") or 0),
            "total":       data.get("totals", {}).get("total") or "0",
            "emitente":    self._build_emitente(data.get("seller", {})),
            "produtos":    self._build_produtos(data.get("items", [])),
            "pagamento":   self._build_pagamento(data.get("payments", [])),
        }
        consumidor = self._build_consumidor(data.get("buyer"))
        if consumidor:
            result["consumidor"] = consumidor
        return result

    def _load_source(self, source: Union[dict, str, Path]) -> dict:
        """Load JSON data from dict, file path, or string path."""
        if isinstance(source, dict):
            return source
        with open(Path(source), encoding="utf-8") as f:
            return json.load(f)

    def _build_status(self, data: dict) -> str:
        """Determine status: cancelado, denegado, or aprovado."""
        if data.get("is_cancelled"):
            return "cancelado"
        if data.get("is_denied"):
            return "denegado"
        return "aprovado"

    def _parse_address(self, raw: str) -> dict:
        """
        Parse comma-separated address string.

        Format: "street , number , complement , neighborhood , city , state"
        """
        parts = raw.split(" , ") if raw else []
        def get(i): return parts[i].strip() if i < len(parts) else ""
        return {
            "endereco": get(0),
            "numero":   get(1),
            "bairro":   get(3),
            "cidade":   get(4),
            "uf":       get(5),
        }

    def _build_emitente(self, seller: dict) -> dict:
        """Build seller/issuer block with address parsing."""
        return {
            "cnpj":         seller.get("cnpj", ""),
            "razao_social": seller.get("name", ""),
            **self._parse_address(seller.get("address", "")),
        }

    def _build_consumidor(self, buyer: dict | None) -> dict | None:
        """Build buyer block. Return None if no CPF/CNPJ."""
        if not buyer:
            return None
        result = {}
        if buyer.get("cpf"):
            result["cpf"] = buyer["cpf"]
        if buyer.get("cnpj"):
            result["cnpj"] = buyer["cnpj"]
        return result or None

    def _parse_unit(self, unit: str) -> str:
        """Strip 'UN: ' prefix from unit if present."""
        if unit and unit.upper().startswith("UN: "):
            return unit[4:].strip()
        return (unit or "").strip()

    def _build_produtos(self, items: list) -> list:
        """Build products array. Omit 'ean' if code is None/empty."""
        result = []
        for i, item in enumerate(items):
            produto = {
                "nome":           item.get("description", ""),
                "item":           str(i + 1),
                "quantidade":     item.get("quantity", "0"),
                "unidade":        self._parse_unit(item.get("unit", "")),
                "valor_unitario": item.get("unit_price", "0"),
                "subtotal":       item.get("total_price", "0"),
                "total":          item.get("total_price", "0"),
            }
            if item.get("code"):
                produto["ean"] = item["code"]
            result.append(produto)
        return result

    def _build_pagamento(self, payments: list) -> list:
        """Build payments array."""
        return [
            {
                "forma_pagamento": p.get("method", ""),
                "valor_pagamento": p.get("amount_paid", "0"),
            }
            for p in payments
        ]


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python nfce_to_webmania.py <path_to_nfce_json>", file=sys.stderr)
        sys.exit(1)

    filepath = sys.argv[1]
    try:
        translator = NfceToWebmaniaTranslator()
        result = translator.translate(filepath)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except FileNotFoundError:
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in file: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
