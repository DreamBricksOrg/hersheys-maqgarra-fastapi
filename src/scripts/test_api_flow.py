import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import requests


def pretty(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False, default=str)


class ApiFlowTester:
    def __init__(self, base_url: str, api_key: str, device_id: str, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "x-api-key": api_key,
            "x-device-id": device_id,
        })

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def request(self, method: str, path: str, expected_status: int | None = None, **kwargs):
        url = self._url(path)
        print(f"\n>>> {method.upper()} {url}")
        if "json" in kwargs:
            print("payload:")
            print(pretty(kwargs["json"]))
        if "files" in kwargs:
            print("payload: <multipart/form-data>")

        resp = self.session.request(method, url, timeout=self.timeout, **kwargs)
        print(f"status: {resp.status_code}")
        try:
            data = resp.json()
            print(pretty(data))
        except Exception:
            data = resp.text
            print(data)

        if expected_status is not None and resp.status_code != expected_status:
            raise RuntimeError(
                f"Expected {expected_status} for {method.upper()} {path}, got {resp.status_code}"
            )
        return resp, data

    def run(
        self,
        qr_value: str,
        tag_key: str,
        image_path: str | None = None,
        override_bars: int | None = None,
        deactivate_reason: str | None = "used_for_play",
    ):
        # 1. alive
        self.request("GET", "/alive", expected_status=200)

        # 2. ver estado inicial da tag
        self.request("GET", f"/api/tags/{tag_key}", expected_status=200)

        # 3. validar nota por QR
        _, qr_receipt = self.request(
            "POST",
            "/api/receipts/qr",
            expected_status=200,
            json={"qr_value": qr_value},
        )
        qr_receipt_id = qr_receipt["receipt_id"]

        # 4. consultar nota recém-criada
        self.request("GET", f"/api/receipts/{qr_receipt_id}", expected_status=200)

        # 5. opcional: rota de imagem
        image_receipt_id = None
        if image_path:
            path = Path(image_path)
            if not path.exists():
                raise FileNotFoundError(f"Image file not found: {image_path}")
            with path.open("rb") as f:
                _, img_receipt = self.request(
                    "POST",
                    "/api/receipts/image",
                    expected_status=200,
                    files={"image": (path.name, f, "image/jpeg")},
                )
            image_receipt_id = img_receipt["receipt_id"]
            self.request("GET", f"/api/receipts/{image_receipt_id}", expected_status=200)

        # 6. override opcional
        if override_bars is None:
            override_bars = int(qr_receipt.get("found_bars", 0)) + 1

        _, overridden = self.request(
            "POST",
            "/api/receipts/override",
            expected_status=200,
            json={
                "receipt_id": qr_receipt_id,
                "final_bars": override_bars,
                "reason": "teste de fluxo automatizado",
            },
        )

        # 7. liberar tag para uso
        self.request(
            "POST",
            f"/api/tags/{tag_key}/activate",
            expected_status=200,
            json={"reason": "liberação para teste automatizado"},
        )

        # 8. ver estado da tag após liberação
        self.request("GET", f"/api/tags/{tag_key}", expected_status=200)

        # 9. associar tag à nota de QR
        self.request(
            "POST",
            "/api/tags/associate",
            expected_status=200,
            json={
                "receipt_ids": [qr_receipt_id],
                "tags": [tag_key],
            },
        )

        # 10. ver estado da tag após associação
        self.request("GET", f"/api/tags/{tag_key}", expected_status=200)

        # 11. desativar tag
        self.request(
            "POST",
            f"/api/tags/{tag_key}/deactivate",
            expected_status=200,
            json={"reason": deactivate_reason},
        )

        # 12. ver estado final da tag
        self.request("GET", f"/api/tags/{tag_key}", expected_status=200)

        print("\nFluxo finalizado com sucesso.")
        print("\nResumo:")
        print(pretty({
            "qr_receipt_id": qr_receipt_id,
            "image_receipt_id": image_receipt_id,
            "override_final_bars": overridden.get("final_bars"),
            "tag_key": tag_key,
        }))


def main():
    parser = argparse.ArgumentParser(description="Testa o fluxo atual da API Capibarra")
    parser.add_argument("--base-url", default=os.getenv("BASE_URL", "http://localhost:8000"))
    parser.add_argument("--api-key", default=os.getenv("API_KEY"))
    parser.add_argument("--device-id", default=os.getenv("DEVICE_ID", "tablet-01"))
    parser.add_argument("--qr-value", default=os.getenv("QR_VALUE"))
    parser.add_argument("--tag-key", default=os.getenv("TAG_KEY"))
    parser.add_argument("--image-path", default=os.getenv("IMAGE_PATH"))
    parser.add_argument("--override-bars", type=int, default=None)
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()

    missing = []
    if not args.api_key:
        missing.append("--api-key or API_KEY")
    if not args.qr_value:
        missing.append("--qr-value or QR_VALUE")
    if not args.tag_key:
        missing.append("--tag-key or TAG_KEY")

    if missing:
        print("Missing required parameters:")
        for item in missing:
            print(f"- {item}")
        sys.exit(2)

    tester = ApiFlowTester(
        base_url=args.base_url,
        api_key=args.api_key,
        device_id=args.device_id,
        timeout=args.timeout,
    )
    tester.run(
        qr_value=args.qr_value,
        tag_key=args.tag_key,
        image_path=args.image_path,
        override_bars=args.override_bars,
    )


if __name__ == "__main__":
    main()
