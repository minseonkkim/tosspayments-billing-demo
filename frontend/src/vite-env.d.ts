/// <reference types="vite/client" />

interface TossPaymentWindow {
  requestBillingAuth(request: {
    method: "CARD";
    successUrl: string;
    failUrl: string;
    customerName?: string;
    customerEmail?: string;
    windowTarget?: "self" | "iframe";
  }): Promise<void> | void;
}

interface TossPaymentsFactory {
  payment(params: { customerKey: string }): TossPaymentWindow;
}

declare global {
  interface Window {
    TossPayments: (clientKey: string) => TossPaymentsFactory;
  }
}

export {};
