import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { BillingMethod, DemoSession, chargePayment, getBillingMethods, getDemoSession } from "../api";

const currencyFormatter = new Intl.NumberFormat("ko-KR");

const cardCompanyMap: Record<string, string> = {
  "3K": "기업BC",
  "46": "광주은행",
  "71": "롯데카드",
  "30": "한국산업은행",
  "31": "BC카드",
  "51": "삼성카드",
  "38": "새마을금고",
  "41": "신한카드",
  "62": "신협",
  "36": "씨티카드",
  "33": "우리BC카드",
  "W1": "우리카드",
  "37": "우체국예금보험",
  "39": "저축은행중앙회",
  "35": "전북은행",
  "42": "제주은행",
  "15": "카카오뱅크",
  "3A": "케이뱅크",
  "24": "토스뱅크",
  "21": "하나카드",
  "61": "현대카드",
  "11": "KB국민카드",
  "34": "Sh수협은행",
  "91": "NH농협카드",
};

function getCardCompanyLabel(method: BillingMethod) {
  if (!method.card_company) {
    return "등록 카드";
  }

  return cardCompanyMap[method.card_company] ?? method.card_company;
}

function getCardNumberLabel(method: BillingMethod) {
  if (method.card_number) {
    return method.card_number;
  }

  return `billingKey: ${method.billing_key.slice(0, 12)}...`;
}

function getPaymentFailMessage(error: unknown) {
  const fallbackMessage = "결제 승인에 실패했습니다.";
  if (!(error instanceof Error)) {
    return fallbackMessage;
  }

  try {
    const parsed = JSON.parse(error.message) as {
      detail?: { message?: string };
    };
    const detailMessage = parsed.detail?.message;
    if (detailMessage) {
      return `${detailMessage} 다시 시도해주세요.`;
    }
  } catch {
    return error.message || fallbackMessage;
  }

  return error.message || fallbackMessage;
}

function isBillingCancelError(error: unknown) {
  if (!(error instanceof Error)) {
    return false;
  }

  const normalized = error.message.toLowerCase();
  return normalized.includes("cancel") || normalized.includes("canceled") || normalized.includes("취소");
}

export default function CheckoutPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [session, setSession] = useState<DemoSession | null>(null);
  const [methods, setMethods] = useState<BillingMethod[]>([]);
  const [selectedBillingKey, setSelectedBillingKey] = useState("");
  const [customerName, setCustomerName] = useState("홍길동");
  const [customerEmail, setCustomerEmail] = useState("demo@example.com");
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isTermsChecked, setIsTermsChecked] = useState(false);
  const [error, setError] = useState("");
  const [toastMessage, setToastMessage] = useState("");
  const planName = session?.plan.name ?? "-";
  const billingCycle = session?.plan.billing_cycle ?? "-";
  const appliedStartDate = session?.plan.applied_start_date ?? "-";
  const amount = session?.plan.amount ?? 0;

  useEffect(() => {
    if (searchParams.get("toast") !== "billing-canceled") {
      return;
    }

    setToastMessage(searchParams.get("message") ?? "카드 등록이 취소되었습니다.");
    setSearchParams({}, { replace: true });
  }, [searchParams, setSearchParams]);

  useEffect(() => {
    if (!toastMessage) {
      return;
    }

    const timer = window.setTimeout(() => {
      setToastMessage("");
    }, 3500);

    return () => {
      window.clearTimeout(timer);
    };
  }, [toastMessage]);

  useEffect(() => {
    async function bootstrap() {
      try {
        const demoSession = await getDemoSession();
        const billingMethods = await getBillingMethods(demoSession.customer_key);
        setSession(demoSession);
        setMethods(billingMethods);
        setSelectedBillingKey(billingMethods[0]?.billing_key ?? "");
      } catch (fetchError) {
        setError(fetchError instanceof Error ? fetchError.message : "초기 정보를 불러오지 못했습니다.");
      } finally {
        setIsLoading(false);
      }
    }

    void bootstrap();
  }, []);

  async function refreshMethods(customerKey: string) {
    const billingMethods = await getBillingMethods(customerKey);
    setMethods(billingMethods);
    setSelectedBillingKey((current) => current || billingMethods[0]?.billing_key || "");
  }

  async function handleAddCard() {
    if (!session) {
      return;
    }

    setError("");
    const tossPayments = window.TossPayments(session.toss_client_key);
    const payment = tossPayments.payment({ customerKey: session.customer_key });
    const isMobile = window.matchMedia("(max-width: 768px)").matches;

    try {
      await payment.requestBillingAuth({
        method: "CARD",
        successUrl: session.success_url,
        failUrl: session.fail_url,
        customerName,
        customerEmail,
        windowTarget: isMobile ? "self" : "iframe",
      });
    } catch (sdkError) {
      if (isBillingCancelError(sdkError)) {
        setToastMessage("카드 등록이 취소되었습니다.");
        return;
      }

      setError(sdkError instanceof Error ? sdkError.message : "카드 등록창을 열지 못했습니다.");
    }
  }

  async function handlePay() {
    if (!session || !selectedBillingKey) {
      return;
    }

    setIsSubmitting(true);
    setError("");
    try {
      const result = await chargePayment({
        customer_key: session.customer_key,
        billing_key: selectedBillingKey,
        amount,
        order_name: `${planName} 요금제`,
        plan_name: planName,
        billing_cycle: billingCycle,
        applied_start_date: appliedStartDate,
        customer_email: customerEmail,
        customer_name: customerName,
      });
      await refreshMethods(session.customer_key);
      const nextParams = new URLSearchParams({
        orderId: result.order_id,
      });
      navigate(`/payment/success?${nextParams.toString()}`);
    } catch (chargeError) {
      const message = getPaymentFailMessage(chargeError);
      const nextParams = new URLSearchParams({
        code: "PAYMENT_FAILED",
        message,
      });
      navigate(`/payment/fail?${nextParams.toString()}`);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="page-shell">
      {toastMessage ? (
        <div className="toast-message" role="status" aria-live="polite">
          <span>{toastMessage}</span>
          <button
            type="button"
            className="toast-close"
            onClick={() => setToastMessage("")}
            aria-label="토스트 닫기"
          >
            닫기
          </button>
        </div>
      ) : null}

      <section className="payment-panel">
        <div className="panel-header">
          <div>
            <h1>결제하기</h1>
          </div>
        </div>

        <div className="grid">
          <div className="card">
            <h2>요금제 정보</h2>
            <div className="summary-list">
              <div className="summary-row">
                <span>요금제</span>
                <strong>{planName}</strong>
              </div>
              <div className="summary-row">
                <span>청구 주기</span>
                <strong>{billingCycle}</strong>
              </div>
              <div className="summary-row">
                <span>적용 시작일</span>
                <strong>{appliedStartDate}</strong>
              </div>
              <div className="summary-row">
                <span>월 요금</span>
                <strong>{currencyFormatter.format(amount)}원</strong>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <h2>결제 수단</h2>
            </div>

            {isLoading ? <p className="muted">저장된 카드를 불러오는 중입니다.</p> : null}

            {!isLoading && methods.length === 0 ? (
              <div className="empty-state">
                <p>등록된 카드가 없습니다.</p>
                <span>먼저 카드를 등록한 뒤 자동결제를 진행하세요.</span>
              </div>
            ) : null}

            <div className="method-strip">
              {methods.map((method) => (
                <label key={method.billing_key} className={`method-item ${selectedBillingKey === method.billing_key ? "selected" : ""}`}>
                  <input
                    type="radio"
                    name="billingKey"
                    checked={selectedBillingKey === method.billing_key}
                    onChange={() => setSelectedBillingKey(method.billing_key)}
                  />
                  <div className="method-content">
                    <span className="method-chip">등록 카드</span>
                    <strong>{getCardCompanyLabel(method)}</strong>
                    <p>{getCardNumberLabel(method)}</p>
                  </div>
                </label>
              ))}

              <button
                type="button"
                className="add-card-tile"
                onClick={handleAddCard}
                disabled={!session}
              >
                <span className="add-card-plus">+</span>
                <strong>카드 추가</strong>
                <p>새 결제수단 등록</p>
              </button>
            </div>

            <div className="terms-box">
              <label className="terms-label">
                <input
                  className="terms-checkbox-input"
                  type="checkbox"
                  checked={isTermsChecked}
                  onChange={(event) => setIsTermsChecked(event.target.checked)}
                />
                <span className="terms-checkbox" aria-hidden="true" />
                <span>결제대행 서비스 이용약관과 자동결제 진행에 동의합니다.</span>
              </label>
              <p className="terms-copy">
                등록된 카드로 즉시 결제가 진행되며, 실제 서비스에서는 필수 약관 전문 링크를 함께 제공해야 합니다.
              </p>
            </div>
          </div>
        </div>

        {error ? <div className="feedback error">{error}</div> : null}

        <button
          type="button"
          className="primary-button"
          onClick={handlePay}
          disabled={!selectedBillingKey || !isTermsChecked || isSubmitting || amount <= 0}
        >
          {isSubmitting ? "결제 승인 중..." : "결제하기"}
        </button>
      </section>
    </main>
  );
}
