const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export type DemoSession = {
  customer_key: string;
  success_url: string;
  fail_url: string;
  toss_client_key: string;
  plan: {
    name: string;
    billing_cycle: string;
    amount: number;
    applied_start_date: string;
  };
};

export type BillingMethod = {
  billing_key: string;
  customer_key: string;
  card_company: string | null;
  card_number: string | null;
  owner_type: string | null;
  authenticated_at: string | null;
};

export type ChargeResult = {
  payment_key: string;
  order_id: string;
  status: string;
  total_amount: number;
  raw: Record<string, unknown>;
};

export type PaymentSummary = {
  order_id: string;
  payment_key: string;
  status: string;
  total_amount: number;
  plan_name: string;
  billing_cycle: string;
  payment_method: string;
  subscription_start_date: string;
  next_billing_date: string;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(errorBody || "Request failed");
  }

  return (await response.json()) as T;
}

export function getDemoSession(): Promise<DemoSession> {
  return request("/api/demo/session");
}

export async function getPaymentSummary(orderId: string): Promise<PaymentSummary> {
  const response = await request<{ payment: PaymentSummary }>(`/api/payments/${orderId}`);
  return response.payment;
}

export async function getBillingMethods(customerKey: string): Promise<BillingMethod[]> {
  const response = await request<{ items: BillingMethod[] }>(`/api/billing-methods/${customerKey}`);
  console.log("[Toss Billing] billing methods response", response);
  return response.items;
}

export function confirmBilling(customerKey: string, authKey: string) {
  return request<{ billing_key: string; method: BillingMethod }>("/api/billing/confirm", {
    method: "POST",
    body: JSON.stringify({
      customer_key: customerKey,
      auth_key: authKey,
    }),
  }).then((response) => {
    console.log("[Toss Billing] confirm billing response", response);
    return response;
  });
}

export function chargePayment(payload: {
  customer_key: string;
  billing_key: string;
  amount: number;
  order_name: string;
  plan_name: string;
  billing_cycle: string;
  applied_start_date: string;
  customer_email?: string;
  customer_name?: string;
}) {
  return request<ChargeResult>("/api/payments/charge", {
    method: "POST",
    body: JSON.stringify(payload),
  }).then((response) => {
    console.log("[Toss Billing] charge payment response", response);
    return response;
  });
}
