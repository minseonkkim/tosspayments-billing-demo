import json
from pathlib import Path

from app.schemas import BillingMethodSummary, PaymentSummary


def format_card_number(card_number: str | None) -> str | None:
    if not card_number:
        return card_number

    normalized = card_number.replace(" ", "").replace("-", "")
    if len(normalized) < 8:
        return card_number

    return f"{normalized[:4]} **** **** {normalized[-4:]}"


class BillingStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("{}", encoding="utf-8")

    def _read(self) -> dict[str, list[dict]]:
        raw = self.path.read_text(encoding="utf-8").strip()
        if not raw:
            return {}
        return json.loads(raw)

    def _write(self, data: dict[str, list[dict]]) -> None:
        self.path.write_text(
            json.dumps(data, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )

    def list_methods(self, customer_key: str) -> list[BillingMethodSummary]:
        data = self._read()
        items = data.get(customer_key, [])
        return [
            BillingMethodSummary(
                **{
                    **item,
                    "card_number": format_card_number(item.get("card_number")),
                }
            )
            for item in items
        ]

    def save_method(self, method: BillingMethodSummary) -> None:
        data = self._read()
        items = data.get(method.customer_key, [])
        filtered = [item for item in items if item["billing_key"] != method.billing_key]
        filtered.append(
            method.model_copy(
                update={"card_number": format_card_number(method.card_number)}
            ).model_dump()
        )
        data[method.customer_key] = filtered
        self._write(data)


class PaymentStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("{}", encoding="utf-8")

    def _read(self) -> dict[str, dict]:
        raw = self.path.read_text(encoding="utf-8").strip()
        if not raw:
            return {}
        return json.loads(raw)

    def _write(self, data: dict[str, dict]) -> None:
        self.path.write_text(
            json.dumps(data, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )

    def get_payment(self, order_id: str) -> PaymentSummary | None:
        data = self._read()
        item = data.get(order_id)
        if not item:
            return None
        return PaymentSummary(**item)

    def save_payment(self, payment: PaymentSummary) -> None:
        data = self._read()
        data[payment.order_id] = payment.model_dump()
        self._write(data)
