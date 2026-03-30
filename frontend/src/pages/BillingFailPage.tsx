import { Link, Navigate, useSearchParams } from "react-router-dom";

function getDisplayMessage(rawMessage: string | null) {
  if (!rawMessage) {
    return "카드 등록 중 문제가 발생했습니다. 잠시 후 다시 시도해 주세요.";
  }

  try {
    const parsed = JSON.parse(rawMessage) as {
      message?: string;
      detail?: { message?: string };
    };
    if (parsed.detail?.message) {
      return parsed.detail.message;
    }
    if (parsed.message) {
      return parsed.message;
    }
  } catch {
    return rawMessage;
  }

  return rawMessage;
}

export default function BillingFailPage() {
  const [searchParams] = useSearchParams();
  const code = searchParams.get("code");
  const message = searchParams.get("message");
  const displayMessage = getDisplayMessage(message);

  console.log("[Toss Billing] fail redirect params", {
    code,
    message,
    rawQuery: Object.fromEntries(searchParams.entries()),
  });

  if (code === "PAY_PROCESS_CANCELED" || code === "USER_CANCEL") {
    const nextParams = new URLSearchParams();
    if (code) {
      nextParams.set("code", code);
    }
    if (message) {
      nextParams.set("message", message);
    }
    return <Navigate to={`/billing/cancel?${nextParams.toString()}`} replace />;
  }

  return (
    <main className="result-shell">
      <section className="result-card fail-card">
        <div className="fail-hero">
          <div className="fail-icon" aria-hidden="true">
            <span />
            <span />
          </div>
          <h1>카드 등록에 실패했습니다</h1>
          <p className="fail-copy">{displayMessage}</p>
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
