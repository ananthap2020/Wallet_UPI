from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from database import engine, SessionLocal, Base
from models import User, Transaction

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Wallet API", description="User Wallet Management APIs", version="1.0")


# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==============================
# Schemas
# ==============================
class UserSchema(BaseModel):
    id: int
    name: str
    email: str
    phone: str
    wallet_balance: float

    class Config:
        orm_mode = True


class WalletUpdateSchema(BaseModel):
    amount: float
    
class UserCreateSchema(BaseModel):
    name: str
    email: str
    phone: str

@app.post("/users", response_model=UserSchema)
def create_user(payload: UserCreateSchema, db: Session = Depends(get_db)):
    """Create a new user"""
    user = User(
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        wallet_balance=0.0
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

class TransactionSchema(BaseModel):
    id: int
    user_id: int
    amount: float
    type: str  # "credit" or "debit"

    class Config:
        orm_mode = True


# ==============================
# APIs
# ==============================

@app.get("/users", response_model=List[UserSchema])
def list_users(db: Session = Depends(get_db)):
    """Fetch all users with wallet balance"""
    return db.query(User).all()


@app.post("/users/{user_id}/wallet")
def update_wallet(user_id: int, payload: WalletUpdateSchema, db: Session = Depends(get_db)):
    """Add or update wallet balance for a user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.wallet_balance += payload.amount

    # Record transaction
    txn_type = "credit" if payload.amount > 0 else "debit"
    txn = Transaction(user_id=user_id, amount=payload.amount, type=txn_type)
    db.add(txn)
    db.commit()
    db.refresh(user)

    return {"message": "Wallet updated successfully", "balance": user.wallet_balance}


@app.get("/users/{user_id}/transactions", response_model=List[TransactionSchema])
def fetch_transactions(user_id: int, db: Session = Depends(get_db)):
    """Fetch all wallet transactions for a specific user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return db.query(Transaction).filter(Transaction.user_id == user_id).all()