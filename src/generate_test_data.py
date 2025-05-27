import os
import json
from datetime import datetime, timedelta
from decimal import Decimal
import random
from src.utils import generate_id, save_json
from src.customer_service import create_customer
from src.account_service import create_account, get_account
from src.credit_service import request_credit
from src import config

def generate_customer_data(num_customers=50):
    """Generates customer data for testing."""
    print(f"Generating data for {num_customers} customers...")
    
    # Create data directory if it doesn't exist
    os.makedirs(config.DATA_DIR, exist_ok=True)
    os.makedirs(config.CUSTOMERS_DIR, exist_ok=True)
    os.makedirs(config.ACCOUNTS_DIR, exist_ok=True)
    os.makedirs(config.TRANSACTIONS_DIR, exist_ok=True)
    
    # Generate customers
    customers = []
    for i in range(num_customers):
        customer_id = generate_id("C")
        name = f"Test Customer {i+1}"
        address = f"Test Street {i+1}, Test City"
        birth_date = (datetime.now() - timedelta(days=random.randint(365*18, 365*80))).strftime("%Y-%m-%d")
        
        customer_data = {
            "customer_id": customer_id,
            "name": name,
            "address": address,
            "birth_date": birth_date,
            "created_at": datetime.now().isoformat(),
            "status": "active"
        }
        
        # Create customer
        create_customer(customer_data)
        customers.append(customer_data)
        
        # Create account
        create_account(customer_id)
    
    return customers

def generate_credit_request(customer_id, current_date):
    """Generates a credit request for a customer."""
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
    """Generates transactions for all customers between start_date and end_date."""
    print(f"Generating transactions from {start_date} to {end_date}...")
    
    current_date = start_date
    while current_date <= end_date:
        # Generate 20 transactions per customer per month
        for customer in customers:
            customer_id = customer['customer_id']
            account_id = f"CH{customer_id[1:]}"  # Convert C to CH for account ID
            
            # Generate 20 transactions for this customer in this month
            for _ in range(20):
                # Random transaction type (including credit requests and account closures)
                tx_type = random.choices(
                    ['transfer_in', 'transfer_out', 'credit_request', 'account_closure'],
                    weights=[0.35, 0.35, 0.2, 0.1]  # 35% in, 35% out, 20% credit requests, 10% closures
                )[0]
                
                if tx_type == 'credit_request':
                    # Generate credit request
                    credit_tx = generate_credit_request(customer_id, current_date)
                    continue
                elif tx_type == 'account_closure':
                    # Generate account closure request
                    closure_tx = {
                        "transaction_id": generate_id("CLS"),
                        "type": "account_closure",
                        "account_id": account_id,
                        "timestamp": current_date.isoformat()
                    }
                    # Save transaction
                    tx_file = os.path.join(config.TRANSACTIONS_DIR, f"{closure_tx['transaction_id']}.json")
                    save_json(tx_file, closure_tx)
                    continue
                
                # Random amount between 100 and 10000
                amount = Decimal(str(random.randint(100, 10000)))
                
                # Create transaction
                tx_data = {
                    "transaction_id": generate_id("TR"),
                    "type": tx_type,
                    "timestamp": current_date.isoformat(),
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
        
        # Move to next day
        current_date += timedelta(days=1)
    
    print("Transaction generation complete.")

def validate_test_data():
    """Validates the generated test data."""
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
    """Main function to generate all test data."""
    # Generate customers and accounts
    customers = generate_customer_data()
    
    # Generate transactions for 2 years
    start_date = datetime.now()
    end_date = start_date + timedelta(days=365*2)
    generate_transactions(customers, start_date, end_date)
    
    # Validate generated data
    validate_test_data()
    
    print("Test data generation complete.")

if __name__ == "__main__":
    generate_test_data() 