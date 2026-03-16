"""Tests for NfceScrapper class."""

import json
from pathlib import Path

import pytest
import responses
from requests.exceptions import ConnectionError, Timeout

from util.nfce_scrapper import NfceScrapper
from util.nfce_scrapper.exceptions import (
    NfceCancelledError,
    NfceInvalidUrlError,
    NfceNetworkError,
    NfceNotFoundError,
)


class TestNfceScrapperUrlValidation:
    """Test URL validation (no HTTP calls)."""

    def test_invalid_url_missing_scheme(self):
        """Invalid URL without scheme should return error."""
        scraper = NfceScrapper()
        data, status = scraper.scrape("www.example.com")
        assert data == {}
        assert "Invalid URL" in status or "scheme" in status.lower()

    def test_invalid_url_missing_host(self):
        """Invalid URL without host should return error."""
        scraper = NfceScrapper()
        data, status = scraper.scrape("https://")
        assert data == {}
        assert "Invalid URL" in status or "host" in status.lower()

    def test_missing_p_param(self):
        """URL without 'p' query param should return error."""
        scraper = NfceScrapper()
        data, status = scraper.scrape("https://www.example.com/page")
        assert data == {}
        assert "p" in status.lower() or "param" in status.lower()

    def test_single_pipe_segment(self):
        """Param 'p' with only 1 segment (no pipe) should return error."""
        scraper = NfceScrapper()
        data, status = scraper.scrape(
            "https://www.nfce.fazenda.sp.gov.br/qrcode?p=35260243283811004732650010001055941001056011"
        )
        assert data == {}
        assert "segment" in status.lower() or "pipe" in status.lower()

    def test_first_segment_not_44_digits(self):
        """First segment not 44 digits should return error."""
        scraper = NfceScrapper()
        data, status = scraper.scrape(
            "https://www.nfce.fazenda.sp.gov.br/qrcode?p=invalid44digitkey|2"
        )
        assert data == {}
        assert "44 digit" in status.lower() or "first segment" in status.lower()

    def test_valid_url_format_with_minimal_segments(self):
        """Valid URL with exactly 2 segments should pass validation."""
        # This test uses mocking to avoid actual HTTP calls
        scraper = NfceScrapper()
        with responses.RequestsMock() as rsps:
            url = "https://www.nfce.fazenda.sp.gov.br/qrcode?p=35260243283811004732650010001055941001056011|2"
            html_content = """
                <input id="hdfNotaCancelada" value="false" />
                <input id="hdfNotaDenegada" value="false" />
            """
            rsps.add(responses.GET, url, body=html_content, status=404)
            data, status = scraper.scrape(url)
            # Should fail on HTTP error, not URL validation
            assert "HTTP" in status or "404" in status


class TestNfceScrapperHttpErrors:
    """Test HTTP error handling with mocked requests."""

    def test_http_404_error(self):
        """HTTP 404 should return error gracefully."""
        scraper = NfceScrapper()
        with responses.RequestsMock() as rsps:
            url = "https://www.nfce.fazenda.sp.gov.br/qrcode?p=35260243283811004732650010001055941001056011|2|1|1|abc123"
            rsps.add(responses.GET, url, status=404)
            data, status = scraper.scrape(url)
            assert data == {}
            assert "404" in status or "HTTP" in status

    def test_http_500_error(self):
        """HTTP 500 should return error gracefully."""
        scraper = NfceScrapper()
        with responses.RequestsMock() as rsps:
            url = "https://www.nfce.fazenda.sp.gov.br/qrcode?p=35260243283811004732650010001055941001056011|2|1|1|abc123"
            rsps.add(responses.GET, url, status=500)
            data, status = scraper.scrape(url)
            assert data == {}
            assert "500" in status or "HTTP" in status

    def test_network_connection_error(self):
        """Network error should return error gracefully."""
        scraper = NfceScrapper()
        with responses.RequestsMock() as rsps:
            url = "https://www.nfce.fazenda.sp.gov.br/qrcode?p=35260243283811004732650010001055941001056011|2|1|1|abc123"
            rsps.add(responses.GET, url, body=ConnectionError("Connection refused"))
            data, status = scraper.scrape(url)
            assert data == {}
            assert "Network" in status or "error" in status.lower()

    def test_network_timeout_error(self):
        """Network timeout should return error gracefully."""
        scraper = NfceScrapper()
        with responses.RequestsMock() as rsps:
            url = "https://www.nfce.fazenda.sp.gov.br/qrcode?p=35260243283811004732650010001055941001056011|2|1|1|abc123"
            rsps.add(responses.GET, url, body=Timeout("Request timed out"))
            data, status = scraper.scrape(url)
            assert data == {}
            assert "Network" in status or "error" in status.lower()


class TestNfceScrapperSuccessfulScrape:
    """Test successful scraping with mocked HTML."""

    def test_scrape_valid_html_returns_ok(self, sample_nfce_html):
        """Scraping valid HTML should return status OK."""
        scraper = NfceScrapper()
        with open(sample_nfce_html, encoding="utf-8") as f:
            html_content = f.read()

        with responses.RequestsMock() as rsps:
            url = "https://www.nfce.fazenda.sp.gov.br/qrcode?p=35260243283811004732650010001055941001056011|2|1|1|abc123"
            rsps.add(responses.GET, url, body=html_content, status=200)
            data, status = scraper.scrape(url)

            assert status == "OK"
            assert data != {}
            assert isinstance(data, dict)

    def test_scrape_valid_html_has_seller_info(self, sample_nfce_html):
        """Scraped data should contain seller info."""
        scraper = NfceScrapper()
        with open(sample_nfce_html, encoding="utf-8") as f:
            html_content = f.read()

        with responses.RequestsMock() as rsps:
            url = "https://www.nfce.fazenda.sp.gov.br/qrcode?p=35260243283811004732650010001055941001056011|2|1|1|abc123"
            rsps.add(responses.GET, url, body=html_content, status=200)
            data, status = scraper.scrape(url)

            assert "seller" in data
            seller = data["seller"]
            assert seller.get("name") == "Kalunga SA"
            assert "43.283.811/0047-32" in seller.get("cnpj", "")

    def test_scrape_valid_html_has_items(self, sample_nfce_html):
        """Scraped data should contain items list."""
        scraper = NfceScrapper()
        with open(sample_nfce_html, encoding="utf-8") as f:
            html_content = f.read()

        with responses.RequestsMock() as rsps:
            url = "https://www.nfce.fazenda.sp.gov.br/qrcode?p=35260243283811004732650010001055941001056011|2|1|1|abc123"
            rsps.add(responses.GET, url, body=html_content, status=200)
            data, status = scraper.scrape(url)

            assert "items" in data
            items = data["items"]
            assert len(items) > 0

            # Check first item structure
            item = items[0]
            assert "description" in item
            assert "quantity" in item
            assert "unit" in item
            assert "total_price" in item

    def test_item_unit_is_bare_code(self, sample_nfce_html):
        """Item unit should be bare code (e.g. 'BL'), not prefixed."""
        scraper = NfceScrapper()
        with open(sample_nfce_html, encoding="utf-8") as f:
            html_content = f.read()

        with responses.RequestsMock() as rsps:
            url = "https://www.nfce.fazenda.sp.gov.br/qrcode?p=35260243283811004732650010001055941001056011|2|1|1|abc123"
            rsps.add(responses.GET, url, body=html_content, status=200)
            data, status = scraper.scrape(url)

            items = data.get("items", [])
            for item in items:
                unit = item.get("unit", "")
                # Should not contain "UN: " prefix
                assert not unit.startswith("UN:"), f"Unit should not have 'UN: ' prefix: {unit}"

    def test_invoice_number_is_numeric_string(self, sample_nfce_html):
        """invoice_number should be a numeric string."""
        scraper = NfceScrapper()
        with open(sample_nfce_html, encoding="utf-8") as f:
            html_content = f.read()

        with responses.RequestsMock() as rsps:
            url = "https://www.nfce.fazenda.sp.gov.br/qrcode?p=35260243283811004732650010001055941001056011|2|1|1|abc123"
            rsps.add(responses.GET, url, body=html_content, status=200)
            data, status = scraper.scrape(url)

            invoice_num = data.get("invoice_number", "")
            assert invoice_num.isdigit(), f"invoice_number should be numeric: {invoice_num}"

    def test_series_is_numeric_string(self, sample_nfce_html):
        """series should be a numeric string."""
        scraper = NfceScrapper()
        with open(sample_nfce_html, encoding="utf-8") as f:
            html_content = f.read()

        with responses.RequestsMock() as rsps:
            url = "https://www.nfce.fazenda.sp.gov.br/qrcode?p=35260243283811004732650010001055941001056011|2|1|1|abc123"
            rsps.add(responses.GET, url, body=html_content, status=200)
            data, status = scraper.scrape(url)

            series = data.get("series", "")
            assert series.isdigit(), f"series should be numeric: {series}"

    def test_scrape_with_no_output_dir_does_not_save_file(self, sample_nfce_html, tmp_path):
        """Scraping without output_dir should not write a file."""
        scraper = NfceScrapper(output_dir=None)
        with open(sample_nfce_html, encoding="utf-8") as f:
            html_content = f.read()

        with responses.RequestsMock() as rsps:
            url = "https://www.nfce.fazenda.sp.gov.br/qrcode?p=35260243283811004732650010001055941001056011|2|1|1|abc123"
            rsps.add(responses.GET, url, body=html_content, status=200)
            data, status = scraper.scrape(url)

            assert status == "OK"
            # Verify no file is written (scraper uses self._output_dir internally)
            assert len(list(tmp_path.glob("*.json"))) == 0

    def test_scrape_with_output_dir_saves_file(self, sample_nfce_html, tmp_path):
        """Scraping with output_dir should write a JSON file."""
        scraper = NfceScrapper(output_dir=str(tmp_path))
        with open(sample_nfce_html, encoding="utf-8") as f:
            html_content = f.read()

        with responses.RequestsMock() as rsps:
            url = "https://www.nfce.fazenda.sp.gov.br/qrcode?p=35260243283811004732650010001055941001056011|2|1|1|abc123"
            rsps.add(responses.GET, url, body=html_content, status=200)
            data, status = scraper.scrape(url)

            assert status == "OK"
            # Verify file is written with access_key as filename
            json_files = list(tmp_path.glob("*.json"))
            assert len(json_files) > 0

    def test_scrape_totals_match_items_sum(self, sample_nfce_html):
        """Total should match sum of item prices."""
        scraper = NfceScrapper()
        with open(sample_nfce_html, encoding="utf-8") as f:
            html_content = f.read()

        with responses.RequestsMock() as rsps:
            url = "https://www.nfce.fazenda.sp.gov.br/qrcode?p=35260243283811004732650010001055941001056011|2|1|1|abc123"
            rsps.add(responses.GET, url, body=html_content, status=200)
            data, status = scraper.scrape(url)

            items = data.get("items", [])
            totals = data.get("totals", {})
            total = totals.get("total")

            # Convert string prices to float for comparison
            items_sum = sum(float(item.get("total_price", 0)) for item in items)
            total_value = float(total) if total else 0

            # Allow small floating point differences
            assert abs(items_sum - total_value) < 0.01


class TestNfceScrapperCancelledStatus:
    """Test handling of cancelled invoices."""

    def test_cancelled_invoice_returns_error(self):
        """Cancelled invoice should return error."""
        scraper = NfceScrapper()
        html_content = """
            <input id="hdfNotaCancelada" value="true" />
            <input id="hdfNotaDenegada" value="false" />
        """

        with responses.RequestsMock() as rsps:
            url = "https://www.nfce.fazenda.sp.gov.br/qrcode?p=35260243283811004732650010001055941001056011|2|1|1|abc123"
            rsps.add(responses.GET, url, body=html_content, status=200)
            data, status = scraper.scrape(url)

            assert data == {}
            assert "cancel" in status.lower() or "cancelada" in status.lower()


class TestNfceScrapperDeniedStatus:
    """Test handling of denied invoices."""

    def test_denied_invoice_returns_error(self):
        """Denied invoice should return error."""
        scraper = NfceScrapper()
        html_content = """
            <input id="hdfNotaCancelada" value="false" />
            <input id="hdfNotaDenegada" value="true" />
        """

        with responses.RequestsMock() as rsps:
            url = "https://www.nfce.fazenda.sp.gov.br/qrcode?p=35260243283811004732650010001055941001056011|2|1|1|abc123"
            rsps.add(responses.GET, url, body=html_content, status=200)
            data, status = scraper.scrape(url)

            assert data == {}
            assert "denie" in status.lower() or "denegada" in status.lower()
