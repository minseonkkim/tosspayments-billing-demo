import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { getPaymentSummary, PaymentSummary } from "../api";

const currencyFormatter = new Intl.NumberFormat("ko-KR");

export default function PaymentSuccessPage() {
  const [searchParams] = useSearchParams();
  const [payment, setPayment] = useState<PaymentSummary | null>(null);
  const [error, setError] = useState("");
  const orderId = searchParams.get("orderId");

  useEffect(() => {
    async function loadPayment() {
      if (!orderId) {
        setError("주문 정보를 찾을 수 없습니다.");
        return;
      }

      try {
        const paymentSummary = await getPaymentSummary(orderId);
        setPayment(paymentSummary);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "결제 정보를 불러오지 못했습니다.");
      }
    }

    void loadPayment();
  }, [orderId]);

  const formattedAmount = payment
    ? `${currencyFormatter.format(payment.total_amount)}원`
    : "-";

  return (
    <main className="result-shell">
      <section className="result-card success-card">
        <div className="success-hero">
          <div className="success-icon" aria-hidden="true">
            <span />
          </div>
          <h1>결제가 완료되었습니다</h1>
        </div>

        {error ? <p className="feedback error">{error}</p> : null}
        {!error && !payment ? <p className="muted">결제 정보를 불러오는 중입니다.</p> : null}

        {payment ? (
          <div className="success-summary">
            <div className="summary-list">
              <div className="summary-row">
                <span>요금제명</span>
                <strong>{payment.plan_name}</strong>
              </div>
              <div className="summary-row">
                <span>청구 주기</span>
                <strong>{payment.billing_cycle}</strong>
              </div>
              <div className="summary-row">
                <span>결제 수단</span>
                <strong>{payment.payment_method}</strong>
              </div>
              <div className="summary-row">
                <span>결제 금액</span>
                <strong>{formattedAmount}</strong>
              </div>
              <div className="summary-row">
                <span>구독 시작일</span>
                <strong>{payment.subscription_start_date}</strong>
              </div>
              <div className="summary-row">
                <span>다음 결제일</span>
                <strong>{payment.next_billing_date}</strong>
              </div>
            </div>
          </div>
        ) : null}

        <div className="success-actions">
          <Link to="/" className="primary-button success-button">
            결제 화면으로 이동
          </Link>
        </div>
      </section>
    </main>
  );
}
