# src/credit_service.py
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from dateutil.relativedelta import relativedelta # Externes Paket
import os
import json
from . import config
from .utils import generate_id, save_json, load_json, parse_datetime
from .ledger_service import update_bank_ledger
from .time_processing_service import get_system_date

def calculate_amortization(principal, annual_rate, term_months):
    """Calculates amortization schedule for a loan."""
    monthly_rate = annual_rate / 12

    # Calculate monthly payment using the formula: P = (r*PV) / (1 - (1+r)^-n)
    # Where P = payment, r = monthly rate, PV = present value (principal), n = number of payments
    if monthly_rate == 0:
        # Special case: no interest
        monthly_payment = principal / term_months
    else:
        monthly_payment = (monthly_rate * principal) / (1 - (1 + monthly_rate) ** -term_months)

    # Round to 2 decimal places
    monthly_payment = monthly_payment.quantize(config.CHF_QUANTIZE, ROUND_HALF_UP)

    # Generate amortization schedule
    schedule = []
    remaining_principal = principal

    for month in range(1, term_months + 1):
        if remaining_principal <= 0:
            break

        # Calculate interest for this period
        interest_payment = (remaining_principal * monthly_rate).quantize(config.CHF_QUANTIZE, ROUND_HALF_UP)

        # Calculate principal for this period (payment - interest)
        principal_payment = (monthly_payment - interest_payment).quantize(config.CHF_QUANTIZE, ROUND_HALF_UP)

        # Adjust for final payment to avoid rounding issues
        if month == term_months or principal_payment > remaining_principal:
            principal_payment = remaining_principal
            monthly_payment = principal_payment + interest_payment

        # Update remaining principal
        remaining_principal = (remaining_principal - principal_payment).quantize(config.CHF_QUANTIZE, ROUND_HALF_UP)

        # Add to schedule
        schedule.append({
            "month": month,
            "payment": monthly_payment,
            "principal": principal_payment,
            "interest": interest_payment,
            "remaining": remaining_principal
        })

    return monthly_payment, schedule

def request_credit(transaction_data):
    """Processes a credit request, disburses funds, and charges the fee."""
    # Import here to avoid circular imports
    from .account_service import get_account, add_transaction_to_account, save_account
    
    main_account_id = transaction_data.get('main_account')
    credit_account_id = f"CR{main_account_id}"
    amount_str = transaction_data.get('amount', '0')
    requested_amount = Decimal(amount_str).quantize(config.CHF_QUANTIZE, ROUND_HALF_UP)
    timestamp = transaction_data.get('timestamp', datetime.now().isoformat())
    system_date = parse_datetime(timestamp) or get_system_date()

    main_account = get_account(main_account_id)
    credit_account = get_account(credit_account_id)

    # --- Validations ---
    if not main_account or not credit_account:
        print(f"Credit Request Failed: Account(s) not found for {main_account_id}.")
        return None  # Or return a rejected transaction status

    if main_account['status'] != 'active':
        print(f"Credit Request Failed: Main account {main_account_id} is not active.")
        return None

    if credit_account['status'] not in ['inactive', 'paid_off']:
        print(f"Credit Request Failed: Credit account {credit_account_id} is already active or blocked.")
        return None

    if not (config.MIN_CREDIT <= requested_amount <= config.MAX_CREDIT):
        print(f"Credit Request Failed: Amount {requested_amount} is outside limits ({config.MIN_CREDIT}-{config.MAX_CREDIT}).")
        return None

    # --- Process Disbursement ---
    disbursement_tx_id = generate_id("CRD")  # Credit Disbursement
    balance_before_disburse = main_account['balance']
    main_account['balance'] += requested_amount
    balance_after_disburse = main_account['balance']

    # Create disbursement transaction record (add later)
    disburse_tx = {
        "transaction_id": disbursement_tx_id,
        "type": "credit_disbursement",
        "credit_account": credit_account_id,
        "main_account": main_account_id,
        "amount": requested_amount,
        "timestamp": timestamp,
        "status": "completed",
        "main_balance_before": balance_before_disburse,
        "main_balance_after": balance_after_disburse
    }

    # --- Update Credit Account ---
    credit_balance_before = credit_account['balance']
    credit_account['balance'] = requested_amount  # Loan principal owed
    credit_account['original_amount'] = requested_amount
    credit_account['status'] = 'active'
    credit_account['credit_start_date'] = system_date.isoformat()
    credit_account['credit_end_date'] = (system_date + relativedelta(months=config.CREDIT_TERM_MONTHS)).isoformat()
    credit_account['remaining_payments'] = config.CREDIT_TERM_MONTHS
    credit_account['missed_payments_count'] = 0
    credit_account['penalty_accrued'] = Decimal('0.00')  # Reset penalty on new loan

    # Calculate Amortization
    monthly_payment, schedule = calculate_amortization(requested_amount, config.CREDIT_INTEREST_RATE_PA, config.CREDIT_TERM_MONTHS)
    credit_account['monthly_payment'] = monthly_payment
    credit_account['amortization_schedule'] = schedule  # Store the schedule

    print(f"Credit Approved: {requested_amount} for {main_account_id}. Monthly Payment: {monthly_payment}")

    # --- Ledger Update for Disbursement ---
    update_bank_ledger([
        ('credit_assets', +requested_amount),  # Bank's asset increases
        ('customer_liabilities', +requested_amount)  # Bank owes customer more (in their account)
    ])

    # --- Process Credit Fee ---
    fee_tx_id = generate_id("FEE")
    balance_before_fee = main_account['balance']  # Use balance *after* disbursement

    # Create fee transaction record (add later)
    fee_tx = {
        "transaction_id": fee_tx_id,
        "type": "credit_fee",
        "from_account": main_account_id,
        "credit_account": credit_account_id,  # Link fee to the credit event
        "amount": config.CREDIT_FEE,
        "timestamp": timestamp,  # Use same timestamp or slightly later? Same is fine.
        "status": "rejected",  # Default
        "balance_before": balance_before_fee,
        "balance_after": balance_before_fee,
        "reason": ""
    }

    if balance_before_fee < config.CREDIT_FEE:
        print(f"Warning: Insufficient funds in {main_account_id} to pay credit fee ({config.CREDIT_FEE}). Fee not charged.")
        fee_tx["status"] = "rejected"
        fee_tx["reason"] = "Insufficient funds for credit fee"
    else:
        main_account['balance'] -= config.CREDIT_FEE
        fee_tx["status"] = "completed"
        fee_tx["balance_after"] = main_account['balance']
        print(f"Credit Fee Charged: {config.CREDIT_FEE} from {main_account_id}. New balance: {main_account['balance']:.2f}")

        # --- Ledger Update for Fee ---
        update_bank_ledger([
            ('customer_liabilities', -config.CREDIT_FEE),  # Customer balance decreases
            ('income', +config.CREDIT_FEE)  # Bank earns income
        ])

    # --- Save All Changes ---
    # Save main account
    account_file_path = os.path.join(config.ACCOUNTS_DIR, f"{main_account_id}.json")
    save_json(account_file_path, main_account)

    # Save credit account
    credit_account_file_path = os.path.join(config.ACCOUNTS_DIR, f"{credit_account_id}.json")
    save_json(credit_account_file_path, credit_account)

    # Add transactions to respective accounts
    add_transaction_to_account(main_account, disburse_tx)  # Disbursement to main account
    add_transaction_to_account(main_account, fee_tx)  # Fee to main account
    add_transaction_to_account(credit_account, disburse_tx)  # Link disbursement to credit account too

    return disburse_tx

def process_manual_credit_repayment(transaction_data):
    """Processes a manual (partial or full) credit repayment initiated by customer."""
    # Note: The requirements focus on automatic monthly amortization.
    # This function handles ad-hoc repayments if needed ('kann jederzeit ... zurückgezahlt werden').
    # It simplifies things: reduces principal directly, doesn't recalculate schedule here.
    # Import here to avoid circular imports
    from .account_service import get_account, add_transaction_to_account, save_account
    main_account_id = transaction_data.get('main_account')
    credit_account_id = transaction_data.get('credit_account')  # Should be CR<main_account_id>
    amount_str = transaction_data.get('amount', '0')
    repayment_amount = Decimal(amount_str).quantize(config.CHF_QUANTIZE, ROUND_HALF_UP)
    timestamp = transaction_data.get('timestamp', datetime.now().isoformat())
    transaction_id = generate_id("MRP")  # Manual RePayment

    # --- Load accounts ---
    main_account = get_account(main_account_id)
    credit_account = get_account(credit_account_id)

    # --- Base TX Record ---
    tx_record = {
        "transaction_id": transaction_id,
        "type": "manual_credit_repayment",
        "credit_account": credit_account_id,
        "main_account": main_account_id,
        "amount": repayment_amount,
        "principal_amount": Decimal('0.00'),  # Will be determined
        "interest_amount": Decimal('0.00'),  # Manual repayment goes to principal first
        "timestamp": timestamp,
        "status": "rejected",
        "credit_balance_before": None,
        "credit_balance_after": None,
        "account_balance_before": None,
        "account_balance_after": None,
        "reason": ""
    }

    # --- Validations ---
    if not main_account or not credit_account:
        tx_record["reason"] = "Account(s) not found"
        print(f"Manual Repayment Failed: {tx_record['reason']}")
        # Cannot save transaction record if accounts don't exist
        return tx_record

    if main_account['status'] == 'closed' or credit_account['status'] not in ['active', 'blocked']:
        tx_record[
            "reason"] = f"Invalid account status (Main: {main_account['status']}, Credit: {credit_account['status']})"
        print(f"Manual Repayment Failed: {tx_record['reason']}")
        # Save rejection to accounts if they exist
        if main_account: add_transaction_to_account(main_account, tx_record)
        if credit_account: add_transaction_to_account(credit_account, tx_record)
        return tx_record

    tx_record["account_balance_before"] = main_account['balance']
    tx_record["credit_balance_before"] = credit_account['balance']

    if main_account['balance'] < repayment_amount:
        tx_record["reason"] = "Insufficient funds in main account"
        print(f"Manual Repayment Failed: {tx_record['reason']}")
        tx_record["account_balance_after"] = main_account['balance']
        tx_record["credit_balance_after"] = credit_account['balance']
        add_transaction_to_account(main_account, tx_record)
        add_transaction_to_account(credit_account, tx_record)
        return tx_record

    # --- Process Repayment ---
    # Apply repayment primarily to principal for manual payments.
    # Consider accrued interest/penalties if account is blocked? Rule says 'ganz oder Teile'.
    # Simple: Reduce principal by the amount paid, up to the outstanding balance.
    principal_paid = min(repayment_amount, credit_account['balance'])
    tx_record["principal_amount"] = principal_paid
    # Any overpayment is ignored or refunded? Let's assume exact or less payment.
    if repayment_amount > credit_account['balance']:
        print(
            f"Warning: Repayment amount {repayment_amount} exceeds outstanding balance {credit_account['balance']}. Paying off balance.")
        repayment_amount = credit_account['balance']  # Adjust actual payment
        principal_paid = repayment_amount
        tx_record["amount"] = repayment_amount  # Update transaction amount

    main_account['balance'] -= repayment_amount
    credit_account['balance'] -= principal_paid

    tx_record["status"] = "completed"
    tx_record["account_balance_after"] = main_account['balance']
    tx_record["credit_balance_after"] = credit_account['balance']

    print(
        f"Manual Repayment: {repayment_amount} applied to {credit_account_id}. Credit Balance: {credit_account['balance']:.2f}, Main Balance: {main_account['balance']:.2f}")

    # --- Update Credit Account Status if Paid Off ---
    if credit_account['balance'] <= 0:
        credit_account['balance'] = Decimal('0.00')  # Ensure exactly zero
        credit_account['status'] = 'paid_off'
        credit_account['remaining_payments'] = 0
        # Clear schedule? Optional, keep for history? Keep for now.
        print(f"Credit account {credit_account_id} is now fully paid off.")

    # --- Ledger Update ---
    update_bank_ledger([
        ('customer_liabilities', -repayment_amount),  # Money leaves customer account
        ('credit_assets', -principal_paid)  # Loan asset decreases
        # No income component for manual principal repayment
    ])

    # --- Save ---
    add_transaction_to_account(main_account, tx_record)
    add_transaction_to_account(credit_account, tx_record)
    # Explicit saves just in case
    save_account(main_account)
    save_account(credit_account)

    return tx_record

def process_monthly_credit_payments(current_date):
    """Processes monthly credit payments and handles account blocking if payments fail."""
    # Import here to avoid circular imports
    from .account_service import get_account, add_transaction_to_account, save_account
    print(f"\n--- Processing Monthly Credit Payments for {current_date.isoformat()} ---")

    all_files = os.listdir(config.ACCOUNTS_DIR)
    credit_files = [f for f in all_files if f.startswith('CR') and f.endswith('.json')]

    payments_processed = 0
    payments_failed = 0
    accounts_blocked = 0

    for credit_file in credit_files:
        credit_account = load_json(os.path.join(config.ACCOUNTS_DIR, credit_file))
        
        # Skip inactive or paid off credits
        if not credit_account or credit_account['status'] not in ['active', 'blocked']:
            continue

        credit_account_id = credit_account['account_id']
        main_account_id = credit_account_id[2:]  # Remove 'CR' prefix
        main_account = get_account(main_account_id)

        if not main_account:
            print(f"Error: Main account {main_account_id} not found for credit {credit_account_id}")
            continue

        # Convert remaining_payments to int if it's a string
        remaining_payments = int(credit_account['remaining_payments']) if isinstance(credit_account['remaining_payments'], str) else credit_account['remaining_payments']

        # Skip if no payments remaining
        if remaining_payments <= 0:
            continue

        # Get current payment from schedule
        payment_index = int(config.CREDIT_TERM_MONTHS - remaining_payments)
        if payment_index >= len(credit_account['amortization_schedule']):
            print(f"Error: Invalid payment index {payment_index} for credit {credit_account_id}")
            continue

        payment_info = credit_account['amortization_schedule'][payment_index]
        
        # Convert all amounts to Decimal
        payment_amount = Decimal(str(payment_info['payment']))
        principal_amount = Decimal(str(payment_info['principal']))
        interest_amount = Decimal(str(payment_info['interest']))
        
        # Ensure balances are Decimal
        main_account['balance'] = Decimal(str(main_account['balance']))
        credit_account['balance'] = Decimal(str(credit_account['balance']))

        # Create payment transaction record
        payment_tx = {
            "transaction_id": generate_id("CRP"),
            "type": "credit_repayment",
            "credit_account": credit_account_id,
            "main_account": main_account_id,
            "amount": payment_amount,
            "principal_amount": principal_amount,
            "interest_amount": interest_amount,
            "timestamp": current_date.isoformat(),
            "status": "pending",
            "credit_balance_before": credit_account['balance'],
            "credit_balance_after": credit_account['balance'],
            "account_balance_before": main_account['balance'],
            "account_balance_after": main_account['balance']
        }

        # Check if payment can be made
        if main_account['balance'] >= payment_amount:
            # Process payment
            main_account['balance'] -= payment_amount
            credit_account['balance'] -= principal_amount
            credit_account['remaining_payments'] = remaining_payments - 1
            
            # Update payment transaction
            payment_tx["status"] = "completed"
            payment_tx["credit_balance_after"] = credit_account['balance']
            payment_tx["account_balance_after"] = main_account['balance']
            
            # Reset missed payments counter if payment successful
            credit_account['missed_payments_count'] = 0
            credit_account['last_payment_attempt_date'] = current_date.isoformat()
            
            # Update ledger
            update_bank_ledger([
                ('customer_liabilities', -payment_amount),
                ('credit_assets', -principal_amount),
                ('income', +interest_amount)
            ])
            
            print(f"Credit payment processed: {payment_amount} from {main_account_id} to {credit_account_id}")
            payments_processed += 1
            
            # Check if credit is fully paid
            if credit_account['balance'] <= Decimal('0.00'):
                credit_account['status'] = 'paid_off'
                print(f"Credit {credit_account_id} fully paid off")
        else:
            # Payment failed - handle account blocking
            payment_tx["status"] = "rejected"
            payment_tx["reason"] = "Insufficient funds"
            
            # Increment missed payments counter
            credit_account['missed_payments_count'] = credit_account.get('missed_payments_count', 0) + 1
            credit_account['last_payment_attempt_date'] = current_date.isoformat()
            
            # Block account if not already blocked
            if main_account['status'] == 'active':
                main_account['status'] = 'blocked'
                main_account['blocked_at'] = current_date.isoformat()
                accounts_blocked += 1
                print(f"Account {main_account_id} blocked due to failed credit payment")
            
            payments_failed += 1
            print(f"Credit payment failed: {main_account_id} has insufficient funds ({main_account['balance']})")

        # Save changes
        save_account(main_account)
        save_account(credit_account)
        
        # Add transaction records
        add_transaction_to_account(main_account, payment_tx)
        add_transaction_to_account(credit_account, payment_tx)

    print(f"--- Monthly Credit Payment Processing Complete ---")
    print(f"Payments Processed: {payments_processed}")
    print(f"Payments Failed: {payments_failed}")
    print(f"Accounts Blocked: {accounts_blocked}")

def calculate_daily_penalties(current_date):
    """Calculates daily penalties for blocked accounts and handles account reopening if conditions are met."""
    # Import here to avoid circular imports
    from .account_service import get_account, add_transaction_to_account, save_account
    print(f"\n--- Calculating Daily Penalties for {current_date.isoformat()} ---")

    all_files = os.listdir(config.ACCOUNTS_DIR)
    credit_files = [f for f in all_files if f.startswith('CR') and f.endswith('.json')]

    penalties_applied = 0
    accounts_reopened = 0

    for credit_file in credit_files:
        credit_account = load_json(os.path.join(config.ACCOUNTS_DIR, credit_file))
        
        # Skip inactive or paid off credits
        if not credit_account or credit_account['status'] not in ['active', 'blocked']:
            continue

        credit_account_id = credit_account['account_id']
        main_account_id = credit_account_id[2:]  # Remove 'CR' prefix
        main_account = get_account(main_account_id)

        if not main_account:
            print(f"Error: Main account {main_account_id} not found for credit {credit_account_id}")
            continue

        # Only process if main account is blocked
        if main_account['status'] != 'blocked':
            continue

        # Calculate daily penalty (30% annual rate / 365 days)
        daily_penalty_rate = Decimal('0.30') / Decimal('365')
        penalty_amount = (credit_account['balance'] * daily_penalty_rate).quantize(config.CHF_QUANTIZE, ROUND_HALF_UP)

        # Create penalty transaction
        penalty_tx = {
            "transaction_id": generate_id("PEN"),
            "type": "daily_penalty",
            "credit_account": credit_account_id,
            "main_account": main_account_id,
            "amount": penalty_amount,
            "timestamp": current_date.isoformat(),
            "status": "completed",
            "credit_balance_before": credit_account['balance'],
            "credit_balance_after": credit_account['balance'] + penalty_amount,
            "account_balance_before": main_account['balance'],
            "account_balance_after": main_account['balance']
        }

        # Apply penalty
        credit_account['balance'] += penalty_amount
        credit_account['penalty_accrued'] = credit_account.get('penalty_accrued', Decimal('0.00')) + penalty_amount
        penalties_applied += 1

        # Check if account can be reopened
        if main_account['balance'] >= Decimal('0.00'):
            # Calculate total outstanding amount (credit balance + accrued penalties)
            total_outstanding = credit_account['balance'] + credit_account['penalty_accrued']
            
            if main_account['balance'] >= total_outstanding:
                # Account can be reopened
                main_account['status'] = 'active'
                main_account['reopened_at'] = current_date.isoformat()
                credit_account['status'] = 'active'
                credit_account['penalty_accrued'] = Decimal('0.00')
                accounts_reopened += 1
                
                # Create reopening transaction
                reopen_tx = {
                    "transaction_id": generate_id("REO"),
                    "type": "account_reopening",
                    "credit_account": credit_account_id,
                    "main_account": main_account_id,
                    "amount": total_outstanding,
                    "timestamp": current_date.isoformat(),
                    "status": "completed",
                    "credit_balance_before": credit_account['balance'],
                    "credit_balance_after": credit_account['balance'],
                    "account_balance_before": main_account['balance'],
                    "account_balance_after": main_account['balance'] - total_outstanding,
                    "note": f"Account reopened after paying outstanding balance and penalties"
                }
                
                # Apply payment
                main_account['balance'] -= total_outstanding
                credit_account['balance'] = Decimal('0.00')
                
                # Update ledger
                update_bank_ledger([
                    ('customer_liabilities', -total_outstanding),
                    ('credit_assets', -credit_account['balance']),
                    ('income', +credit_account['penalty_accrued'])
                ])
                
                # Add reopening transaction
                add_transaction_to_account(main_account, reopen_tx)
                add_transaction_to_account(credit_account, reopen_tx)
                
                print(f"Account {main_account_id} reopened after paying outstanding balance and penalties")
            else:
                print(f"Account {main_account_id} has insufficient funds to cover outstanding balance and penalties")

        # Save changes
        save_account(main_account)
        save_account(credit_account)
        
        # Add penalty transaction
        add_transaction_to_account(main_account, penalty_tx)
        add_transaction_to_account(credit_account, penalty_tx)

    print(f"--- Daily Penalty Processing Complete ---")
    print(f"Penalties Applied: {penalties_applied}")
    print(f"Accounts Reopened: {accounts_reopened}")

def write_off_bad_credits(current_date):
    """Identifies and writes off credits with no payments for WRITE_OFF_MONTHS."""
    # Import here to avoid circular imports
    from .account_service import get_account, add_transaction_to_account, save_account
    print(f"\n--- Checking for Bad Credit Write-offs for {current_date.strftime('%Y-%m-%d')} ---")
    written_off_count = 0
    all_credit_ids = [f.replace('.json', '') for f in os.listdir(config.ACCOUNTS_DIR) if
                      f.startswith('CR') and f.endswith('.json')]

    for credit_account_id in all_credit_ids:
        credit_account = get_account(credit_account_id)

        # Check accounts that are blocked and have missed payments
        if not credit_account or credit_account['status'] != 'blocked' or \
                credit_account['balance'] <= 0 or credit_account.get('missed_payments_count', 0) == 0:
            continue

        # Check how long ago the *last payment attempt* was made.
        # If no payment has *ever* succeeded, maybe use credit_start_date?
        # Using last_payment_attempt_date is more robust if payments started then stopped.
        last_attempt_str = credit_account.get('last_payment_attempt_date')
        if not last_attempt_str:
            # If no attempts recorded, maybe check start date (only if blocked for a while)
            start_date_str = credit_account.get('credit_start_date')
            if not start_date_str: continue  # Cannot determine age
            last_relevant_date = parse_datetime(start_date_str)

        else:
            last_relevant_date = parse_datetime(last_attempt_str)

        if not last_relevant_date: continue  # Skip if date is invalid

        # Check if WRITE_OFF_MONTHS have passed since the last attempt/start
        if current_date >= (last_relevant_date + relativedelta(months=config.WRITE_OFF_MONTHS)):
            written_off_count += 1
            write_off_amount = credit_account['balance']  # The amount to write off
            transaction_id = generate_id("WOFF")  # Write Off
            timestamp = current_date.isoformat()

            print(
                f"Writing Off Credit: {credit_account_id}. Amount: {write_off_amount}. Reason: Non-payment for >{config.WRITE_OFF_MONTHS} months.")

            tx_record = {
                "transaction_id": transaction_id,
                "type": "credit_write_off",
                "credit_account": credit_account_id,
                "amount": write_off_amount,
                "timestamp": timestamp,
                "status": "completed",
                "credit_balance_before": write_off_amount,
                "credit_balance_after": Decimal('0.00'),
            }

            # Update credit account
            credit_account['status'] = 'written_off'
            credit_account['balance'] = Decimal('0.00')
            credit_account['remaining_payments'] = 0  # No more payments due

            # Ledger Update (Decrease asset, Decrease income/recognize loss)
            update_bank_ledger([
                ('credit_assets', -write_off_amount),
                ('income', -write_off_amount)  # Loss reduces income
            ])

            # Save transaction and account state
            add_transaction_to_account(credit_account, tx_record)  # Saves account

    print(f"--- Credit Write-offs Complete. Written Off: {written_off_count} ---")
