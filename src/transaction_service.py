# Transaction processing functions for the banking system
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
import os
import config
from utils import load_json, generate_id, parse_datetime
from account_service import get_account, add_transaction_to_account, save_account
from customer_service import create_customer
from account_service import create_account
from credit_service import request_credit
from ledger_service import update_bank_ledger
from time_processing_service import process_time_event

def process_transfer_out(transaction_data):
    """Processes an outgoing transfer from a customer account."""
    account_id = transaction_data.get('from_account')
    amount_str = transaction_data.get('amount', '0')
    amount = Decimal(amount_str).quantize(config.CHF_QUANTIZE, ROUND_HALF_UP)
    timestamp = transaction_data.get('timestamp', datetime.now().isoformat())
    transaction_id = generate_id("TR")

    account_data = get_account(account_id)

    # --- Create base transaction record (for history) ---
    tx_record = {
        "transaction_id": transaction_id,
        "type": "transfer_out",
        "from_account": account_id,
        "to_iban": transaction_data.get('to_iban'),
        "amount": amount,
        "timestamp": timestamp,
        "status": "rejected",  # Default to rejected
        "balance_before": None,
        "balance_after": None,
        "reason": ""
    }

    if not account_data:
        print(f"Transaction Rejected: Account {account_id} not found.")
        tx_record["reason"] = "Account not found"
        # Cannot save to account if not found, maybe log elsewhere?
        # For now, we just return the rejected record
        return tx_record  # Return immediately

    if account_data['status'] != 'active':
        print(f"Transaction Rejected: Account {account_id} is not active (status: {account_data['status']}).")
        tx_record["reason"] = f"Account not active ({account_data['status']})"
        tx_record["balance_before"] = account_data['balance']
        tx_record["balance_after"] = account_data['balance']  # Balance doesn't change
        add_transaction_to_account(account_id, tx_record)
        return tx_record

    balance_before = account_data['balance']
    tx_record["balance_before"] = balance_before

    if balance_before < amount:
        print(f"Transaction Rejected: Insufficient funds in account {account_id}.")
        tx_record["reason"] = "Insufficient funds"
        tx_record["balance_after"] = balance_before  # Balance doesn't change
        add_transaction_to_account(account_id, tx_record)
        return tx_record
    else:
        # Process successful transfer
        account_data['balance'] -= amount
        tx_record["status"] = "completed"
        tx_record["balance_after"] = account_data['balance']
        print(f"Transfer Out: {amount} from {account_id}. New balance: {account_data['balance']:.2f}")

        # Update Ledger
        update_bank_ledger([
            ('customer_liabilities', -amount),
            ('central_bank_assets', -amount)
        ])

        # Save transaction and account state
        add_transaction_to_account(account_id, tx_record)  # Saves the account implicitly

        return tx_record

def process_incoming_payment(transaction_data):
    """Processes an incoming payment to a customer account."""
    account_id = transaction_data.get('to_account')
    amount_str = transaction_data.get('amount', '0')
    amount = Decimal(amount_str).quantize(config.CHF_QUANTIZE, ROUND_HALF_UP)
    timestamp = transaction_data.get('timestamp', datetime.now().isoformat())
    transaction_id = generate_id("TR")  # Can reuse prefix, ID ensures uniqueness

    account_data = get_account(account_id)

    # --- Create base transaction record (for history) ---
    tx_record = {
        "transaction_id": transaction_id,
        "type": "transfer_in",
        "to_account": account_id,
        "from_iban": transaction_data.get('from_iban'),
        "amount": amount,
        "timestamp": timestamp,
        "status": "rejected",  # Default to rejected
        "balance_before": None,
        "balance_after": None,
        "reason": ""
    }

    if not account_data:
        print(f"Transaction Rejected: Account {account_id} not found for incoming payment.")
        tx_record["reason"] = "Account not found"
        # Cannot save transaction to non-existent account
        return tx_record

    # Allow deposits to active or blocked accounts (to potentially unblock)
    if account_data['status'] == 'closed':
        print(f"Transaction Rejected: Account {account_id} is closed.")
        tx_record["reason"] = "Account closed"
        tx_record["balance_before"] = account_data['balance']
        tx_record["balance_after"] = account_data['balance']  # Balance doesn't change
        add_transaction_to_account(account_id, tx_record)
        return tx_record

    balance_before = account_data['balance']
    tx_record["balance_before"] = balance_before

    account_data['balance'] += amount
    tx_record["status"] = "completed"
    tx_record["balance_after"] = account_data['balance']

    print(f"Transfer In: {amount} to {account_id}. New balance: {account_data['balance']:.2f}")

    # Check if deposit unblocks the account
    if account_data['status'] == 'blocked':
        # Simple unblock: if balance is now non-negative.
        # Complex unblock (paying arrears) is not implemented here.
        if account_data['balance'] >= 0:
            account_data['status'] = 'active'
            print(f"Account {account_id} status changed to 'active' due to deposit.")
            # Reset penalty accrual if unblocked? Or keep it until paid? Keep it for now.
            # Reset missed payments count? Resetting seems reasonable upon unblocking.
            credit_account_id = f"CR{account_id}"
            credit_account_data = get_account(credit_account_id)
            if credit_account_data:
                credit_account_data['missed_payments_count'] = 0
                # We might need to clear accrued penalties IF the deposit covers them + arrears
                # Simple approach: Penalties accrued remain on the credit account balance.
                save_account(credit_account_data)

    # Update Ledger
    update_bank_ledger([
        ('customer_liabilities', +amount),
        ('central_bank_assets', +amount)
    ])

    # Save transaction and account state
    add_transaction_to_account(account_id, tx_record)  # Saves the account implicitly

    return tx_record

def process_transaction_file(file_path):
    """Loads transactions from a JSON file and processes them sequentially."""
    print(f"\n--- Processing Transaction File: {file_path} ---")
    transactions = load_json(file_path)

    if transactions is None:
        print(f"Error: Could not load or decode transaction file {file_path}")
        return
    if not isinstance(transactions, list):
        print(f"Error: Transaction file {file_path} does not contain a list of transactions.")
        return

    # Assume transactions in the file are already ordered by timestamp correctly.
    for i, tx_data in enumerate(transactions):
        tx_type = tx_data.get('type')
        print(f"\nProcessing Transaction {i + 1}/{len(transactions)}: Type = {tx_type}")

        try:
            if tx_type == "time_event":
                process_time_event(tx_data)
            elif tx_type == "create_customer":
                create_customer(tx_data.get('name'), tx_data.get('address'), tx_data.get('birth_date'))
            elif tx_type == "create_account":
                create_account(tx_data.get('customer_id'))
            elif tx_type == "transfer_out":
                process_transfer_out(tx_data)
            elif tx_type == "transfer_in":
                process_incoming_payment(tx_data)
            elif tx_type == "credit_request":
                request_credit(tx_data)
            else:
                print(f"Warning: Unknown transaction type '{tx_type}'. Skipping.")

        except Exception as e:
            print(f"!!! Critical Error processing transaction {i + 1} ({tx_type}): {e} !!!")
            import traceback
            traceback.print_exc()

    print(f"--- Finished Processing Transaction File: {file_path} ---")
