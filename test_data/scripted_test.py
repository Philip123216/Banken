from src.customer_service import create_customer
from src.account_service import create_account, get_account
from src.transaction_service import process_transfer_out, process_incoming_payment, process_account_closure
from src.credit_service import request_credit, process_manual_credit_repayment
from src.time_processing_service import process_time_event
from datetime import datetime

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

# 3. Incoming transfer to acc1
result = process_incoming_payment({
    'type': 'transfer_in',
    'to_account': acc1,
    'from_iban': 'DE89370400440532013000',
    'amount': '5000.00',
    'timestamp': '2024-03-01T10:00:00'
})
print("Transfer in to acc1:", result)

# 4. Outgoing transfer from acc1
result = process_transfer_out({
    'type': 'transfer_out',
    'from_account': acc1,
    'to_iban': 'CH9300762011623852957',
    'amount': '1000.00',
    'timestamp': '2024-03-01T11:00:00'
})
print("Transfer out from acc1:", result)

# 5. Credit request for acc1 (fix field name)
result = request_credit({
    'type': 'credit_request',
    'main_account': acc1,
    'amount': '2000.00',
    'term_months': 12,
    'timestamp': '2024-03-01T12:00:00'
})
print("Credit request for acc1:", result)

# 6. Manual credit repayment for acc1's credit account (fix field names)
result = process_manual_credit_repayment({
    'type': 'manual_credit_repayment',
    'main_account': acc1,
    'credit_account': cr_acc1,
    'amount': '200.00',
    'timestamp': '2024-03-15T10:00:00'
})
print("Manual credit repayment for acc1's credit account:", result)

# 7. Incoming transfer to acc2
result = process_incoming_payment({
    'type': 'transfer_in',
    'to_account': acc2,
    'from_iban': 'FR7630006000011234567890189',
    'amount': '3000.00',
    'timestamp': '2024-03-01T13:00:00'
})
print("Transfer in to acc2:", result)

# 8. Time event: quarterly fee
result = process_time_event({
    'type': 'time_event',
    'event_type': 'quarterly_fee',
    'date': '2024-03-31',
    'timestamp': '2024-03-31T23:59:59'
})
print("Time event (quarterly fee):", result)

# 9. Outgoing transfer from acc2
result = process_transfer_out({
    'type': 'transfer_out',
    'from_account': acc2,
    'to_iban': 'IT60X0542811101000000123456',
    'amount': '500.00',
    'timestamp': '2024-03-02T09:00:00'
})
print("Transfer out from acc2:", result)

# 10. Transfer out remaining balance from acc2 to zero it
acc2_data = get_account(acc2)
if acc2_data['balance'] > 0:
    result = process_transfer_out({
        'type': 'transfer_out',
        'from_account': acc2,
        'to_iban': 'IT60X0542811101000000123456',
        'amount': str(acc2_data['balance']),
        'timestamp': '2024-03-02T09:30:00'
    })
    print("Transfer out remaining balance from acc2:", result)

# 11. Account closure for acc2
result = process_account_closure({
    'type': 'account_closure',
    'account_id': acc2,
    'timestamp': '2024-03-02T10:00:00'
})
print("Account closure for acc2:", result)

print("--- Scripted Test End ---") 