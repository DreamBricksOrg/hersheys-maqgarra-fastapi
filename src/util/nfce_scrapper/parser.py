import logging
import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from bs4 import BeautifulSoup, Tag

from .exceptions import NfceCancelledError, NfceDeniedError, NfceNotFoundError, NfceParseError
from .models import (
    NfceBuyerModel,
    NfceData,
    NfceItemModel,
    NfcePaymentModel,
    NfceSellerModel,
    NfceTotalsModel,
)

logger = logging.getLogger(__name__)

_RE_CNPJ = re.compile(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}")
_RE_CPF = re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}")
_RE_ACCESS_KEY = re.compile(r"\d{4}[\s\.]?\d{4}[\s\.]?\d{4}[\s\.]?\d{4}[\s\.]?\d{4}[\s\.]?\d{4}[\s\.]?\d{4}[\s\.]?\d{4}[\s\.]?\d{4}[\s\.]?\d{4}[\s\.]?\d{4}")
_RE_CURRENCY = re.compile(r"R\$\s*([\d\.]+,\d{2})")
_RE_DATE = re.compile(r"\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2}")
_RE_DIGITS44 = re.compile(r"\d{44}")


def _clean_text(s: Optional[str]) -> str:
    if not s:
        return ""
    return " ".join(s.split())


def _clean_money(s: str) -> Optional[Decimal]:
    """Convert Brazilian currency string (e.g. '1.234,56' or 'R$ 1.234,56') to Decimal."""
    if not s:
        return None
    s = s.strip()
    # Handle special values
    if s.lower() in ("nan", "n/a", "indefinido"):
        return None
    s = re.sub(r"R\$\s*", "", s)
    s = s.replace(".", "").replace(",", ".")
    try:
        result = Decimal(s)
        # Check if result is NaN or infinite
        if result.is_nan() or result.is_infinite():
            return None
        return result
    except (InvalidOperation, ValueError):
        return None


def _find_by_label(soup: BeautifulSoup, *labels: str) -> Optional[str]:
    """Walk all text nodes; when one matches a label, return the next sibling text."""
    for label in labels:
        for tag in soup.find_all(string=re.compile(re.escape(label), re.IGNORECASE)):
            parent = tag.parent
            if parent is None:
                continue
            # Try next sibling text
            next_sib = parent.find_next_sibling()
            if next_sib:
                text = _clean_text(next_sib.get_text())
                if text:
                    return text
            # Try parent's next sibling
            grandparent = parent.parent
            if grandparent:
                next_sib2 = grandparent.find_next_sibling()
                if next_sib2:
                    text = _clean_text(next_sib2.get_text())
                    if text:
                        return text
    return None


def _get_hidden(soup: BeautifulSoup, field_id: str) -> str:
    tag = soup.find("input", {"id": field_id})
    if tag:
        return tag.get("value", "") or ""
    return ""


class NfceParser:
    def __init__(self, html: str, url: str):
        self._soup = BeautifulSoup(html, "lxml")
        self._url = url
        self._text = self._soup.get_text(" ", strip=True)
        logger.debug("NfceParser HTML preview:\n%s", self._soup.prettify()[:5000])

    def parse(self) -> NfceData:
        self._check_error_container()
        self._check_status_flags()

        is_cancelled = _get_hidden(self._soup, "hdfNotaCancelada").lower() == "true"
        is_denied = _get_hidden(self._soup, "hdfNotaDenegada").lower() == "true"
        is_epec = _get_hidden(self._soup, "hdfNotaEpec").lower() == "true"

        seller = self._parse_seller()
        buyer = self._parse_buyer()
        items = self._parse_items()
        totals = self._parse_totals(items)
        payments = self._parse_payments()
        metadata = self._parse_metadata()

        from datetime import datetime, timezone
        scraped_at = datetime.now(timezone.utc).isoformat()

        return NfceData(
            access_key=metadata["access_key"],
            invoice_number=metadata["invoice_number"],
            series=metadata["series"],
            issue_date=metadata["issue_date"],
            authorization_protocol=metadata["authorization_protocol"],
            authorization_date=metadata["authorization_date"],
            seller=seller,
            buyer=buyer,
            items=items,
            totals=totals,
            payments=payments,
            is_cancelled=is_cancelled,
            is_denied=is_denied,
            is_epec_only=is_epec,
            source_url=self._url,
            scraped_at=scraped_at,
        )

    # ------------------------------------------------------------------
    # Status checks
    # ------------------------------------------------------------------

    def _check_error_container(self):
        err = self._soup.find(id="erro")
        if err:
            style = err.get("style", "")
            if "display:none" not in style.replace(" ", "") and "display: none" not in style:
                msg = _clean_text(err.get_text())
                raise NfceNotFoundError(f"SEFAZ returned error page: {msg}")

    def _check_status_flags(self):
        if _get_hidden(self._soup, "hdfNotaCancelada").lower() == "true":
            raise NfceCancelledError("Invoice is cancelled")
        if _get_hidden(self._soup, "hdfNotaDenegada").lower() == "true":
            raise NfceDeniedError("Invoice is denied")

    # ------------------------------------------------------------------
    # Seller
    # ------------------------------------------------------------------

    def _parse_seller(self) -> NfceSellerModel:
        name = self._seller_name()
        cnpj = self._seller_cnpj()
        address = self._seller_address()

        if not name:
            raise NfceParseError("Seller name not found")
        if not cnpj:
            raise NfceParseError("Seller CNPJ not found")

        return NfceSellerModel(name=name, cnpj=cnpj, address=address or "")

    def _seller_name(self) -> Optional[str]:
        # Layer 1: common container IDs/classes used by SEFAZ SP
        for selector in (
            {"id": "txtNomeEmitente"},
            {"class": "txtTopo"},
        ):
            tag = self._soup.find(attrs=selector)
            if tag:
                return _clean_text(tag.get_text())

        # Layer 2: first <div> or <span> that is a prominent heading near top of body
        # SEFAZ SP wraps seller name in <div class="text-center"> at top of page
        for tag in self._soup.find_all(["div", "span", "h1", "h2", "h3"]):
            text = _clean_text(tag.get_text())
            if text and 5 < len(text) < 120 and not any(c in text for c in ["CNPJ", "CPF", "R$", "/"]):
                # heuristic: first substantial text block before CNPJ line
                cnpj_tag = self._soup.find(string=_RE_CNPJ)
                if cnpj_tag:
                    cnpj_pos = str(self._soup).find(str(cnpj_tag))
                    tag_pos = str(self._soup).find(str(tag))
                    if 0 < tag_pos < cnpj_pos:
                        return text

        return None

    def _seller_cnpj(self) -> Optional[str]:
        m = _RE_CNPJ.search(self._text)
        return m.group(0) if m else None

    def _seller_address(self) -> Optional[str]:
        for selector in ({"id": "txtEndereco"}, {"class": "NomeProduto"}):
            tag = self._soup.find(attrs=selector)
            if tag:
                return _clean_text(tag.get_text())

        label_result = _find_by_label(self._soup, "Endereço:", "Endereco:")
        if label_result:
            return label_result

        # Fallback: text between CNPJ line and next section
        cnpj_tags = self._soup.find_all(string=_RE_CNPJ)
        if cnpj_tags:
            parent = cnpj_tags[0].parent
            if parent:
                next_tag = parent.find_next_sibling()
                if next_tag:
                    return _clean_text(next_tag.get_text())
        return ""

    # ------------------------------------------------------------------
    # Buyer
    # ------------------------------------------------------------------

    def _parse_buyer(self) -> Optional[NfceBuyerModel]:
        # CPF do destinatário
        cpf = None
        cpf_label = _find_by_label(self._soup, "CPF do Consumidor:", "CPF:")
        if cpf_label:
            m = _RE_CPF.search(cpf_label)
            cpf = m.group(0) if m else cpf_label

        cnpj = None
        cnpj_tags = _RE_CNPJ.findall(self._text)
        # First CNPJ is seller; second (if exists) is buyer
        if len(cnpj_tags) >= 2:
            cnpj = cnpj_tags[1]

        if not cpf and not cnpj:
            return None

        return NfceBuyerModel(cpf=cpf, cnpj=cnpj)

    # ------------------------------------------------------------------
    # Items
    # ------------------------------------------------------------------

    def _parse_items(self) -> list[NfceItemModel]:
        items: list[NfceItemModel] = []

        # Primary: look for table rows inside a products section (more reliable)
        table = self._soup.find("table", attrs={"id": re.compile(r"tabResult|tabelaProduto", re.I)})
        if table:
            item_rows = table.find_all("tr")
        else:
            # Fallback: SEFAZ SP wraps each item in a container with class "item" or "linhaShade"/"linhaNormal"
            item_rows = self._soup.find_all(attrs={"class": re.compile(r"item|linhaNormal|linhaShade|produto", re.I)})

        for row in item_rows:
            item = self._parse_item_row(row)
            if item:
                items.append(item)

        if not items:
            raise NfceParseError("No items found in invoice")

        return items

    def _parse_item_row(self, row: Tag) -> Optional[NfceItemModel]:
        cells = row.find_all(["td", "span", "div"])
        texts = [_clean_text(c.get_text()) for c in cells if _clean_text(c.get_text())]

        if len(texts) < 2:
            return None

        # Try to find description (longest non-numeric text)
        description = ""
        code = None
        qty = None
        unit = ""
        unit_price = None
        total_price = None

        # Look for labeled sub-elements
        desc_tag = row.find(attrs={"class": re.compile(r"descricao|txtTit|nomeProduto|NomeProduto", re.I)})
        if desc_tag:
            description = _clean_text(desc_tag.get_text())

        code_tag = row.find(attrs={"class": re.compile(r"codigo|txtCodigo|Codigo|RCod", re.I)})
        if code_tag:
            code_text = _clean_text(code_tag.get_text())
            m = re.search(r"(\d+)", code_text)
            code = m.group(1) if m else code_text

        qty_tag = row.find(attrs={"class": re.compile(r"Qtd|qtd|quantidade|Rqtd", re.I)})
        if qty_tag:
            qty_text = _clean_text(qty_tag.get_text())
            # Match numbers that can have commas or dots (Brazilian format)
            m = re.search(r"(\d[\d,\.]*\d|\d)", qty_text)
            if m:
                qty = _clean_money(m.group(1).replace(".", ",") if "," not in m.group(1) else m.group(1))

        unit_tag = row.find(attrs={"class": re.compile(r"unidade|txtUM|Un\b|RUN", re.I)})
        if unit_tag:
            unit = _clean_text(unit_tag.get_text())

        unit_price_tag = row.find(attrs={"class": re.compile(r"vlrUni|VlUnit|unit_price|precoUni|RvlUnit", re.I)})
        if unit_price_tag:
            unit_price = _clean_money(_clean_text(unit_price_tag.get_text()))

        total_tag = row.find(attrs={"class": re.compile(r"valor|vlrItem|totalItem|Total\b", re.I)})
        if total_tag:
            total_price = _clean_money(_clean_text(total_tag.get_text()))

        # Fallback: parse structured spans/divs by label text within the row
        if not description:
            for tag in row.find_all(string=re.compile(r"Código|Descrição|Qtde\.|Vl\. Unit\.|Vl\. Total", re.I)):
                label = _clean_text(str(tag))
                value_tag = tag.parent.find_next_sibling() if tag.parent else None
                if value_tag:
                    val = _clean_text(value_tag.get_text())
                    if "Descrição" in label or "Descricao" in label:
                        description = val
                    elif "Código" in label or "Codigo" in label:
                        code = val
                    elif "Qtde" in label:
                        m = re.search(r"([\d,\.]+)\s*(\w+)?", val)
                        if m:
                            qty = _clean_money(m.group(1).replace(".", "").replace(",", ".") if "," in m.group(1) else m.group(1))
                            if m.group(2):
                                unit = m.group(2)
                    elif "Unit" in label:
                        unit_price = _clean_money(val)
                    elif "Total" in label:
                        total_price = _clean_money(val)

        if not description or qty is None or total_price is None:
            return None

        return NfceItemModel(
            code=code,
            description=description,
            quantity=qty,
            unit=unit or "UN",
            unit_price=unit_price or Decimal("0"),
            total_price=total_price,
        )

    # ------------------------------------------------------------------
    # Totals
    # ------------------------------------------------------------------

    def _parse_totals(self, items: list[NfceItemModel]) -> NfceTotalsModel:
        item_count = len(items)

        # Total value to pay
        total = None
        for label in ("Valor a pagar", "Total", "Valor Total"):
            val = _find_by_label(self._soup, label)
            if val:
                total = _clean_money(val)
                if total:
                    break

        if total is None:
            # Try regex on full text
            m = _RE_CURRENCY.search(self._text)
            total = _clean_money(m.group(1)) if m else None

        if total is None:
            # Sum items as last resort
            total = sum(i.total_price for i in items)

        subtotal_val = _find_by_label(self._soup, "Valor dos Produtos", "Subtotal")
        subtotal = _clean_money(subtotal_val) if subtotal_val else None

        discounts_val = _find_by_label(self._soup, "Desconto", "Descontos")
        discounts = _clean_money(discounts_val) if discounts_val else None

        taxes_val = _find_by_label(self._soup, "Valor aprox. dos Tributos", "Tributos")
        taxes = _clean_money(taxes_val) if taxes_val else None

        return NfceTotalsModel(
            item_count=item_count,
            subtotal=subtotal,
            discounts=discounts,
            total=total,
            total_taxes=taxes,
        )

    # ------------------------------------------------------------------
    # Payments
    # ------------------------------------------------------------------

    def _parse_payments(self) -> list[NfcePaymentModel]:
        payments: list[NfcePaymentModel] = []

        # Look for payment section container
        payment_section = self._soup.find(attrs={"id": re.compile(r"pagamento|payment", re.I)})
        if not payment_section:
            payment_section = self._soup.find(attrs={"class": re.compile(r"pagamento|payment|infoPgto", re.I)})
        if not payment_section:
            payment_section = self._soup

        # Find rows/spans that contain payment method and amount
        pay_rows = payment_section.find_all(attrs={"class": re.compile(r"linhaForma|pgto|payment_row|Pagamento", re.I)})

        for row in pay_rows:
            payment = self._parse_payment_row(row)
            if payment:
                payments.append(payment)

        # Fallback: scan for label patterns like "Cartão de Crédito" or "Dinheiro"
        if not payments:
            known_methods = [
                "Cartão de Crédito", "Cartão de Débito", "Dinheiro",
                "PIX", "Voucher", "Transferência", "Cheque"
            ]
            for method in known_methods:
                val = _find_by_label(self._soup, method)
                if val:
                    amount = _clean_money(val)
                    if amount:
                        change_val = _find_by_label(self._soup, "Troco")
                        change = _clean_money(change_val) if change_val else None
                        payments.append(NfcePaymentModel(
                            method=method, amount_paid=amount, change=change
                        ))

        if not payments:
            # Last resort: try to extract from page text with Valor a pagar
            total_val = _find_by_label(self._soup, "Valor a pagar")
            amount = _clean_money(total_val) if total_val else None
            if amount:
                payments.append(NfcePaymentModel(method="Não identificado", amount_paid=amount))

        return payments

    def _parse_payment_row(self, row: Tag) -> Optional[NfcePaymentModel]:
        method_tag = row.find(attrs={"class": re.compile(r"method|forma|descricao", re.I)})
        amount_tag = row.find(attrs={"class": re.compile(r"valor|amount|vlr", re.I)})
        change_tag = row.find(attrs={"class": re.compile(r"troco|change", re.I)})

        method = _clean_text(method_tag.get_text()) if method_tag else _clean_text(row.get_text())
        amount = _clean_money(_clean_text(amount_tag.get_text())) if amount_tag else None
        change = _clean_money(_clean_text(change_tag.get_text())) if change_tag else None

        if not method or not amount:
            return None
        return NfcePaymentModel(method=method, amount_paid=amount, change=change)

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def _parse_metadata(self) -> dict:
        access_key = self._parse_access_key()
        if not access_key:
            raise NfceParseError("Access key (chave de acesso) not found")

        invoice_number = self._find_invoice_field("Número", "Nro.", "Numero")
        series = self._find_invoice_field("Série", "Serie")
        issue_date = self._find_date_field("Emissão:", "Data de Emissão", "Emissao")
        auth_protocol = self._find_invoice_field("Protocolo de Autorização", "Protocolo")
        auth_date = self._find_date_field("Protocolo de Autorização", "Data Autorização")

        # Fallbacks via regex
        all_dates = _RE_DATE.findall(self._text)
        if not issue_date and all_dates:
            issue_date = all_dates[0]
        if not auth_date and len(all_dates) >= 2:
            auth_date = all_dates[1]
        elif not auth_date and all_dates:
            auth_date = all_dates[0]

        return {
            "access_key": access_key,
            "invoice_number": invoice_number or "",
            "series": series or "",
            "issue_date": issue_date or "",
            "authorization_protocol": auth_protocol or "",
            "authorization_date": auth_date or "",
        }

    def _parse_access_key(self) -> Optional[str]:
        # Layer 1: hidden field
        key = _get_hidden(self._soup, "hdfChaveNFe")
        if key and _RE_DIGITS44.match(key.replace(" ", "")):
            return key

        # Layer 2: label-based
        val = _find_by_label(self._soup, "Chave de acesso", "Chave de Acesso")
        if val:
            digits = re.sub(r"\s+", "", val)
            if _RE_DIGITS44.match(digits):
                return val

        # Layer 3: regex on full text (44 consecutive digits)
        m = _RE_DIGITS44.search(self._text.replace(" ", ""))
        if m:
            return m.group(0)

        return None

    def _find_invoice_field(self, *labels: str) -> Optional[str]:
        # Try to find using label-based approach first
        for label in labels:
            # Search in the full text for the label followed by a value
            # Pattern: "Label: value" where value is digits
            pattern = re.escape(label) + r"[:\s]*(\d+)"
            m = re.search(pattern, self._text, re.IGNORECASE)
            if m:
                return m.group(1)

        # Fallback to original method if regex doesn't find it
        val = _find_by_label(self._soup, *labels)
        if val:
            # Try to extract just the number
            m = re.search(r"(\d+)", val)
            if m:
                return m.group(1)
            return val
        return None

    def _find_date_field(self, *labels: str) -> Optional[str]:
        val = _find_by_label(self._soup, *labels)
        if val:
            m = _RE_DATE.search(val)
            return m.group(0) if m else val
        return None
