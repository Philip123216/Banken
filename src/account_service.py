# src/account_service.py
from datetime import datetime
from decimal import Decimal
import os
from dateutil.relativedelta import relativedelta # Externes Paket, bleibt so
from . import config # RELATIV
from .utils import generate_id, save_json, load_json, parse_datetime # RELATIV
from .customer_service import get_customer # RELATIV
from .ledger_service import update_bank_ledger # RELATIV


def create_account(customer_id):
    """Creates a regular account and an associated (inactive) credit account for a customer."""
    # Import here to avoid circular imports
    from .time_processing_service import get_system_date

    customer_data = get_customer(customer_id)
    if not customer_data:
        print(f"Error: Cannot create account, customer {customer_id} not found.")
        return None, None

    if get_customer_account(customer_id):
        print(f"Error: Customer {customer_id} already has an account.")
        return None, None

    # Create Regular Account
    account_id = generate_id("CH")  # Using CH prefix for IBAN-like ID
    now_iso = datetime.now().isoformat()
    system_date_iso = get_system_date().isoformat()  # Use system date for fee tracking

    account_data = {
        "account_id": account_id,
        "customer_id": customer_id,
        "balance": Decimal("0.00"),
        "status": "active",  # 'active', 'blocked', 'closed'
        "created_at": now_iso,
        "last_fee_date": system_date_iso,  # Initialize fee date
        "transactions": []
    }
    account_file_path = os.path.join(config.ACCOUNTS_DIR, f"{account_id}.json")
    save_json(account_file_path, account_data)
    print(f"Regular account created: {account_id}")

    # Create Associated Credit Account (initialized but inactive)
    credit_account_id = f"CR{account_id}"
    credit_account_data = {
        "account_id": credit_account_id,
        "customer_id": customer_id,
        "balance": Decimal("0.00"),  # Outstanding loan amount
        "status": "inactive",  # 'inactive', 'active', 'paid_off', 'blocked', 'written_off'
        "created_at": now_iso,
        "credit_start_date": None,
        "credit_end_date": None,
        "original_amount": Decimal("0.00"),
        "monthly_payment": Decimal("0.00"),
        "monthly_rate": config.CREDIT_MONTHLY_RATE,
        "remaining_payments": 0,
        "amortization_schedule": [],
        "transactions": [],
        "missed_payments_count": 0,  # Track consecutive missed payments
        "last_payment_attempt_date": None,
        "penalty_accrued": Decimal("0.00")  # Track accrued penalties while blocked
    }
    credit_account_file_path = os.path.join(config.ACCOUNTS_DIR, f"{credit_account_id}.json")
    save_json(credit_account_file_path, credit_account_data)
    print(f"Associated credit account created: {credit_account_id}")

    return account_data, credit_account_data

def get_account(account_id):
    """Retrieves account information (regular or credit)."""
    file_path = os.path.join(config.ACCOUNTS_DIR, f"{account_id}.json")
    account_data = load_json(file_path)
    # Ensure balance is Decimal
    if account_data and 'balance' in account_data:
        if isinstance(account_data['balance'], str):
            account_data['balance'] = Decimal(account_data['balance'])
    return account_data

def get_customer_account(customer_id):
    """Finds the regular account for a customer."""
    all_files = os.listdir(config.ACCOUNTS_DIR)
    account_files = [f for f in all_files if f.endswith('.json') and not f.startswith('CR')]

    for acc_file in account_files:
        acc_data = load_json(os.path.join(config.ACCOUNTS_DIR, acc_file))
        if acc_data and acc_data.get('customer_id') == customer_id:
            return acc_data
    return None

def save_account(account_data):
    """Saves account data back to its file."""
    if not account_data or 'account_id' not in account_data:
        print("Error: Invalid account data for saving.")
        return False

    file_path = os.path.join(config.ACCOUNTS_DIR, f"{account_data['account_id']}.json")
    save_json(file_path, account_data)
    return True

def add_transaction_to_account(account_data_param, transaction_data):
    """Adds a transaction record to an account's history using the provided account_data object."""
    if not account_data_param:
        print(f"Error: Invalid account_data provided to add_transaction_to_account.")
        return False

    if 'transactions' not in account_data_param:
        account_data_param['transactions'] = []

    account_data_param['transactions'].append(transaction_data)
    return save_account(account_data_param)

def process_quarterly_fees(current_date):
    """Processes quarterly account fees for all active accounts."""
    print(f"\n--- Processing Quarterly Fees for {current_date.isoformat()} ---")

    all_files = os.listdir(config.ACCOUNTS_DIR)
    account_files = [f for f in all_files if f.endswith('.json') and not f.startswith('CR')]

    fees_charged = 0
    fees_failed = 0

    for acc_file in account_files:
        account_data = load_json(os.path.join(config.ACCOUNTS_DIR, acc_file))

        # Skip inactive accounts
        if not account_data or account_data.get('status') != 'active':
            continue

        account_id = account_data['account_id']
        last_fee_date_str = account_data.get('last_fee_date')

        if not last_fee_date_str:
            print(f"Warning: Account {account_id} missing last_fee_date. Setting to current date.")
            account_data['last_fee_date'] = current_date.isoformat()
            save_account(account_data)
            continue

        last_fee_date = parse_datetime(last_fee_date_str)

        # Check if at least 3 months have passed since last fee
        months_diff = (current_date.year - last_fee_date.year) * 12 + (current_date.month - last_fee_date.month)

        if months_diff >= 3:
            # Charge quarterly fee
            balance_before = account_data['balance']

            # Create fee transaction record
            fee_tx = {
                "transaction_id": generate_id("FEE"),
                "type": "quarterly_fee",
                "amount": config.QUARTERLY_FEE,
                "timestamp": current_date.isoformat(),
                "status": "pending",
                "balance_before": balance_before,
                "balance_after": balance_before  # Will update if successful
            }

            if balance_before >= config.QUARTERLY_FEE:
                # Sufficient funds - charge fee
                account_data['balance'] -= config.QUARTERLY_FEE
                fee_tx["status"] = "completed"
                fee_tx["balance_after"] = account_data['balance']

                # Update last fee date to current date
                account_data['last_fee_date'] = current_date.isoformat()

                # Update ledger
                update_bank_ledger([
                    ('customer_liabilities', -config.QUARTERLY_FEE),
                    ('income', +config.QUARTERLY_FEE)
                ])

                print(f"Quarterly fee charged: {config.QUARTERLY_FEE} from {account_id}. New balance: {account_data['balance']}")
                fees_charged += 1
            else:
                # Insufficient funds - record failed attempt but don't change balance
                fee_tx["status"] = "rejected"
                fee_tx["reason"] = "Insufficient funds"
                print(f"Quarterly fee failed: {account_id} has insufficient funds ({balance_before})")
                fees_failed += 1

            # Save transaction and account state
            add_transaction_to_account(account_data, fee_tx)  # This saves the account

    print(f"--- Quarterly Fee Processing Complete. Charged: {fees_charged}, Failed: {fees_failed} ---")
