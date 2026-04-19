from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import stripe
import os
from dotenv import load_dotenv

from .api.routes import router
from .database import init_db

# Load environment variables
load_dotenv()

# Configure Stripe with your test secret key
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    init_db()

# ========== PAYMENT MODELS ==========
class PaymentIntentRequest(BaseModel):
    amount: int  # in cents (e.g., 4999 = €49.99)
    currency: str = "eur"
    payment_method_type: str = "card"

class PaymentIntentResponse(BaseModel):
    clientSecret: str
    paymentIntentId: str

class PaymentStatusResponse(BaseModel):
    status: str
    amount: int
    currency: str

# ========== PAYMENT ENDPOINTS ==========
@app.post("/api/create-payment-intent", response_model=PaymentIntentResponse)
async def create_payment_intent(payment: PaymentIntentRequest):
    """
    Create a Stripe Payment Intent for checkout
    """
    try:
        intent = stripe.PaymentIntent.create(
            amount=payment.amount,
            currency=payment.currency,
            payment_method_types=["card"],
        )
        return PaymentIntentResponse(
            clientSecret=intent.client_secret,
            paymentIntentId=intent.id
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/payment-status/{payment_intent_id}", response_model=PaymentStatusResponse)
async def get_payment_status(payment_intent_id: str):
    """
    Get payment status by payment intent ID
    """
    try:
        intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        return PaymentStatusResponse(
            status=intent.status,
            amount=intent.amount,
            currency=intent.currency
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ========== SIMPLE MOCK PAYMENT (optional, for testing without Stripe) ==========
class MockPaymentRequest(BaseModel):
    amount: float
    currency: str = "EUR"

@app.post("/api/mock-payment")
async def mock_payment(payment: MockPaymentRequest):
    """
    Simple mock payment for testing without Stripe
    """
    import uuid
    from datetime import datetime
    
    import random
    is_successful = random.random() < 0.95
    
    if not is_successful:
        return {
            "success": False,
            "transaction_id": None,
            "message": "Payment failed - insufficient funds",
            "amount": payment.amount,
            "currency": payment.currency
        }
    
    return {
        "success": True,
        "transaction_id": f"mock_txn_{uuid.uuid4().hex[:12]}",
        "message": "Payment successful (mock)",
        "amount": payment.amount,
        "currency": payment.currency,
        "timestamp": datetime.utcnow().isoformat()
    }

# Include your existing routes
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)