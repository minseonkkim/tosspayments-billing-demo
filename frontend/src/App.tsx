import { Navigate, Route, Routes } from "react-router-dom";
import BillingCancelPage from "./pages/BillingCancelPage";
import BillingFailPage from "./pages/BillingFailPage";
import BillingSuccessPage from "./pages/BillingSuccessPage";
import CheckoutPage from "./pages/CheckoutPage";
import PaymentFailPage from "./pages/PaymentFailPage";
import PaymentSuccessPage from "./pages/PaymentSuccessPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<CheckoutPage />} />
      <Route path="/billing/cancel" element={<BillingCancelPage />} />
      <Route path="/billing/success" element={<BillingSuccessPage />} />
      <Route path="/billing/fail" element={<BillingFailPage />} />
      <Route path="/payment/success" element={<PaymentSuccessPage />} />
      <Route path="/payment/fail" element={<PaymentFailPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
