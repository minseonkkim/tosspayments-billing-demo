import { Link, useSearchParams } from "react-router-dom";

export default function BillingCancelPage() {
  const [searchParams] = useSearchParams();
  const code = searchParams.get("code");
  const message = searchParams.get("message");

  return (
    <main className="result-shell">
      <section className="result-card cancel-card">
        <div className="cancel-hero">
          <div className="cancel-icon" aria-hidden="true">
            <span />
            <span />
          </div>
          <h1>결제를 취소했습니다</h1>
          <p className="cancel-copy">
            {message ?? "카드 추가가 중단되어 결제가 진행되지 않았습니다. 원하면 다시 시도할 수 있습니다."}
          </p>
        </div>

        <div className="cancel-actions">
          <Link to="/" className="primary-button cancel-button">
            결제 화면으로 돌아가기
          </Link>
        </div>
      </section>
    </main>
  );
}
