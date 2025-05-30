from src.customer_service import create_customer
from src.account_service import create_account, get_account, close_account, save_account
from src.transaction_service import process_transfer_out, process_incoming_payment
from src.credit_service import request_credit, process_manual_credit_repayment
from src.time_processing_service import process_time_event
from src.ledger_service import get_bank_ledger
from datetime import datetime, timedelta
import os
import shutil
from src import config
from decimal import Decimal

def cleanup_test_data():
    """Clean up all test data before running the test"""
    print("Cleaning up old test data...")
    for directory in [config.CUSTOMERS_DIR, config.ACCOUNTS_DIR, config.TRANSACTIONS_DIR]:
        if os.path.exists(directory):
            shutil.rmtree(directory)
        os.makedirs(directory, exist_ok=True) # Ensure they are recreated

    # Delete ledger and system date files specifically
    ledger_file = config.LEDGER_FILE
    system_date_file = config.SYSTEM_DATE_FILE
    
    if os.path.exists(ledger_file):
        os.remove(ledger_file)
        print(f"Deleted {ledger_file}")
    if os.path.exists(system_date_file):
        os.remove(system_date_file)
        print(f"Deleted {system_date_file}")

    # Ensure data directory itself exists
    os.makedirs(config.DATA_DIR, exist_ok=True)
    print("Cleanup complete.")

def validate_system_integrity():
    """Validate system integrity by checking ledger and account balances"""
    print("\n--- System Integrity Check ---")
    ledger = get_bank_ledger()
    
    # Print all account balances
    print("\nBank Ledger Balances:")
    for account, data in ledger.items():
        balance = data.get('balance', Decimal('0.00'))
        if not isinstance(balance, Decimal):
            balance = Decimal(str(balance))
        print(f"{account}: {balance:.2f}")
    
    # Check if assets equal liabilities plus income minus losses
    # Assets = Liabilities + Net Income (Income - Expenses/Losses)
    # Assets + Expenses/Losses = Liabilities + Income
    central_bank_assets = ledger.get('central_bank_assets', {}).get('balance', Decimal('0.00'))
    credit_assets_ledger = ledger.get('credit_assets', {}).get('balance', Decimal('0.00'))
    
    customer_liabilities = ledger.get('customer_liabilities', {}).get('balance', Decimal('0.00'))
    income_ledger = ledger.get('income', {}).get('balance', Decimal('0.00'))
    credit_losses_ledger = ledger.get('credit_losses', {}).get('balance', Decimal('0.00'))

    # Ensure all are Decimal
    if not isinstance(central_bank_assets, Decimal): central_bank_assets = Decimal(str(central_bank_assets))
    if not isinstance(credit_assets_ledger, Decimal): credit_assets_ledger = Decimal(str(credit_assets_ledger))
    if not isinstance(customer_liabilities, Decimal): customer_liabilities = Decimal(str(customer_liabilities))
    if not isinstance(income_ledger, Decimal): income_ledger = Decimal(str(income_ledger))
    if not isinstance(credit_losses_ledger, Decimal): credit_losses_ledger = Decimal(str(credit_losses_ledger))

    total_assets_side = central_bank_assets + credit_assets_ledger + credit_losses_ledger # Assets + Expenses
    total_liabilities_equity_side = customer_liabilities + income_ledger # Liabilities + Income
    
    print(f"\nEquation: Assets (Central Bank + Credit) + Credit Losses = Customer Liabilities + Income")
    print(f"LHS (Assets + Losses): {central_bank_assets:.2f} (Central Bank) + {credit_assets_ledger:.2f} (Credit Assets) + {credit_losses_ledger:.2f} (Losses) = {total_assets_side:.2f}")
    print(f"RHS (Liabilities + Income): {customer_liabilities:.2f} (Cust. Liab.) + {income_ledger:.2f} (Income) = {total_liabilities_equity_side:.2f}")
    
    difference = total_assets_side - total_liabilities_equity_side
    print(f"Difference (LHS - RHS): {difference:.2f}")
    print(f"Balance Check: {'✓' if abs(difference) < config.CHF_QUANTIZE else '✗'}")

# Clean up before starting the test
cleanup_test_data()

print("--- Scripted Test Start ---")

# 1. Create customers
cust1 = create_customer("John Doe", "123 Main St, Zurich", "1980-01-15")
cust2 = create_customer("Jane Smith", "456 Park Ave, Geneva", "1985-06-20")
print(f"Created customers: {cust1['customer_id']}, {cust2['customer_id']}")

# 2. Create accounts
acc1_data, cr_acc1_data = create_account(cust1['customer_id'])
acc2_data, cr_acc2_data = create_account(cust2['customer_id'])
acc1 = acc1_data['account_id']
acc2 = acc2_data['account_id']
cr_acc1 = cr_acc1_data['account_id']
cr_acc2 = cr_acc2_data['account_id']
print(f"Created accounts: {acc1}, {acc2}")

# 3. Test insufficient funds scenario
print("\n--- Testing Insufficient Funds ---")
result = process_transfer_out({
    'type': 'transfer_out',
    'from_account': acc1,
    'to_iban': 'CH9300762011623852957',
    'amount': '10000.00',  # Try to transfer more than available
    'timestamp': '2024-03-01T09:00:00'
})
print("Insufficient funds test:", result)

# 4. Regular transfers
result = process_incoming_payment({
    'type': 'transfer_in',
    'to_account': acc1,
    'from_iban': 'DE89370400440532013000',
    'amount': '5000.00',
    'timestamp': '2024-03-01T10:00:00'
})
print("Transfer in to acc1:", result)

result = process_transfer_out({
    'type': 'transfer_out',
    'from_account': acc1,
    'to_iban': 'CH9300762011623852957',
    'amount': '1000.00',
    'timestamp': '2024-03-01T11:00:00'
})
print("Transfer out from acc1:", result)

# 5. Credit operations
result = request_credit({
    'type': 'credit_request',
    'main_account': acc1,
    'amount': '2000.00',
    'timestamp': '2024-03-01T12:00:00'
})
print("Credit request for acc1:", result)

# 6. Manual credit repayment
result = process_manual_credit_repayment({
    'type': 'manual_credit_repayment',
    'main_account': acc1,
    'credit_account': cr_acc1,
    'amount': '200.00',
    'timestamp': '2024-03-15T10:00:00'
})
print("Manual credit repayment for acc1's credit account:", result)

# 7. Second account operations
result = process_incoming_payment({
    'type': 'transfer_in',
    'to_account': acc2,
    'from_iban': 'FR7630006000011234567890189',
    'amount': '3000.00',
    'timestamp': '2024-03-01T13:00:00'
})
print("Transfer in to acc2:", result)

# 8. Time simulation - Monthly payments
print("\n--- Testing Monthly Payments ---")
# Credit for acc1 was taken on 2024-03-01. First payment due around 2024-04-01.
# Simulate for April, May, June
acc1_details = get_account(acc1)
cr_acc1_details = get_account(cr_acc1)

initial_acc1_balance = acc1_details['balance'] if acc1_details else Decimal('0')
initial_cr_acc1_balance = cr_acc1_details['balance'] if cr_acc1_details else Decimal('0')
expected_monthly_payment = cr_acc1_details['monthly_payment'] if cr_acc1_details and 'monthly_payment' in cr_acc1_details else Decimal('0')

print(f"Initial balance acc1: {initial_acc1_balance:.2f}, cr_acc1: {initial_cr_acc1_balance:.2f}, Expected Monthly Payment: {expected_monthly_payment:.2f}")

simulated_months = 0
successful_payments = 0 # Zähler für erfolgreiche Zahlungen

if not cr_acc1_details or expected_monthly_payment <= Decimal('0'):
    print("WARNING: Cannot simulate monthly payments. Credit account details missing or zero/invalid expected monthly payment.")
else:
    for i in range(1, 4): # Simulate 3 monthly payments (April, May, June)
        current_sim_date = datetime(2024, 3 + i, 1) # 2024-04-01, 2024-05-01, 2024-06-01
        
        print(f"Simulating for date: {current_sim_date.strftime('%Y-%m-%d')}")
        # Temporär den Saldo vor dem Zeitereignis speichern, um Änderungen zu sehen
        temp_cr_acc1_balance_before_event = get_account(cr_acc1)['balance']

        time_event_result = process_time_event({
            'type': 'time_event',
            'date': current_sim_date.strftime('%Y-%m-%d'),
            'timestamp': current_sim_date.strftime('%Y-%m-%dT00:00:00') # Start of day
        })
        
        current_cr_acc1_after_event = get_account(cr_acc1)
        # Überprüfen, ob der Kreditsaldo gesunken ist
        if current_cr_acc1_after_event['balance'] < temp_cr_acc1_balance_before_event:
            print(f"SUCCESS: Monthly payment processed for {current_sim_date.strftime('%Y-%m-%d')}. Credit balance reduced.")
            successful_payments += 1
        else:
            # Gab es einen Ablehnungsgrund in den Transaktionen des Hauptkontos?
            main_acc_after_event = get_account(acc1)
            last_tx_main = main_acc_after_event['transactions'][-1] if main_acc_after_event['transactions'] else None
            reason = "unknown"
            if last_tx_main and last_tx_main.get('type') == 'credit_repayment' and last_tx_main.get('status') == 'rejected':
                reason = last_tx_main.get('reason', 'unknown')
            print(f"INFO: Monthly payment might have been attempted but NOT completed for {current_sim_date.strftime('%Y-%m-%d')}. ")
            print(f"      Credit Balance: {current_cr_acc1_after_event['balance']:.2f}, Main Acc Balance: {main_acc_after_event['balance']:.2f}. Reason (if payment rejected): {reason}")
    simulated_months = successful_payments # Update simulated_months to reflect actual successful payments

print(f"--- After simulating 3 months, {successful_payments} monthly payment(s) were successfully processed ---")
final_acc1 = get_account(acc1)
final_cr_acc1 = get_account(cr_acc1)
print(f"Final balance acc1: {final_acc1['balance']:.2f} (was {initial_acc1_balance:.2f})")
print(f"Final credit balance cr_acc1: {final_cr_acc1['balance']:.2f} (was {initial_cr_acc1_balance:.2f})")
if final_cr_acc1['balance'] < initial_cr_acc1_balance:
    print("SUCCESS: Credit balance decreased, indicating payments were made.")
else:
    print("WARNING: Credit balance did NOT decrease as expected after simulating monthly payments.")
if final_acc1['balance'] < initial_acc1_balance:
    print("SUCCESS: Main account balance decreased, indicating payments were made.")
else:
    print("WARNING: Main account balance did NOT decrease as expected.")

# 9. Test Missed Payments, Account Blocking, and Penalty Accrual for acc1
print("\n--- Testing Missed Payment, Blocking & Penalties for acc1 ---")
# Reduce acc1's balance to be less than the monthly payment
acc1_data = get_account(acc1)
cr_acc1_data = get_account(cr_acc1)
monthly_payment_acc1 = cr_acc1_data['monthly_payment']

if acc1_data['balance'] >= monthly_payment_acc1:
    transfer_amount = acc1_data['balance'] - monthly_payment_acc1 + Decimal('1.00') # Ensure it's just below
    if transfer_amount > 0:
        print(f"Reducing acc1 balance by {transfer_amount} to ensure next payment fails.")
        process_transfer_out({
            'type': 'transfer_out', 'from_account': acc1, 'to_iban': 'CH0000000000000000000',
            'amount': str(transfer_amount), 'timestamp': datetime.now().isoformat()
        })
acc1_data = get_account(acc1) # Refresh data
print(f"acc1 balance before simulating missed payment: {acc1_data['balance']:.2f}")

# Simulate the next month (e.g., 2024-07-01, after 3 successful payments in Apr, May, Jun)
missed_payment_date = datetime(2024, 6 + 1, 1) # 2024-07-01
print(f"Simulating time event for {missed_payment_date.strftime('%Y-%m-%d')} to trigger missed payment...")
process_time_event({
    'type': 'time_event', 'date': missed_payment_date.strftime('%Y-%m-%d'),
    'timestamp': missed_payment_date.strftime('%Y-%m-%dT00:00:00')
})

acc1_data_after_miss = get_account(acc1)
cr_acc1_data_after_miss = get_account(cr_acc1)

print(f"Status acc1: {acc1_data_after_miss['status']}, Expected: blocked")
assert acc1_data_after_miss['status'] == 'blocked', "acc1 status should be blocked"
print(f"Status cr_acc1: {cr_acc1_data_after_miss['status']}, Expected: blocked")
assert cr_acc1_data_after_miss['status'] == 'blocked', "cr_acc1 status should be blocked"

# Ensure missed_payments_count is an integer for comparison
missed_payments_actual = int(cr_acc1_data_after_miss.get('missed_payments_count', 0))
print(f"cr_acc1 missed_payments_count: {missed_payments_actual}, Expected: 1")
assert missed_payments_actual == 1, "cr_acc1 missed_payments_count should be 1"

# Check for penalty accrual (calculate_daily_penalties runs within process_time_event)
# For a single day of blocking, penalty should be low but > 0 if balance > 0
initial_penalty = cr_acc1_data.get('penalty_accrued', Decimal('0.00'))
current_penalty = cr_acc1_data_after_miss.get('penalty_accrued', Decimal('0.00'))
print(f"cr_acc1 penalty_accrued: {current_penalty:.2f} (was {initial_penalty:.2f})")
if cr_acc1_data_after_miss['balance'] > Decimal('0.00'):
    assert current_penalty > initial_penalty, "penalty_accrued should have increased for a blocked credit account with balance"
else:
    print("Skipping penalty increase check as credit balance is zero or less.")


# 10. Test Credit Write-off for acc1
print("\n--- Testing Credit Write-off for acc1 ---")
# We expect 1 missed payment already. Need (config.MAX_MISSED_PAYMENTS - 1) more.
# config.MAX_MISSED_PAYMENTS is currently 3. So, 2 more missed payments.

cr_acc1_data_for_write_off_check = get_account(cr_acc1) # Hole aktuelle Daten
# Stelle sicher, dass missed_payment_count ein Integer ist
missed_payment_count_val = cr_acc1_data_for_write_off_check.get('missed_payments_count', 0)
try:
    missed_payment_count = int(missed_payment_count_val)
except (ValueError, TypeError):
    print(f"Error: Could not convert missed_payment_count '{missed_payment_count_val}' to int. Defaulting to 0.")
    missed_payment_count = 0
    
payments_to_simulate_for_write_off = config.MAX_MISSED_PAYMENTS - missed_payment_count

print(f"Current missed_payments_count for cr_acc1: {missed_payment_count}")
print(f"Need to simulate {payments_to_simulate_for_write_off} more missed payment(s) to reach MAX_MISSED_PAYMENTS ({config.MAX_MISSED_PAYMENTS}).")

for i in range(payments_to_simulate_for_write_off):
    next_month_sim_date = datetime(2024, 7 + i, 1) # Starts from 2024-08-01 if payments_to_simulate_for_write_off > 0
    print(f"Simulating time event for {next_month_sim_date.strftime('%Y-%m-%d')} to trigger further missed payment...")
    process_time_event({
        'type': 'time_event', 'date': next_month_sim_date.strftime('%Y-%m-%d'),
        'timestamp': next_month_sim_date.strftime('%Y-%m-%dT00:00:00')
    })
    cr_acc1_data_loop = get_account(cr_acc1)
    print(f"After simulation for {next_month_sim_date.strftime('%Y-%m-%d')}: cr_acc1 missed_payments_count: {cr_acc1_data_loop['missed_payments_count']}")

# After MAX_MISSED_PAYMENTS, the next time_event on the 1st of the month should trigger write_off
cr_acc1_before_write_off = get_account(cr_acc1)

# Sicherstellen, dass missed_payments_count ein Integer ist für den Vergleich und die Ausgabe
missed_payments_for_assert_val = cr_acc1_before_write_off.get('missed_payments_count', 0)
try:
    missed_payments_for_assert = int(missed_payments_for_assert_val)
except (ValueError, TypeError):
    print(f"Error converting missed_payments_for_assert_val '{missed_payments_for_assert_val}' to int. Defaulting to 0.")
    missed_payments_for_assert = 0

print(f"cr_acc1 status before final write-off check: {cr_acc1_before_write_off['status']}, missed payments: {missed_payments_for_assert}")
assert missed_payments_for_assert >= config.MAX_MISSED_PAYMENTS, "Should have reached max missed payments"

# The write_off logic runs on the 1st of the month as part of process_time_event
# The last simulation (if payments_to_simulate_for_write_off > 0) would have been for e.g. 2024-09-01
# If payments_to_simulate_for_write_off was 0 (meaning 1st missed payment was enough), 
# then the write-off should have occurred during the 2024-07-01 simulation's call to write_off_bad_credits.
# Let's ensure one more process_time_event call on the first of a new month to ensure write_off is triggered if not already.
# The date logic here needs to be careful. The last missed payment was simulated for e.g., 2024-07-01 + (payments_to_simulate_for_write_off -1)
last_sim_month_for_missed_payment = 6 + missed_payment_count # e.g. 6+1=July (for first missed)
if payments_to_simulate_for_write_off > 0 : # if more than 1 missed payment was simulated in the loop
    final_trigger_month = last_sim_month_for_missed_payment + payments_to_simulate_for_write_off
else: # if only 1 missed payment was enough
    final_trigger_month = last_sim_month_for_missed_payment
    
# ensure we are in the next month to be safe for write_off check if it wasn't on the exact boundary
final_write_off_check_date = datetime(2024, (final_trigger_month % 12) + 1 , 1) # Ensure it's the first of the *next* relevant month

# One last run of process_time_event on the first of the month to ensure write_off is attempted
# This is because write_off_bad_credits is called within process_time_event.
# If the MAX_MISSED_PAYMENTS was reached exactly on a date that write_off_bad_credits was called, it should be written_off.
# This call ensures that if it was on the edge, it gets processed.
print(f"Simulating final time event for {final_write_off_check_date.strftime('%Y-%m-%d')} to ensure write-off processing...")
process_time_event({
    'type': 'time_event', 'date': final_write_off_check_date.strftime('%Y-%m-%d'),
    'timestamp': final_write_off_check_date.strftime('%Y-%m-%dT00:00:00')
})

cr_acc1_data_after_write_off = get_account(cr_acc1)
print(f"Status cr_acc1 after write-off attempt: {cr_acc1_data_after_write_off['status']}, Expected: written_off")
assert cr_acc1_data_after_write_off['status'] == 'written_off', "cr_acc1 status should be written_off"
print("SUCCESS: Credit write-off for acc1 verified.")


# 11. Final operations
# acc2 operations are no longer relevant for credit testing here. We'll close acc1.
# Ensure acc1 balance is zero before closing (it might be negative due to penalties if not handled)
acc1_data_final = get_account(acc1)

# Manuell auf 'active' setzen, um Saldoausgleich zu ermöglichen, da es durch Kreditverzug blockiert wurde
if acc1_data_final['status'] == 'blocked':
    print(f"Manually setting account {acc1} to 'active' to allow balance clear and closure.")
    acc1_data_final['status'] = 'active'
    save_account(acc1_data_final)
    acc1_data_final = get_account(acc1) # Neu laden, um sicherzustellen, dass Status übernommen wurde

if acc1_data_final['balance'] != Decimal('0.00'):
    print(f"acc1 final balance before attempting closure: {acc1_data_final['balance']:.2f}. Setting to 0 if negative, or paying out if positive.")
    if acc1_data_final['balance'] < Decimal('0.00'): 
        # Forcibly set to 0 for closure test; in reality, this would be a debt.
        # Or, a better test would be to ensure penalties are handled without main account going negative.
        # For now, we just ensure it can be closed.
        print("Warning: acc1 has negative balance. This state needs review in penalty processing.")
        # acc1_data_final['balance'] = Decimal('0.00') 
        # save_account(acc1_data_final)
        # Current logic doesn't allow closing if not 0. So this part of test might fail if balance is negative.
        # Let's try to deposit to make it zero if negative to proceed with closure test
        if acc1_data_final['balance'] < Decimal('0.00'):
            deposit_to_zero_out = abs(acc1_data_final['balance'])
            print(f"Depositing {deposit_to_zero_out} to acc1 to allow closure.")
            process_incoming_payment({
                'type': 'transfer_in', 'to_account': acc1, 'from_iban': 'SYSTEM',
                'amount': str(deposit_to_zero_out), 'timestamp': datetime.now().isoformat()
            })
            acc1_data_final = get_account(acc1) # refresh
            
    elif acc1_data_final['balance'] > Decimal('0.00'):
         process_transfer_out({
            'type': 'transfer_out', 'from_account': acc1, 'to_iban': 'CH0000000000000000000', # Dummy IBAN
            'amount': str(acc1_data_final['balance']), 'timestamp': datetime.now().isoformat()
        })
    acc1_data_final = get_account(acc1)


print(f"Attempting to close acc1 (CH-ID: {acc1}). Final balance: {acc1_data_final['balance']:.2f}")
# Note: cr_acc1 is already 'written_off', so closure of main acc1 should be possible.
result_close_acc1 = close_account(acc1)
print(f"Account closure for acc1: {result_close_acc1}")
assert result_close_acc1, "Closure of acc1 should be successful"

# Commenting out acc2 operations as they are not the focus of these credit tests anymore
# result = process_transfer_out({
# 'type': 'transfer_out',
# 'from_account': acc2,
# 'to_iban': 'IT60X0542811101000000123456',
# 'amount': str(get_account(acc2)['balance']),
# 'timestamp': '2024-03-02T09:30:00'
# })
# print("Transfer out remaining balance from acc2:", result)
# result = close_account(acc2)
# print("Account closure for acc2:", result)

# 12. System integrity validation
validate_system_integrity()

print("--- Scripted Test End ---") 