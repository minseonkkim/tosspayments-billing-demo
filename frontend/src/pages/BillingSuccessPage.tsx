import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { confirmBilling } from "../api";

export default function BillingSuccessPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [message, setMessage] = useState("카드를 등록하는 중입니다.");
  const [error, setError] = useState("");

  useEffect(() => {
    async function run() {
      const authKey = searchParams.get("authKey");
      const customerKey = searchParams.get("customerKey");
      console.log("[Toss Billing] success redirect params", {
        authKey,
        customerKey,
        rawQuery: Object.fromEntries(searchParams.entries()),
      });

      if (!authKey || !customerKey) {
        setError("필수 파라미터가 없습니다.");
        return;
      }

      try {
        await confirmBilling(customerKey, authKey);
        setMessage("카드 등록이 완료되었습니다. 결제 화면으로 돌아갑니다.");
        window.setTimeout(() => {
          navigate("/", { replace: true });
        }, 1200);
      } catch (confirmError) {
        setError(confirmError instanceof Error ? confirmError.message : "빌링키 발급에 실패했습니다.");
      }
    }

    void run();
  }, [navigate, searchParams]);

  return (
    <main className="result-shell">
      <section className="result-card">
        <h1>카드 등록 결과</h1>
        {error ? <p className="feedback error">{error}</p> : <p>{message}</p>}
        <Link to="/" className="inline-link">
          결제 화면으로 이동
        </Link>
      </section>
    </main>
  );
}
