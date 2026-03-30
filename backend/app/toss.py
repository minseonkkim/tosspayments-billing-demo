import base64
import logging
from uuid import uuid4

import httpx

from app.config import Settings
from app.schemas import BillingMethodSummary, ChargeRequest
from app.store import format_card_number

logger = logging.getLogger(__name__)


class TossBillingClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        credential = f"{settings.toss_secret_key}:".encode("utf-8")
        self.auth_header = base64.b64encode(credential).decode("utf-8")

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Basic {self.auth_header}",
            "Content-Type": "application/json",
        }

    async def issue_billing_key(
        self,
        *,
        auth_key: str,
        customer_key: str,
    ) -> tuple[str, BillingMethodSummary]:
        payload = {
            "authKey": auth_key,
            "customerKey": customer_key,
        }
        async with httpx.AsyncClient(base_url=self.settings.toss_api_base_url, timeout=15.0) as client:
            response = await client.post(
                "/v1/billing/authorizations/issue",
                json=payload,
                headers=self._headers,
            )
        response.raise_for_status()
        data = response.json()
        billing_key = data["billingKey"]
        card = data.get("card", {})
        summary = BillingMethodSummary(
            billing_key=billing_key,
            customer_key=customer_key,
            card_company=card.get("issuerCode") or card.get("company"),
            card_number=format_card_number(card.get("number")),
            owner_type=card.get("ownerType"),
            authenticated_at=data.get("authenticatedAt"),
        )
        return billing_key, summary

    async def charge(self, request: ChargeRequest) -> dict:
        payload = {
            "customerKey": request.customer_key,
            "amount": request.amount,
            "orderId": uuid4().hex,
            "orderName": request.order_name,
        }
        if request.customer_email:
            payload["customerEmail"] = request.customer_email
        if request.customer_name:
            payload["customerName"] = request.customer_name

        headers = dict(self._headers)
        if self.settings.toss_test_code:
            headers["TossPayments-Test-Code"] = self.settings.toss_test_code

        logger.info(
            "[Toss Billing] charge request test code config=%r header=%r order_name=%r billing_key_prefix=%s",
            self.settings.toss_test_code,
            headers.get("TossPayments-Test-Code"),
            request.order_name,
            request.billing_key[:8],
        )

        async with httpx.AsyncClient(base_url=self.settings.toss_api_base_url, timeout=15.0) as client:
            response = await client.post(
                f"/v1/billing/{request.billing_key}",
                json=payload,
                headers=headers,
            )
        response.raise_for_status()
        return response.json()
