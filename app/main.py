from fastapi import FastAPI, Depends, Header
from sqlalchemy.orm import Session
from decimal import Decimal
from pydantic import BaseModel
import json

from .database import engine, Base, get_db, redis_client
from . import crud

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Distributed Banking Engine")

class CreateAccountSchema(BaseModel):
    owner_name: str
    initial_deposit: Decimal

class TransferSchema(BaseModel):
    sender_id: str
    receiver_id: str
    amount: Decimal

@app.post("/accounts")
def create_account_endpoint(payload: CreateAccountSchema, db: Session = Depends(get_db)):
    account = crud.create_account(db, payload.owner_name, payload.initial_deposit)
    return {"id": str(account.id), "owner": account.owner_name, "balance": float(account.balance)}

@app.post("/transfers")
def transfer_endpoint(
    payload: TransferSchema, 
    x_idempotency_key: str = Header(..., alias="X-Idempotency-Key"),
    db: Session = Depends(get_db)
):
    cache_key = f"idempotency:{x_idempotency_key}"
    cached_response = redis_client.get(cache_key)
    
    if cached_response:
        return json.loads(cached_response)

    result = crud.transfer_funds(db, payload.sender_id, payload.receiver_id, payload.amount)
    redis_client.setex(cache_key, 86400, json.dumps(result))

    return result