from contextlib import asynccontextmanager
from calendar import monthrange
from datetime import date

import httpx
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, get_cors_origins, get_settings
from app.schemas import (
    BillingMethodSummary,
    BillingConfirmRequest,
    BillingConfirmResponse,
    BillingMethodListResponse,
    ChargeRequest,
    ChargeResponse,
    DemoSessionResponse,
    PaymentSummary,
    PaymentSummaryResponse,
    PlanSummary,
)
from app.store import BillingStore, PaymentStore
from app.toss import TossBillingClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.billing_store = BillingStore(settings.store_path)
    app.state.payment_store = PaymentStore(settings.payment_store_path)
    app.state.toss_client = TossBillingClient(settings)
    yield


app = FastAPI(title="Toss Billing Demo", lifespan=lifespan)


def get_store() -> BillingStore:
    return app.state.billing_store


def get_toss_client() -> TossBillingClient:
    return app.state.toss_client


def get_payment_store() -> PaymentStore:
    return app.state.payment_store


app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(get_settings()),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/demo/session", response_model=DemoSessionResponse)
async def get_demo_session(settings: Settings = Depends(get_settings)) -> DemoSessionResponse:
    return DemoSessionResponse(
        customer_key="demo-customer",
        success_url=settings.frontend_success_url,
        fail_url=settings.frontend_fail_url,
        toss_client_key=settings.toss_client_key,
        plan=PlanSummary(
            name="스탠다드",
            billing_cycle="매월",
            amount=15000,
            applied_start_date=date.today().isoformat(),
        ),
    )


@app.get("/api/billing-methods/{customer_key}", response_model=BillingMethodListResponse)
async def list_billing_methods(
    customer_key: str,
    store: BillingStore = Depends(get_store),
) -> BillingMethodListResponse:
    return BillingMethodListResponse(items=store.list_methods(customer_key))


@app.post("/api/billing/confirm", response_model=BillingConfirmResponse)
async def confirm_billing(
    request: BillingConfirmRequest,
    store: BillingStore = Depends(get_store),
    toss_client: TossBillingClient = Depends(get_toss_client),
) -> BillingConfirmResponse:
    try:
        billing_key, method = await toss_client.issue_billing_key(
            auth_key=request.auth_key,
            customer_key=request.customer_key,
        )
    except httpx.HTTPStatusError as exc:
        detail = exc.response.json() if exc.response.content else {"message": "Toss API error"}
        raise HTTPException(status_code=exc.response.status_code, detail=detail) from exc

    store.save_method(method)
    return BillingConfirmResponse(billing_key=billing_key, method=method)


@app.post("/api/payments/charge", response_model=ChargeResponse)
async def charge_payment(
    request: ChargeRequest,
    store: BillingStore = Depends(get_store),
    payment_store: PaymentStore = Depends(get_payment_store),
    toss_client: TossBillingClient = Depends(get_toss_client),
) -> ChargeResponse:
    methods = store.list_methods(request.customer_key)
    selected_method = next((method for method in methods if method.billing_key == request.billing_key), None)
    if not selected_method:
        raise HTTPException(status_code=404, detail="Billing method not found for customer")

    try:
        result = await toss_client.charge(request)
    except httpx.HTTPStatusError as exc:
        detail = exc.response.json() if exc.response.content else {"message": "Toss API error"}
        raise HTTPException(status_code=exc.response.status_code, detail=detail) from exc

    payment_store.save_payment(
        PaymentSummary(
            order_id=result["orderId"],
            payment_key=result["paymentKey"],
            status=result["status"],
            total_amount=result["totalAmount"],
            plan_name=request.plan_name,
            billing_cycle=request.billing_cycle,
            payment_method=format_payment_method_label(selected_method),
            subscription_start_date=request.applied_start_date,
            next_billing_date=calculate_next_billing_date(request.applied_start_date),
        )
    )

    return ChargeResponse(
        payment_key=result["paymentKey"],
        order_id=result["orderId"],
        status=result["status"],
        total_amount=result["totalAmount"],
        raw=result,
    )


@app.get("/api/payments/{order_id}", response_model=PaymentSummaryResponse)
async def get_payment_summary(
    order_id: str,
    payment_store: PaymentStore = Depends(get_payment_store),
) -> PaymentSummaryResponse:
    payment = payment_store.get_payment(order_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return PaymentSummaryResponse(payment=payment)


def format_payment_method_label(method: BillingMethodSummary) -> str:
    card_company = method.card_company or "등록 카드"
    if method.card_number:
        return f"{card_company} {method.card_number}"
    return card_company


def calculate_next_billing_date(start_date: str) -> str:
    try:
        year_text, month_text, day_text = start_date.split("-")
        year = int(year_text)
        month = int(month_text)
        day = int(day_text)
    except ValueError:
        return start_date

    next_month = month + 1
    next_year = year
    if next_month > 12:
        next_month = 1
        next_year += 1

    last_day = monthrange(next_year, next_month)[1]
    next_day = min(day, last_day)
    return date(next_year, next_month, next_day).isoformat()
