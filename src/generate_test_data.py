# src/generate_test_data.py
# Testdatengenerierungsmodul für das Smart-Phone Haifisch Bank System
# Erstellt Testdaten für Kunden, Konten und Transaktionen über einen Zeitraum von 2 Jahren

import os
import json
import shutil
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
import random
from src.utils import generate_id, save_json, parse_datetime
from src.customer_service import create_customer
from src.account_service import create_account, get_account
from src import config

# Helper to get amortization details (simplified, assumes it's stored or can be derived)
# In a real scenario, this would come from credit_service.calculate_amortization
# For generation, we might need to simulate this or store it temporarily after a credit is disbursed.
active_credits_info = {} # Stores {credit_account_id: {monthly_payment: X, original_amount: Y, balance: Z, missed_payments: 0, start_date: date}}

def cleanup_old_data():
    """
    Löscht alle alten Testdaten vor der Generierung neuer Daten.
    Entfernt alle Dateien aus den Verzeichnissen:
    - CUSTOMERS_DIR
    - ACCOUNTS_DIR
    - TRANSACTIONS_DIR
    """
    print("Cleaning up old test data...")
    
    # Lösche alle Dateien in den Verzeichnissen
    for directory in [config.CUSTOMERS_DIR, config.ACCOUNTS_DIR, config.TRANSACTIONS_DIR]:
        if os.path.exists(directory):
            shutil.rmtree(directory)
        os.makedirs(directory, exist_ok=True) # Ensure directory exists
    
    # Reset active credits info
    active_credits_info.clear()
    print("Cleanup complete.")

def generate_customer_data(num_customers=50):
    """
    Generiert Testdaten für Kunden und deren Konten.
    
    Args:
        num_customers (int): Anzahl der zu erstellenden Kunden (Standard: 50)
        
    Returns:
        tuple: (list of customer_data, dict of customer_id to credit_account_id map)
    """
    print(f"Generating data for {num_customers} customers...")
    
    # Create data directory if it doesn't exist
    os.makedirs(config.DATA_DIR, exist_ok=True)
    os.makedirs(config.CUSTOMERS_DIR, exist_ok=True)
    os.makedirs(config.ACCOUNTS_DIR, exist_ok=True)
    os.makedirs(config.TRANSACTIONS_DIR, exist_ok=True)
    
    # Generate customers
    customers = []
    customer_to_credit_account_map = {} # Added map
    for i in range(num_customers):
        name = f"Test Customer {i+1}"
        address = f"Test Street {i+1}, Test City"
        birth_date = (datetime.now() - timedelta(days=random.randint(365*18, 365*80))).strftime("%Y-%m-%d")
        
        # Create customer with correct parameters
        customer_data = create_customer(name, address, birth_date)
        if not customer_data:
            print(f"Warning: Could not create customer {name}")
            continue
        customers.append(customer_data)
        
        # Create main account for the customer using the ID from customer_data
        account_data, credit_account_data = create_account(customer_data['customer_id'])
        if not account_data or not credit_account_data: # check both
            print(f"Warning: Could not create account or credit account for customer {customer_data['customer_id']}")
            continue
        
        # Populate the map
        customer_to_credit_account_map[customer_data['customer_id']] = credit_account_data['account_id']

        # Store initial credit account info (inactive at this stage)
        active_credits_info[credit_account_data['account_id']] = {
            'monthly_payment': Decimal('0.00'),
            'original_amount': Decimal('0.00'),
            'balance': Decimal('0.00'),
            'missed_payments': 0,
            'start_date': None, # Will be set upon disbursement
            'customer_id': customer_data['customer_id'],
            'main_account_id': account_data['account_id'],
            'status': 'inactive' # initial status
        }
    
    return customers, customer_to_credit_account_map # Return map

def generate_credit_request(customer_id, current_date):
    """
    Generiert eine Kreditanfrage für einen Kunden.
    
    Args:
        customer_id (str): ID des Kunden
        current_date (datetime): Aktuelles Datum
        
    Returns:
        dict: Transaktionsdatensatz für die Kreditanfrage
        
    Hinweis:
        - Generiert zufälligen Kreditbetrag zwischen 1000 und 15000
        - Speichert die Anfrage als Transaktionsdatei
    """
    account_id = f"CH{customer_id[1:]}"
    
    # Random credit amount between 1000 and 15000
    amount = Decimal(str(random.randint(1000, 15000)))
    
    # Create credit request transaction
    credit_tx = {
        "transaction_id": generate_id("CR"),
        "type": "credit_request",
        "main_account": account_id,
        "amount": amount,
        "timestamp": current_date.isoformat(),
        "status": "pending"
    }
    
    # Save transaction
    tx_file = os.path.join(config.TRANSACTIONS_DIR, f"{credit_tx['transaction_id']}.json")
    save_json(tx_file, credit_tx)
    
    return credit_tx

def generate_transactions(customers, start_date, end_date):
    """
    Generiert Transaktionen für alle Kunden über einen Zeitraum.
    
    Args:
        customers (list): Liste der Kundendatensätze
        start_date (datetime): Startdatum
        end_date (datetime): Enddatum
    """
    print(f"Generating transactions from {start_date} to {end_date}...")
    
    total_transactions = 0
    
    # Generate 20 transactions per customer for this month
    for customer in customers:
        customer_id = customer['customer_id']
        account_id = f"CH{customer_id[1:]}"  # Convert C to CH for account ID
        
        # Generate 20 transactions for this customer in this month
        for _ in range(20):
            total_transactions += 1
            # Random transaction type
            tx_type = random.choices(
                ['transfer_in', 'transfer_out', 'credit_request'],
                weights=[0.4, 0.4, 0.2]  # 40% in, 40% out, 20% credit requests
            )[0]
            
            # Random day in the month for this transaction
            random_day = random.randint(1, (end_date - start_date).days + 1)
            transaction_date = start_date + timedelta(days=random_day - 1)
            
            if tx_type == 'credit_request':
                # Generate credit request with random amount between 1000 and 15000
                amount = Decimal(str(random.randint(1000, 15000)))
                credit_tx = {
                    "transaction_id": generate_id("CR"),
                    "type": "credit_disbursement",
                    "credit_account": f"CR{account_id}",
                    "main_account": account_id,
                    "amount": amount,
                    "timestamp": transaction_date.isoformat(),
                    "status": "pending"
                }
                # Save transaction
                tx_file = os.path.join(config.TRANSACTIONS_DIR, f"{credit_tx['transaction_id']}.json")
                save_json(tx_file, credit_tx)
                continue
            
            # Random amount between 100 and 10000
            amount = Decimal(str(random.randint(100, 10000)))
            
            # Create transaction
            tx_data = {
                "transaction_id": generate_id("TR"),
                "type": tx_type,
                "timestamp": transaction_date.isoformat(),
                "status": "pending"
            }
            
            if tx_type == 'transfer_in':
                tx_data.update({
                    "to_account": account_id,
                    "from_iban": f"CH{generate_id('')}",
                    "amount": amount
                })
            else:  # transfer_out
                tx_data.update({
                    "from_account": account_id,
                    "to_iban": f"CH{generate_id('')}",
                    "amount": amount
                })
            
            # Save transaction
            tx_file = os.path.join(config.TRANSACTIONS_DIR, f"{tx_data['transaction_id']}.json")
            save_json(tx_file, tx_data)
    
    # Generate time event for the first day of the month
    time_event = {
        "type": "time_event",
        "date": start_date.isoformat()
    }
    tx_file = os.path.join(config.TRANSACTIONS_DIR, f"TIME_{start_date.strftime('%Y%m%d')}.json")
    save_json(tx_file, time_event)
    
    print(f"Transaction generation complete.")
    print(f"Total transactions generated: {total_transactions}")
    print(f"Expected transactions: {len(customers) * 20}")
    print(f"Expected distribution:")
    print(f"- Transfer in: {total_transactions * 0.4:.0f}")
    print(f"- Transfer out: {total_transactions * 0.4:.0f}")
    print(f"- Credit requests: {total_transactions * 0.2:.0f}")

def validate_test_data():
    """
    Validiert die generierten Testdaten.
    
    Prüft:
        - Anzahl der Kunden
        - Anzahl der Konten (Haupt- und Kreditkonten)
        - Anzahl der Transaktionen
        - Korrekte Verknüpfung von Haupt- und Kreditkonten
        - Gültige Kontostatus
        
    Hinweis:
        - Gibt Warnungen bei fehlenden oder ungültigen Daten aus
        - Prüft Status-Kombinationen von Haupt- und Kreditkonten
    """
    print("\nValidating test data...")
    
    # Check customers
    customer_files = os.listdir(config.CUSTOMERS_DIR)
    print(f"Found {len(customer_files)} customers")
    
    # Check accounts
    account_files = [f for f in os.listdir(config.ACCOUNTS_DIR) if not f.startswith('CR')]
    credit_files = [f for f in os.listdir(config.ACCOUNTS_DIR) if f.startswith('CR')]
    print(f"Found {len(account_files)} regular accounts")
    print(f"Found {len(credit_files)} credit accounts")
    
    # Check transactions
    transaction_files = os.listdir(config.TRANSACTIONS_DIR)
    print(f"Found {len(transaction_files)} transactions")
    
    # Validate account-credit account pairs
    for account_file in account_files:
        account_id = account_file.replace('.json', '')
        credit_account_id = f"CR{account_id}"
        credit_file = f"{credit_account_id}.json"
        
        if credit_file not in credit_files:
            print(f"Warning: No credit account found for {account_id}")
            continue
        
        # Check account status
        account = get_account(account_id)
        credit_account = get_account(credit_account_id)
        
        if not account or not credit_account:
            print(f"Warning: Could not load account data for {account_id}")
            continue
        
        # Validate account status
        if account['status'] not in ['active', 'blocked', 'closed']:
            print(f"Warning: Invalid account status for {account_id}: {account['status']}")
        
        # Validate credit account status
        if credit_account['status'] not in ['inactive', 'active', 'paid_off', 'blocked', 'written_off']:
            print(f"Warning: Invalid credit account status for {credit_account_id}: {credit_account['status']}")
    
    print("Validation complete.")

def generate_test_data():
    """
    Generiert einen Testdatensatz über 2 Jahre mit 50 Kunden, inklusive aller Transaktionstypen.
    """
    print("Starting test data generation (full scope)...")
    
    cleanup_old_data()
    
    start_date = datetime(2025, 1, 1)
    end_date = datetime(2026, 12, 31)
    
    customers, customer_to_credit_map = generate_customer_data(num_customers=50) # Get the map
    
    current_date_for_loop = start_date
    
    # Statistics
    stats = {
        "customer_transactions": 0,
        "time_events": 0,
        "quarterly_fees": 0,
        "credit_disbursements": 0,
        "credit_fees": 0,
        "credit_repayments": 0,
        "credit_penalties": 0,
        "interest_accruals": 0,
        "write_offs": 0
    }

    while current_date_for_loop <= end_date:
        loop_month_start_date = datetime(current_date_for_loop.year, current_date_for_loop.month, 1)
        if current_date_for_loop.month == 12:
            loop_month_end_date = datetime(current_date_for_loop.year, 12, 31)
            next_month_start_date = datetime(current_date_for_loop.year + 1, 1, 1)
        else:
            loop_month_end_date = datetime(current_date_for_loop.year, current_date_for_loop.month + 1, 1) - timedelta(days=1)
            next_month_start_date = datetime(current_date_for_loop.year, current_date_for_loop.month + 1, 1)

        print(f"Processing month: {loop_month_start_date.strftime('%Y-%m')}")

        # 1. Time Event (monthly)
        time_event_tx = {
            "type": "time_event",
            "date": loop_month_start_date.isoformat()
        }
        save_json(os.path.join(config.TRANSACTIONS_DIR, f"TIME_{loop_month_start_date.strftime('%Y%m%d')}.json"), time_event_tx)
        stats["time_events"] += 1

        # 2. Quarterly Fees
        if loop_month_start_date.month in [3, 6, 9, 12]:
            for cust_data in customers:
                customer_id = cust_data['customer_id']
                # Use the map to get the correct credit_account_id
                credit_account_id_for_fees = customer_to_credit_map.get(customer_id)
                if not credit_account_id_for_fees:
                    print(f"Warning: No credit account mapping for customer {customer_id} for quarterly fee. Skipping.")
                    continue
                
                # Now use this credit_account_id_for_fees to access active_credits_info
                # Ensure the key exists before trying to access 'main_account_id'
                if credit_account_id_for_fees not in active_credits_info:
                    print(f"Warning: Credit account {credit_account_id_for_fees} not in active_credits_info for customer {customer_id}. Skipping quarterly fee.")
                    continue

                main_account_id = active_credits_info[credit_account_id_for_fees]['main_account_id']
                qf_tx = {
                    "transaction_id": generate_id("QF"),
                    "type": "quarterly_fee",
                    "account": main_account_id,
                    "amount": str(config.QUARTERLY_FEE),
                    "timestamp": loop_month_start_date.isoformat(), # Fee applied at start of month
                    "status": "pending" 
                }
                save_json(os.path.join(config.TRANSACTIONS_DIR, f"{qf_tx['transaction_id']}.json"), qf_tx)
                stats["quarterly_fees"] += 1
        
        # 3. Customer initiated transactions (transfer_in, transfer_out, credit_request)
        for customer_info in customers:
            customer_id = customer_info['customer_id']
            
            # Use the map to get the correct credit_account_id which is the key for active_credits_info
            # and also the main_account_id directly from active_credits_info if the mapping is successful
            credit_account_id_for_customer_tx = customer_to_credit_map.get(customer_id)
            if not credit_account_id_for_customer_tx:
                print(f"Warning: No credit account mapping for customer {customer_id} for customer transaction. Skipping.")
                continue

            # Ensure the key exists before trying to access active_credits_info
            if credit_account_id_for_customer_tx not in active_credits_info:
                print(f"Warning: Credit account {credit_account_id_for_customer_tx} not in active_credits_info for customer {customer_id}. Skipping customer transaction.")
                continue
                
            main_account_id = active_credits_info[credit_account_id_for_customer_tx]['main_account_id']
            # credit_account_id is now the correct key for active_credits_info
            # (which is credit_account_id_for_customer_tx)

            for _ in range(20): # 20 transactions per customer per month
                stats["customer_transactions"] +=1
                tx_type_roll = random.random()
                transaction_date = loop_month_start_date + timedelta(days=random.randint(0, (loop_month_end_date - loop_month_start_date).days))
                
                if tx_type_roll < 0.4: # Transfer In
                    tr_in_tx = {
                        "transaction_id": generate_id("TR"), "type": "transfer_in",
                        "to_account": main_account_id, "from_iban": f"CH{generate_id('')}",
                        "amount": str(Decimal(random.randint(50, 5000))), "timestamp": transaction_date.isoformat(),
                        "status": "pending"
                    }
                    save_json(os.path.join(config.TRANSACTIONS_DIR, f"{tr_in_tx['transaction_id']}.json"), tr_in_tx)
                elif tx_type_roll < 0.8: # Transfer Out
                    tr_out_tx = {
                        "transaction_id": generate_id("TR"), "type": "transfer_out",
                        "from_account": main_account_id, "to_iban": f"CH{generate_id('')}",
                        "amount": str(Decimal(random.randint(50, 2000))), "timestamp": transaction_date.isoformat(),
                        "status": "pending"
                    }
                    save_json(os.path.join(config.TRANSACTIONS_DIR, f"{tr_out_tx['transaction_id']}.json"), tr_out_tx)
                else: # Credit Request leading to disbursement and fee
                    # Only request if not already active or if previous paid off (simplified for generation)
                    # Use credit_account_id_for_customer_tx as the key
                    if active_credits_info[credit_account_id_for_customer_tx]['status'] in ['inactive', 'paid_off']:
                        requested_amount = Decimal(random.randint(int(config.MIN_CREDIT), int(config.MAX_CREDIT)))
                        # Credit Disbursement
                        cr_dis_tx = {
                            "transaction_id": generate_id("CRD"), "type": "credit_disbursement", # CRD for disbursement
                            "credit_account": credit_account_id_for_customer_tx, "main_account": main_account_id,
                            "amount": str(requested_amount), "timestamp": transaction_date.isoformat(),
                            "status": "pending"
                        }
                        save_json(os.path.join(config.TRANSACTIONS_DIR, f"{cr_dis_tx['transaction_id']}.json"), cr_dis_tx)
                        stats["credit_disbursements"] += 1
                        
                        # Credit Fee
                        cf_tx = {
                            "transaction_id": generate_id("CF"), "type": "credit_fee", # CF for credit fee
                            "from_account": main_account_id, "credit_account": credit_account_id_for_customer_tx, # Link to credit
                            "amount": str(config.CREDIT_FEE), "timestamp": transaction_date.isoformat(), # Same timestamp as disbursement
                            "status": "pending"
                        }
                        save_json(os.path.join(config.TRANSACTIONS_DIR, f"{cf_tx['transaction_id']}.json"), cf_tx)
                        stats["credit_fees"] += 1

                        # Update active_credits_info for repayments simulation
                        # Use credit_account_id_for_customer_tx as the key
                        pv = requested_amount
                        r = config.CREDIT_MONTHLY_RATE
                        n = config.CREDIT_TERM_MONTHS # Should be 12 for 1-year loan
                        if r > 0:
                             monthly_payment = (r * pv) / (1 - (1 + r)**-n)
                             monthly_payment = monthly_payment.quantize(config.CHF_QUANTIZE, ROUND_HALF_UP)
                        else: # Should not happen with positive interest rate
                             monthly_payment = (pv / n).quantize(config.CHF_QUANTIZE, ROUND_HALF_UP)

                        active_credits_info[credit_account_id_for_customer_tx].update({
                            'status': 'active', 
                            'original_amount': requested_amount,
                            'balance': requested_amount, 
                            'monthly_payment': monthly_payment,
                            'missed_payments': 0,
                            'start_date': transaction_date.date(),
                            'payments_made': 0 # Track number of payments made
                        })
                    else: # if credit already active, generate a different customer transaction type e.g. transfer_in
                         tr_in_tx = { # Fallback to transfer_in if credit request not applicable
                            "transaction_id": generate_id("TR"), "type": "transfer_in",
                            "to_account": main_account_id, "from_iban": f"CH{generate_id('')}",
                            "amount": str(Decimal(random.randint(50, 1000))), "timestamp": transaction_date.isoformat(),
                            "status": "pending"
                         }
                         save_json(os.path.join(config.TRANSACTIONS_DIR, f"{tr_in_tx['transaction_id']}.json"), tr_in_tx)


        # 4. System generated credit-related transactions (Repayments, Penalties, Interest Accruals)
        # These are triggered by the TIME_EVENT at the start of the month, conceptually.
        # For generation, we iterate through active credits.
        for cr_acc_id, info in list(active_credits_info.items()): # Use list to allow modification during iteration (for write-offs)
            if info['status'] == 'active' and info['start_date']:
                # Check if it's time for a monthly payment (1 month after start_date, and so on)
                # This logic needs to be robust for checking payment dates.
                # Simplified: assume payment is due if a month has passed since start_date or last payment
                
                # A more robust way to check if a payment is due this month:
                months_since_start = (loop_month_start_date.year - info['start_date'].year) * 12 + (loop_month_start_date.month - info['start_date'].month)
                
                if months_since_start > info.get('payments_made', 0) and months_since_start <= config.CREDIT_TERM_MONTHS:
                    payment_date = loop_month_start_date + timedelta(days=random.randint(0,5)) # Payment early in month
                    
                    # Simulate missed payment (e.g. 10% chance)
                    if random.random() < 0.10 and info['missed_payments'] < 6 : # Max 6 missed payments before potential write-off
                        # Credit Penalty
                        cp_tx = {
                            "transaction_id": generate_id("CP"), "type": "credit_penalty",
                            "credit_account": cr_acc_id, "main_account": info['main_account_id'],
                            "amount": str(info['monthly_payment']), "timestamp": payment_date.isoformat(),
                            "status": "pending_insufficient_funds", # Or "rejected" by system later
                            "reason": "Simulated insufficient funds"
                        }
                        save_json(os.path.join(config.TRANSACTIONS_DIR, f"{cp_tx['transaction_id']}.json"), cp_tx)
                        stats["credit_penalties"] += 1
                        info['missed_payments'] += 1
                        active_credits_info[cr_acc_id]['status'] = 'blocked_due_to_missed_payment' # Simulate account blocking

                        # Interest Accrual (on regular interest, penalty interest is daily and harder to file monthly)
                        # This IA is for the standard interest part of the missed payment.
                        # Real penalty interest is daily, this is a simplification for file generation
                        # For simplicity, we assume the interest part of the missed payment still accrues.
                        # A more detailed simulation would calculate daily penalties.
                        # Let's assume the interest component of the missed payment is what we record here.
                        # This requires knowing the interest component of info['monthly_payment'].
                        # Placeholder: use a fraction of monthly payment or derive from amortization if available.
                        # Simplified: accrue 1/12 of annual interest on current balance if penalty.
                        # This is not fully accurate to the spec's IA example but a start.
                        accrued_interest_this_month = (info['balance'] * config.CREDIT_MONTHLY_RATE).quantize(config.CHF_QUANTIZE, ROUND_HALF_UP)
                        if accrued_interest_this_month > 0:
                            ia_tx = {
                                "transaction_id": generate_id("IA"), "type": "interest_accrual",
                                "credit_account": cr_acc_id,
                                "amount": str(accrued_interest_this_month),
                                "timestamp": payment_date.isoformat(), # Same day as penalty
                                "status": "pending",
                                "note": "Interest accrued on (partially) unpaid balance due to missed payment"
                            }
                            save_json(os.path.join(config.TRANSACTIONS_DIR, f"{ia_tx['transaction_id']}.json"), ia_tx)
                            stats["interest_accruals"] += 1
                            # info['balance'] += accrued_interest_this_month # Balance increases due to accrued interest

                    else: # Successful Repayment
                        if info['status'] != 'blocked_due_to_missed_payment': # only if not blocked
                            # Calculate principal and interest for this payment (simplified)
                            interest_this_payment = (info['balance'] * config.CREDIT_MONTHLY_RATE).quantize(config.CHF_QUANTIZE, ROUND_HALF_UP)
                            principal_this_payment = (info['monthly_payment'] - interest_this_payment).quantize(config.CHF_QUANTIZE, ROUND_HALF_UP)
                            if principal_this_payment < Decimal('0'): principal_this_payment = Decimal('0') # Ensure not negative
                            if principal_this_payment > info['balance']: # Final payment adjustment
                                principal_this_payment = info['balance']
                                actual_payment_amount = principal_this_payment + interest_this_payment
                            else:
                                actual_payment_amount = info['monthly_payment']

                            rp_tx = {
                                "transaction_id": generate_id("RP"), "type": "credit_repayment",
                                "credit_account": cr_acc_id, "main_account": info['main_account_id'],
                                "amount": str(actual_payment_amount),
                                "principal_amount": str(principal_this_payment),
                                "interest_amount": str(interest_this_payment),
                                "timestamp": payment_date.isoformat(),
                                "status": "pending"
                            }
                            save_json(os.path.join(config.TRANSACTIONS_DIR, f"{rp_tx['transaction_id']}.json"), rp_tx)
                            stats["credit_repayments"] += 1
                            info['balance'] -= principal_this_payment
                            info['missed_payments'] = 0 # Reset missed payments on successful one
                            info['payments_made'] = info.get('payments_made',0) + 1
                            if info['balance'] <= Decimal('0.00'):
                                info['status'] = 'paid_off'
                                info['balance'] = Decimal('0.00')
                            else:
                                 info['status'] = 'active' # ensure it's active if payment was made
                        else: # If blocked, we don't process a regular repayment, penalty was already generated.
                            pass # Or maybe try to clear penalties if customer deposited money - too complex for generator.


        # 5. Credit Write-Offs (Check at the end of the month)
        # This is a simplified check. Real write-off depends on continuous non-payment for 6 months.
        for cr_acc_id, info in list(active_credits_info.items()):
            if info['status'] == 'blocked_due_to_missed_payment' and info['missed_payments'] >= 6 :
                 # And enough time has passed since credit start_date or first missed payment.
                 # This requires more robust tracking of first missed payment date.
                 # Simplified: if 6 missed payments are tracked, and it's been at least 6 months in simulation.
                if info.get('start_date'):
                    months_active_or_blocked = (loop_month_start_date.year - info['start_date'].year) * 12 + (loop_month_start_date.month - info['start_date'].month)
                    if months_active_or_blocked >= 6: # Ensure credit has been around for at least 6 months
                        wo_tx = {
                            "transaction_id": generate_id("WO"), "type": "credit_write_off",
                            "credit_account": cr_acc_id,
                            "amount": str(info['balance']), # Write off remaining balance
                            "timestamp": loop_month_end_date.isoformat(), # End of month
                            "status": "pending"
                        }
                        save_json(os.path.join(config.TRANSACTIONS_DIR, f"{wo_tx['transaction_id']}.json"), wo_tx)
                        stats["write_offs"] += 1
                        # Remove from active credits or mark as written_off to prevent further processing
                        active_credits_info[cr_acc_id]['status'] = 'written_off' 
                        active_credits_info[cr_acc_id]['balance'] = Decimal('0.00')


        current_date_for_loop = next_month_start_date

    validate_test_data()
    
    print("\n--- Test Data Generation Summary ---")
    print(f"Generated data for {len(customers)} customers")
    print(f"Time period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    for key, value in stats.items():
        print(f"Total {key.replace('_', ' ')}: {value}")
    total_generated_files = sum(stats.values())
    print(f"Total transaction files generated: {total_generated_files}")
    print("--- End of Summary ---")


if __name__ == "__main__":
    generate_test_data() 