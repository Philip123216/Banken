# src/credit_service.py
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from dateutil.relativedelta import relativedelta # Externes Paket
import os
from . import config # RELATIV
from .utils import generate_id, save_json, load_json, parse_datetime # RELATIV
from .account_service import get_account, add_transaction_to_account, save_account # RELATIV
from .ledger_service import update_bank_ledger # RELATIV
from .time_processing_service import get_system_date # RELATIV

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
    """Processes scheduled monthly payments for all active credit accounts."""
    print(f"\n--- Processing Monthly Credit Payments for {current_date.strftime('%Y-%m-%d')} ---")
    processed_count = 0
    failed_count = 0
    all_account_ids = [f.replace('.json', '') for f in os.listdir(config.ACCOUNTS_DIR) if
                       f.startswith('CR') and f.endswith('.json')]

    for credit_account_id in all_account_ids:
        credit_account = get_account(credit_account_id)

        # Only process active credits with outstanding balance and payments remaining
        if not credit_account or credit_account['status'] != 'active' or \
                credit_account['balance'] <= 0 or credit_account['remaining_payments'] <= 0:
            continue

        main_account_id = credit_account_id[2:]  # Remove 'CR' prefix to get main account ID
        main_account = get_account(main_account_id)

        if not main_account:
            print(f"Error: Main account {main_account_id} not found for credit {credit_account_id}. Skipping.")
            continue

        # Get monthly payment amount from credit account
        payment_amount = credit_account.get('monthly_payment', Decimal('0.00'))
        if payment_amount <= 0:
            print(f"Error: Invalid monthly payment amount for credit {credit_account_id}. Skipping.")
            continue

        # Get amortization schedule
        schedule = credit_account.get('amortization_schedule', [])
        payment_number_due = (config.CREDIT_TERM_MONTHS - credit_account['remaining_payments']) + 1
        payment_info = next((p for p in schedule if p.get('month') == payment_number_due), None)

        if not payment_info:
            print(f"Warning: Could not find payment info for payment #{payment_number_due} for credit {credit_account_id}. Skipping.")
            continue

        # Use scheduled amounts, ensure they are Decimal
        payment_amount = Decimal(str(payment_info.get('payment', payment_amount)))
        principal_component = Decimal(str(payment_info.get('principal', '0')))
        interest_component = Decimal(str(payment_info.get('interest', '0')))

        transaction_id = generate_id("RP")  # Repayment
        timestamp = current_date.isoformat()

        # --- Base TX Record ---
        tx_record = {
            "transaction_id": transaction_id,
            "type": "credit_repayment",
            "credit_account": credit_account_id,
            "main_account": main_account_id,
            "amount": payment_amount,
            "principal_amount": principal_component,
            "interest_amount": interest_component,
            "timestamp": timestamp,
            "status": "rejected",
            "credit_balance_before": credit_account['balance'],
            "credit_balance_after": credit_account['balance'],
            "account_balance_before": main_account['balance'],
            "account_balance_after": main_account['balance'],
            "reason": ""
        }

        credit_account['last_payment_attempt_date'] = current_date.isoformat()  # Record attempt

        # Check for sufficient funds in the main account
        if main_account['status'] != 'active' or main_account['balance'] < payment_amount:
            failed_count += 1
            tx_record["status"] = "rejected"
            tx_record["reason"] = f"Insufficient funds or account not active (Status: {main_account['status']})"
            print(f"Payment Failed: {credit_account_id}. Reason: {tx_record['reason']}")

            # --- Handle consequences of failed payment ---
            # Block the main account
            if main_account['status'] != 'blocked':
                main_account['status'] = 'blocked'
                print(f"Account {main_account_id} status set to 'blocked'.")

            # Increment missed payment counter on credit account
            credit_account['missed_payments_count'] = credit_account.get('missed_payments_count', 0) + 1
            credit_account['status'] = 'blocked'  # Also block the credit account logic state

            # Accrue standard interest even if payment failed, as per requirement "Kreditzins läuft ... weiter"
            # This adds the *interest portion* of the missed payment to the balance.
            # Penalty interest is handled separately (daily).
            interest_accrual_tx_id = generate_id("IA")
            credit_balance_before_interest = credit_account['balance']
            credit_account['balance'] += interest_component
            credit_balance_after_interest = credit_account['balance']

            interest_tx = {
                "transaction_id": interest_accrual_tx_id,
                "type": "interest_accrual",
                "credit_account": credit_account_id,
                "amount": interest_component,  # The interest that *should* have been paid
                "timestamp": timestamp,
                "status": "completed",  # Accrual is completed
                "credit_balance_before": credit_balance_before_interest,
                "credit_balance_after": credit_balance_after_interest,
                "note": f"Interest accrued on unpaid balance due to missed payment #{payment_number_due}"
            }
            add_transaction_to_account(credit_account_id, interest_tx)  # Adds to history

            # Ledger update for accrued interest (increase asset, increase income)
            update_bank_ledger([
                ('credit_assets', +interest_component),
                ('income', +interest_component)
            ])

            print(f"  Interest Accrued: {interest_component} added to {credit_account_id} balance.")

        else:
            # --- Process successful payment ---
            processed_count += 1
            tx_record["status"] = "completed"

            # Update balances
            main_account['balance'] -= payment_amount
            # Reduce credit balance ONLY by principal amount
            credit_account['balance'] -= principal_component

            # Update remaining payments
            credit_account['remaining_payments'] -= 1

            # Reset missed counter on successful payment
            credit_account['missed_payments_count'] = 0
            # Ensure credit status is active if it was somehow blocked but payment succeeded
            if credit_account['status'] == 'blocked':
                credit_account['status'] = 'active'

            # Update balances in transaction record
            tx_record["credit_balance_after"] = credit_account['balance']
            tx_record["account_balance_after"] = main_account['balance']

            print(
                f"Payment Processed: {credit_account_id}. Amount: {payment_amount}. Credit Balance: {credit_account['balance']:.2f}")

            # Check if loan is now fully paid off
            if credit_account['remaining_payments'] <= 0 or credit_account['balance'] <= 0:
                # Adjust final balance to exactly zero if slightly off due to rounding
                final_diff = credit_account['balance']
                if abs(final_diff) > 0:
                    print(f"Applying final balance adjustment of {final_diff:.2f} to {main_account_id}")
                    # If negative balance, means overpaid slightly -> refund to main? Or just zero out? Zero out.
                    # If positive balance, means underpaid slightly -> take from main? Or zero out? Zero out.
                    main_account['balance'] -= final_diff  # Adjust main account to reflect exact payoff
                    tx_record["account_balance_after"] = main_account['balance']
                    credit_account['balance'] = Decimal('0.00')
                    tx_record["credit_balance_after"] = credit_account['balance']

                credit_account['status'] = 'paid_off'
                credit_account['balance'] = Decimal('0.00')
                credit_account['remaining_payments'] = 0
                print(f"  Credit {credit_account_id} is now fully paid off.")

            # Ledger update for successful payment
            update_bank_ledger([
                ('customer_liabilities', -payment_amount),  # Money leaves customer main account
                ('credit_assets', -principal_component),  # Loan principal reduced
                ('income', +interest_component)  # Bank earns interest income
            ])

        # --- Save results for both success and failure ---
        add_transaction_to_account(main_account, tx_record)
        add_transaction_to_account(credit_account, tx_record)
        # Explicit saves
        save_account(main_account)
        save_account(credit_account)

    print(f"--- Monthly Payments Complete. Processed: {processed_count}, Failed/Blocked: {failed_count} ---")

def calculate_daily_penalties(current_date):
    """Calculates and applies daily penalty interest to blocked credit accounts."""
    print(f"\n--- Calculating Daily Penalties for {current_date.strftime('%Y-%m-%d')} ---")
    penalty_count = 0
    all_credit_ids = [f.replace('.json', '') for f in os.listdir(config.ACCOUNTS_DIR) if
                      f.startswith('CR') and f.endswith('.json')]

    for credit_account_id in all_credit_ids:
        credit_account = get_account(credit_account_id)

        # Only apply penalties to accounts that are 'blocked' (due to missed payments)
        # and have an outstanding balance.
        if not credit_account or credit_account['status'] != 'blocked' or credit_account['balance'] <= 0:
            continue

        # Calculate penalty interest (simple daily interest on current outstanding balance)
        outstanding_balance = credit_account['balance']
        daily_penalty = (outstanding_balance * config.PENALTY_DAILY_RATE).quantize(config.CHF_QUANTIZE, ROUND_HALF_UP)

        if daily_penalty <= 0:
            continue  # No penalty if balance is zero or rate results in zero

        penalty_count += 1
        transaction_id = generate_id("PEN")  # Penalty
        timestamp = current_date.isoformat()

        # Add penalty amount to the outstanding balance and track separately?
        # Requirement: "Strafzins ist 30% und wird täglich berechnet" -> Implying it adds to the debt.
        # Requirement: "Kreditzins läuft auf dem Kredit weiter" -> Regular interest also accrues (handled in monthly processing failure).
        # Let's add penalty direct to balance and also track cumulative penalty.

        credit_balance_before = credit_account['balance']
        cumulative_penalty_before = credit_account.get('penalty_accrued', Decimal('0.00'))

        credit_account['balance'] += daily_penalty
        credit_account['penalty_accrued'] = cumulative_penalty_before + daily_penalty

        tx_record = {
            "transaction_id": transaction_id,
            "type": "penalty_interest",
            "credit_account": credit_account_id,
            "amount": daily_penalty,
            "timestamp": timestamp,
            "status": "completed",  # Penalty application is completed
            "credit_balance_before": credit_balance_before,
            "credit_balance_after": credit_account['balance'],
            "note": f"Daily penalty interest ({config.PENALTY_INTEREST_RATE_PA * 100}%)"
        }

        print(
            f"Penalty Applied: {credit_account_id}. Amount: {daily_penalty}. New Balance: {credit_account['balance']:.2f}")

        # Ledger Update (Increase asset, Increase income)
        # Recognizing penalty as income immediately is aggressive but consistent with interest accrual.
        update_bank_ledger([
            ('credit_assets', +daily_penalty),
            ('income', +daily_penalty)
        ])

        # Save transaction and account state
        add_transaction_to_account(credit_account, tx_record)  # Saves account

    print(f"--- Daily Penalties Complete. Penalties Applied: {penalty_count} ---")

def write_off_bad_credits(current_date):
    """Identifies and writes off credits with no payments for WRITE_OFF_MONTHS."""
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
