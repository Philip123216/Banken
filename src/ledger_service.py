# Ledger management functions for the banking system
from decimal import Decimal
import os
import config
from utils import load_json, save_json

def load_bank_ledger():
    """Loads the bank's ledger. Initializes if it doesn't exist."""
    ledger = load_json(config.LEDGER_FILE)
    if ledger is None:
        print("Initializing new bank ledger.")
        ledger = {
            "customer_liabilities": {"balance": Decimal("0.00")},
            "central_bank_assets": {"balance": Decimal("0.00")},
            "credit_assets": {"balance": Decimal("0.00")},
            "income": {"balance": Decimal("0.00")}
        }
        save_json(config.LEDGER_FILE, ledger)
    # Ensure balances are Decimal
    for key in ledger:
        if isinstance(ledger[key].get('balance'), str):
            ledger[key]['balance'] = Decimal(ledger[key]['balance'])
        elif not isinstance(ledger[key].get('balance'), Decimal):
            ledger[key]['balance'] = Decimal('0.00')  # Default if missing or wrong type

    return ledger

def update_bank_ledger(updates):
    """
    Updates the bank ledger based on double-entry principles.
    'updates' is a list of tuples: [('account_name', amount_change), ...]
    Example: [('customer_liabilities', +100), ('central_bank_assets', +100)]
    """
    ledger = load_bank_ledger()
    total_change = Decimal('0.00')
    for account, amount in updates:
        if account not in ledger:
            print(f"Warning: Ledger account '{account}' not found.")
            continue
        if not isinstance(amount, Decimal):
            print(f"Warning: Amount '{amount}' for ledger update is not Decimal. Skipping.")
            continue

        ledger[account]["balance"] += amount
        total_change += amount

    save_json(config.LEDGER_FILE, ledger)
    return ledger

def get_bank_ledger():
    """Returns the current state of the bank ledger."""
    return load_bank_ledger()

def validate_bank_system():
    """Performs basic validation checks on the system's financial state."""
    print("\n--- Starting System Validation ---")
    ledger = load_bank_ledger()
    total_customer_balance = Decimal("0.00")
    total_credit_outstanding = Decimal("0.00")
    active_accounts = 0
    active_credits = 0

    # Sum balances from all customer accounts
    all_files = os.listdir(config.ACCOUNTS_DIR)
    account_files = [f for f in all_files if f.endswith('.json') and not f.startswith('CR')]
    credit_files = [f for f in all_files if f.endswith('.json') and f.startswith('CR')]

    for acc_file in account_files:
        acc_data = load_json(os.path.join(config.ACCOUNTS_DIR, acc_file))
        if acc_data and acc_data.get('status') in ['active', 'blocked']:
            balance = acc_data.get('balance', '0')
            total_customer_balance += Decimal(balance) if isinstance(balance, str) else balance
            if acc_data.get('status') == 'active':
                active_accounts += 1

    for cred_file in credit_files:
        cred_data = load_json(os.path.join(config.ACCOUNTS_DIR, cred_file))
        if cred_data and cred_data.get('status') in ['active', 'blocked'] and Decimal(
                cred_data.get('balance', '0')) > 0:
            balance = cred_data.get('balance', '0')
            total_credit_outstanding += Decimal(balance) if isinstance(balance, str) else balance
            active_credits += 1

    # Basic Accounting Equation Check
    assets = ledger['central_bank_assets']['balance'] + ledger['credit_assets']['balance']
    liabilities_plus_income = ledger['customer_liabilities']['balance'] + ledger['income']['balance']
    diff = assets - liabilities_plus_income

    print(f"Total Customer Liabilities (Ledger): {ledger['customer_liabilities']['balance']:.2f}")
    print(f"Sum of Customer Account Balances:    {total_customer_balance:.2f}")
    customer_bal_diff = ledger['customer_liabilities']['balance'] - total_customer_balance
    print(f"  Difference: {customer_bal_diff:.2f} {'(OK)' if abs(customer_bal_diff) < config.CHF_QUANTIZE else '(MISMATCH!)'}")

    print(f"Total Credit Assets (Ledger):      {ledger['credit_assets']['balance']:.2f}")
    print(f"Sum of Credit Account Balances:    {total_credit_outstanding:.2f}")
    credit_bal_diff = ledger['credit_assets']['balance'] - total_credit_outstanding
    print(f"  Difference: {credit_bal_diff:.2f} {'(OK)' if abs(credit_bal_diff) < config.CHF_QUANTIZE else '(MISMATCH!)'}")

    print(f"Assets (Central Bank + Credit): {assets:.2f}")
    print(f"Liabilities + Income:           {liabilities_plus_income:.2f}")
    print(
        f"  Difference (Assets - (Liab+Inc)): {diff:.2f} {'(BALANCED)' if abs(diff) < config.CHF_QUANTIZE else '(OUT OF BALANCE!)'}")

    print(f"Total Active/Blocked Accounts: {active_accounts}")
    print(f"Total Active/Blocked Credits: {active_credits}")
    print("--- Validation Complete ---")
    return abs(customer_bal_diff) < config.CHF_QUANTIZE and abs(credit_bal_diff) < config.CHF_QUANTIZE and abs(diff) < config.CHF_QUANTIZE