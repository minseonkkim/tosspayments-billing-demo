# Toss Payments Billing Demo

FastAPI 백엔드와 React 프론트엔드로 구성한 토스페이먼츠 Billing 예제입니다. 결제 화면에서 결제 금액을 확인하고, 저장된 카드 중 하나를 선택하거나 새 카드를 등록한 뒤 `결제하기` 버튼으로 자동결제를 승인합니다.

## 구성

- `backend`: 토스 Billing 키 발급, 저장 카드 조회, 빌링키 자동결제 승인 API
- `frontend`: 결제 금액, 카드 선택, 카드 추가, 결제 결과 UI

## 1. 환경 변수 설정

### backend

`backend/.env.example`를 `backend/.env`로 복사하고 값을 채우세요.

```env
TOSS_SECRET_KEY=test_sk_your_secret_key
TOSS_CLIENT_KEY=test_ck_your_client_key
TOSS_API_BASE_URL=https://api.tosspayments.com
FRONTEND_SUCCESS_URL=http://localhost:5173/billing/success
FRONTEND_FAIL_URL=http://localhost:5173/billing/fail
BACKEND_CORS_ORIGINS=http://localhost:5173
STORE_PATH=./data/billing_store.json
PAYMENT_STORE_PATH=./data/payment_store.json
TOSS_TEST_CODE=
```

### frontend

`frontend/.env.example`를 `frontend/.env`로 복사하세요.

```env
VITE_API_BASE_URL=http://localhost:8000
```

## 2. 실행

### backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### frontend

```bash
cd frontend
npm install
npm run dev
```

브라우저에서 `http://localhost:5173`에 접속하면 됩니다.

## 동작 흐름

1. 프론트엔드가 저장된 카드 목록을 조회합니다.
2. `카드 추가` 버튼으로 토스 Billing 등록창을 엽니다.
3. 성공 리다이렉트에서 `authKey`, `customerKey`를 받아 백엔드가 빌링키를 발급하고 저장합니다.
4. 저장된 카드 중 하나를 선택하고 `결제하기`를 누르면 백엔드가 빌링키 자동결제 승인 API를 호출합니다.

## 주의사항

- 토스 Billing은 계약 및 리스크 심사 후 사용할 수 있습니다.
- 현재 저장소 예제는 인증/회원 시스템 없이 데모용 고객 키를 사용합니다. 실제 서비스에서는 로그인 사용자 기준의 난수형 `customerKey`를 서버에서 생성하고 보관해야 합니다.
- 저장된 결제수단은 `backend/data/billing_store.json`, 결제 완료 화면용 요약 정보는 `backend/data/payment_store.json`에 파일 형태로 보관됩니다. 운영 환경에서는 DB로 교체하세요.

## 결제 실패 테스트

자동결제 실패를 재현하려면 `backend/.env`에 아래 값을 넣고 백엔드를 재시작하세요.

```env
TOSS_TEST_CODE=REJECT_CARD_PAYMENT
```

성공 흐름으로 되돌리려면 값을 비우거나 항목을 제거하면 됩니다.
