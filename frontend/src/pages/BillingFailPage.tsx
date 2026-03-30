import { Link, Navigate, useSearchParams } from "react-router-dom";

export default function BillingFailPage() {
  const [searchParams] = useSearchParams();
  const code = searchParams.get("code");
  const message = searchParams.get("message");

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
      <section className="result-card">
        <h1>카드 등록 실패</h1>
        <p className="feedback error">
          {code ? `에러 코드: ${code}` : "에러 코드가 없습니다."}
          <br />
          {message ?? "알 수 없는 오류"}
        </p>
        <Link to="/" className="inline-link">
          다시 시도하기
        </Link>
      </section>
    </main>
  );
}
