import { Link, useSearchParams } from "react-router-dom";

function getDisplayMessage(rawMessage: string | null) {
  if (!rawMessage) {
    return "결제 승인에 실패했습니다. 다시 시도해 주세요.";
  }

  try {
    const parsed = JSON.parse(rawMessage) as {
      detail?: { message?: string };
      message?: string;
    };
    if (parsed.detail?.message) {
      return `${parsed.detail.message} 다시 시도해 주세요.`;
    }
    if (parsed.message) {
      return `${parsed.message} 다시 시도해 주세요.`;
    }
  } catch {
    return rawMessage;
  }

  return rawMessage;
}

export default function PaymentFailPage() {
  const [searchParams] = useSearchParams();
  const code = searchParams.get("code");
  const message = searchParams.get("message");
  const displayMessage = getDisplayMessage(message);

  return (
    <main className="result-shell">
      <section className="result-card fail-card">
        <div className="fail-hero">
          <div className="fail-icon" aria-hidden="true">
            <span />
            <span />
          </div>
          <h1>결제에 실패했습니다</h1>
          <p className="fail-copy">
            {displayMessage}
          </p>
        </div>

        <div className="fail-actions">
          <Link to="/" className="primary-button fail-button">
            재시도
          </Link>
        </div>
      </section>
    </main>
  );
}
