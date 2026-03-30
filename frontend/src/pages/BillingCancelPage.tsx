import { Navigate, useSearchParams } from "react-router-dom";

export default function BillingCancelPage() {
  const [searchParams] = useSearchParams();
  const code = searchParams.get("code");
  const message = searchParams.get("message");
  const nextParams = new URLSearchParams({ toast: "billing-canceled" });

  if (code) {
    nextParams.set("code", code);
  }

  if (message) {
    nextParams.set("message", message);
  }

  return <Navigate to={`/?${nextParams.toString()}`} replace />;
}
