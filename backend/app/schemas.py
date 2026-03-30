from typing import Any

from pydantic import BaseModel, Field


class BillingAuthRequest(BaseModel):
    customer_key: str = Field(min_length=1, max_length=200)


class BillingMethodSummary(BaseModel):
    billing_key: str
    customer_key: str
    card_company: str | None = None
    card_number: str | None = None
    owner_type: str | None = None
    authenticated_at: str | None = None


class BillingMethodListResponse(BaseModel):
    items: list[BillingMethodSummary]


class BillingConfirmRequest(BaseModel):
    customer_key: str = Field(min_length=1, max_length=200)
    auth_key: str = Field(min_length=1)


class BillingConfirmResponse(BaseModel):
    billing_key: str
    method: BillingMethodSummary


class ChargeRequest(BaseModel):
    customer_key: str = Field(min_length=1, max_length=200)
    billing_key: str = Field(min_length=1)
    amount: int = Field(gt=0)
    order_name: str = Field(min_length=1, max_length=100)
    plan_name: str = Field(min_length=1, max_length=100)
    billing_cycle: str = Field(min_length=1, max_length=50)
    applied_start_date: str = Field(min_length=1, max_length=20)
    customer_email: str | None = None
    customer_name: str | None = None


class ChargeResponse(BaseModel):
    payment_key: str
    order_id: str
    status: str
    total_amount: int
    raw: dict[str, Any]


class PaymentSummary(BaseModel):
    order_id: str
    payment_key: str
    status: str
    total_amount: int
    plan_name: str
    billing_cycle: str
    payment_method: str
    subscription_start_date: str
    next_billing_date: str


class PlanSummary(BaseModel):
    name: str
    billing_cycle: str
    amount: int = Field(gt=0)
    applied_start_date: str


class DemoSessionResponse(BaseModel):
    customer_key: str
    success_url: str
    fail_url: str
    toss_client_key: str
    plan: PlanSummary


class PaymentSummaryResponse(BaseModel):
    payment: PaymentSummary
