import uuid
from decimal import Decimal
from sqlalchemy.orm import Session
from fastapi import HTTPException
from .models import Account, LedgerEntry, EntryType

def create_account(db: Session, owner_name: str, initial_deposit: Decimal):
    account = Account(owner_name=owner_name, balance=initial_deposit)
    db.add(account)
    db.commit()
    db.refresh(account)
    
    if initial_deposit > 0:
        entry = LedgerEntry(
            account_id=account.id,
            amount=initial_deposit,
            entry_type=EntryType.CREDIT,
            reference_id=uuid.uuid4()
        )
        db.add(entry)
        db.commit()
        
    return account

def transfer_funds(db: Session, sender_id: str, receiver_id: str, amount: Decimal):
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    first_id, second_id = sorted([uuid.UUID(sender_id), uuid.UUID(receiver_id)])

    accounts = (
        db.query(Account)
        .filter(Account.id.in_([first_id, second_id]))
        .with_for_update()
        .all()
    )
    
    account_map = {acc.id: acc for acc in accounts}
    sender = account_map.get(uuid.UUID(sender_id))
    receiver = account_map.get(uuid.UUID(receiver_id))

    if not sender or not receiver:
        raise HTTPException(status_code=404, detail="One or both accounts not found")

    if sender.balance < amount:
        raise HTTPException(status_code=400, detail="Insufficient funds")

    sender.balance -= amount
    receiver.balance += amount

    transfer_ref = uuid.uuid4()
    debit_entry = LedgerEntry(
        account_id=sender.id, amount=amount, entry_type=EntryType.DEBIT, reference_id=transfer_ref
    )
    credit_entry = LedgerEntry(
        account_id=receiver.id, amount=amount, entry_type=EntryType.CREDIT, reference_id=transfer_ref
    )

    db.add_all([debit_entry, credit_entry])
    db.commit()

    return {"status": "SUCCESS", "transfer_reference": str(transfer_ref)}