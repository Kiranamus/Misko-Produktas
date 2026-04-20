from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session
import stripe
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from jose import JWTError, jwt

from .api.routes import router
from .database import init_db, get_db, User, PurchasedPlan
from .auth import verify_password, get_password_hash, create_access_token, create_random_token

load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key-change-this")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

app = FastAPI()

# CORS
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

security = HTTPBearer()

def get_current_user(token: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = db.query(User).filter(User.username == username).first()
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

class PaymentIntentRequest(BaseModel):
    amount: int
    currency: str = "eur"

class PurchaseRequest(BaseModel):
    plan_id: str
    transaction_id: str

@app.post("/api/create-payment-intent")
async def create_payment_intent(payment: PaymentIntentRequest):
    try:
        intent = stripe.PaymentIntent.create(
            amount=payment.amount,
            currency=payment.currency,
            payment_method_types=["card"],
        )
        return {
            "clientSecret": intent.client_secret,
            "paymentIntentId": intent.id
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/payment-status/{payment_intent_id}")
async def get_payment_status(payment_intent_id: str):
    try:
        intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        return {
            "status": intent.status,
            "amount": intent.amount,
            "currency": intent.currency
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/record-purchase")
async def record_purchase(
    purchase: PurchaseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Record a successful purchase - deactivates old plans"""
    
    existing_plans = db.query(PurchasedPlan).filter(
        PurchasedPlan.user_id == current_user.id,
        PurchasedPlan.is_active == True
    ).all()
    
    for plan in existing_plans:
        plan.is_active = False
    
    existing = db.query(PurchasedPlan).filter(
        PurchasedPlan.user_id == current_user.id,
        PurchasedPlan.plan_id == purchase.plan_id
    ).first()
    
    if existing:
        existing.is_active = True
        existing.transaction_id = purchase.transaction_id
        existing.purchased_at = datetime.utcnow()
        
        if purchase.plan_id == "lithuania_month":
            existing.expires_at = datetime.utcnow() + timedelta(days=30)
        else:
            existing.expires_at = None
        
        db.commit()
        return {"message": "Plan reactivated successfully", "success": True}
    
    expires_at = None
    if purchase.plan_id == "lithuania_month":
        expires_at = datetime.utcnow() + timedelta(days=30)
    
    purchased_plan = PurchasedPlan(
        user_id=current_user.id,
        plan_id=purchase.plan_id,
        transaction_id=purchase.transaction_id,
        expires_at=expires_at,
        is_active=True
    )
    
    db.add(purchased_plan)
    db.commit()
    
    return {"message": "Purchase recorded successfully", "success": True}

@app.get("/api/user-plans")
async def get_user_plans(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    purchases = db.query(PurchasedPlan).filter(
        PurchasedPlan.user_id == current_user.id,
        PurchasedPlan.is_active == True
    ).all()
    
    active_plans = []
    for purchase in purchases:
        if purchase.expires_at and purchase.expires_at < datetime.utcnow():
            purchase.is_active = False
            db.commit()
            continue
        active_plans.append(purchase.plan_id)
    
    return {"purchased_plans": active_plans}

@app.get("/api/has-active-plan")
async def has_active_plan(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    purchases = db.query(PurchasedPlan).filter(
        PurchasedPlan.user_id == current_user.id,
        PurchasedPlan.is_active == True
    ).all()
    
    has_active = False
    for purchase in purchases:
        if purchase.expires_at and purchase.expires_at < datetime.utcnow():
            purchase.is_active = False
            db.commit()
            continue
        has_active = True
    
    return {"has_active_plan": has_active}

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)