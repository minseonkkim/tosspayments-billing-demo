import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from calendar import monthrange
from datetime import date, timedelta

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
    RecurringChargeResult,
    RecurringChargeRunResponse,
    SubscriptionListResponse,
    SubscriptionSummary,
)
from app.store import BillingStore, PaymentStore, SubscriptionStore
from app.toss import TossBillingClient

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.billing_store = BillingStore(settings.store_path)
    app.state.payment_store = PaymentStore(settings.payment_store_path)
    app.state.subscription_store = SubscriptionStore(settings.subscription_store_path)
    app.state.toss_client = TossBillingClient(settings)
    app.state.subscription_job_lock = asyncio.Lock()
    scheduler_task = asyncio.create_task(recurring_billing_loop(app))
    yield
    scheduler_task.cancel()
    with suppress(asyncio.CancelledError):
        await scheduler_task


app = FastAPI(title="Toss Billing Demo", lifespan=lifespan)


def get_store() -> BillingStore:
    return app.state.billing_store


def get_toss_client() -> TossBillingClient:
    return app.state.toss_client


def get_payment_store() -> PaymentStore:
    return app.state.payment_store


def get_subscription_store() -> SubscriptionStore:
    return app.state.subscription_store


def get_subscription_job_lock() -> asyncio.Lock:
    return app.state.subscription_job_lock


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
    subscription_store: SubscriptionStore = Depends(get_subscription_store),
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
        build_payment_summary(
            result=result,
            plan_name=request.plan_name,
            billing_cycle=request.billing_cycle,
            payment_method=format_payment_method_label(selected_method),
            subscription_start_date=request.applied_start_date,
            next_billing_date=calculate_next_billing_date(request.applied_start_date),
        )
    )
    subscription_store.save_subscription(
        SubscriptionSummary(
            customer_key=request.customer_key,
            billing_key=request.billing_key,
            plan_name=request.plan_name,
            billing_cycle=request.billing_cycle,
            amount=request.amount,
            order_name=request.order_name,
            payment_method=format_payment_method_label(selected_method),
            subscription_start_date=request.applied_start_date,
            next_billing_date=calculate_next_billing_date(request.applied_start_date),
            customer_email=request.customer_email,
            customer_name=request.customer_name,
            last_payment_key=result["paymentKey"],
            last_order_id=result["orderId"],
            last_billed_at=date.today().isoformat(),
            retry_count=0,
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


@app.get("/api/subscriptions/{customer_key}", response_model=SubscriptionListResponse)
async def list_subscriptions(
    customer_key: str,
    subscription_store: SubscriptionStore = Depends(get_subscription_store),
) -> SubscriptionListResponse:
    return SubscriptionListResponse(items=subscription_store.list_subscriptions(customer_key))


@app.post("/api/subscriptions/run-due", response_model=RecurringChargeRunResponse)
async def run_due_subscriptions(
    store: BillingStore = Depends(get_store),
    payment_store: PaymentStore = Depends(get_payment_store),
    subscription_store: SubscriptionStore = Depends(get_subscription_store),
    toss_client: TossBillingClient = Depends(get_toss_client),
    subscription_job_lock: asyncio.Lock = Depends(get_subscription_job_lock),
) -> RecurringChargeRunResponse:
    async with subscription_job_lock:
        return await run_due_subscriptions_once(
            store=store,
            payment_store=payment_store,
            subscription_store=subscription_store,
            toss_client=toss_client,
        )


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


def build_payment_summary(
    *,
    result: dict,
    plan_name: str,
    billing_cycle: str,
    payment_method: str,
    subscription_start_date: str,
    next_billing_date: str,
) -> PaymentSummary:
    return PaymentSummary(
        order_id=result["orderId"],
        payment_key=result["paymentKey"],
        status=result["status"],
        total_amount=result["totalAmount"],
        plan_name=plan_name,
        billing_cycle=billing_cycle,
        payment_method=payment_method,
        subscription_start_date=subscription_start_date,
        next_billing_date=next_billing_date,
    )


def parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def should_process_subscription(subscription: SubscriptionSummary, today: date) -> bool:
    if subscription.status != "active":
        return False

    retry_date = parse_iso_date(subscription.next_retry_date)
    if retry_date and retry_date <= today:
        return True

    next_billing_date = parse_iso_date(subscription.next_billing_date)
    if not next_billing_date:
        return False

    return next_billing_date <= today


async def recurring_billing_loop(app: FastAPI) -> None:
    settings = get_settings()
    await asyncio.sleep(1)
    while True:
        try:
            async with app.state.subscription_job_lock:
                await run_due_subscriptions_once(
                    store=app.state.billing_store,
                    payment_store=app.state.payment_store,
                    subscription_store=app.state.subscription_store,
                    toss_client=app.state.toss_client,
                )
        except Exception:
            logger.exception("Recurring billing loop failed")

        await asyncio.sleep(max(settings.recurring_poll_interval_seconds, 10))


async def run_due_subscriptions_once(
    *,
    store: BillingStore,
    payment_store: PaymentStore,
    subscription_store: SubscriptionStore,
    toss_client: TossBillingClient,
) -> RecurringChargeRunResponse:
    today = date.today()
    items: list[RecurringChargeResult] = []

    for subscription in subscription_store.list_subscriptions():
        if not should_process_subscription(subscription, today):
            continue

        methods = store.list_methods(subscription.customer_key)
        selected_method = next((method for method in methods if method.billing_key == subscription.billing_key), None)
        payment_method = (
            format_payment_method_label(selected_method)
            if selected_method
            else subscription.payment_method
        )
        request = ChargeRequest(
            customer_key=subscription.customer_key,
            billing_key=subscription.billing_key,
            amount=subscription.amount,
            order_name=subscription.order_name,
            plan_name=subscription.plan_name,
            billing_cycle=subscription.billing_cycle,
            applied_start_date=subscription.subscription_start_date,
            customer_email=subscription.customer_email,
            customer_name=subscription.customer_name,
        )

        try:
            result = await toss_client.charge(request)
        except httpx.HTTPStatusError as exc:
            detail = exc.response.json() if exc.response.content else {"message": "Toss API error"}
            message = detail.get("message") if isinstance(detail, dict) else str(detail)
            subscription_store.save_subscription(
                subscription.model_copy(
                    update={
                        "payment_method": payment_method,
                        "last_failed_at": today.isoformat(),
                        "last_failure_message": message,
                        "retry_count": subscription.retry_count + 1,
                        "next_retry_date": (today + timedelta(days=1)).isoformat(),
                    }
                )
            )
            items.append(
                RecurringChargeResult(
                    billing_key=subscription.billing_key,
                    customer_key=subscription.customer_key,
                    status="failed",
                    message=message,
                )
            )
            continue

        next_billing_date = calculate_next_billing_date(subscription.next_billing_date)
        payment_store.save_payment(
            build_payment_summary(
                result=result,
                plan_name=subscription.plan_name,
                billing_cycle=subscription.billing_cycle,
                payment_method=payment_method,
                subscription_start_date=subscription.subscription_start_date,
                next_billing_date=next_billing_date,
            )
        )
        subscription_store.save_subscription(
            subscription.model_copy(
                update={
                    "payment_method": payment_method,
                    "next_billing_date": next_billing_date,
                    "last_payment_key": result["paymentKey"],
                    "last_order_id": result["orderId"],
                    "last_billed_at": today.isoformat(),
                    "last_failed_at": None,
                    "last_failure_message": None,
                    "retry_count": 0,
                    "next_retry_date": None,
                }
            )
        )
        items.append(
            RecurringChargeResult(
                billing_key=subscription.billing_key,
                customer_key=subscription.customer_key,
                status="charged",
                order_id=result["orderId"],
                payment_key=result["paymentKey"],
            )
        )

    return RecurringChargeRunResponse(
        processed_at=today.isoformat(),
        processed_count=len(items),
        items=items,
    )
