# Implementation Mapping

This document maps the requirements from both `Smartphone Bank Aufgabe.md` and `Technische Beschreibung.md` to their implementations in the codebase.

## 1. Customer Management

### Requirements from Smartphone Bank Aufgabe.md
- Only natural persons (1a)
- Name and address (1a)
- Birth date (1a)
- Customers can open and close accounts (2a)
- Customer data can be modified (2b)

### Implementation
- `src/customer_service.py`:
  - `create_customer()`: Implements customer creation with name, address, birth date
  - `update_customer()`: Implements customer data modification
  - Customer data stored in JSON format in `/data/customers/`

## 2. Account Management

### Requirements from Smartphone Bank Aufgabe.md
- Only current accounts (3a)
- No savings accounts (3b)
- Accounts don't give credit (3c)
- Accounts have IBAN numbers (3d)
- One account per customer (3e)
- CHF 100 annual fee, charged quarterly (3f)
- Credit account created with credit request (3g)

### Implementation
- `src/account_service.py`:
  - `create_account()`: Creates regular account and associated credit account
  - `process_quarterly_fees()`: Implements quarterly fee charging
  - `close_account()`: Implements account closure
  - Account data stored in JSON format in `/data/accounts/`

## 3. Payment Processing

### Requirements from Smartphone Bank Aufgabe.md
- Customers can transfer to IBAN numbers (4a)
- Funds can be received from external systems (4b)
- No cash transactions (4c)
- All transactions come as data (5a-d)

### Implementation
- `src/transaction_service.py`:
  - `process_transfer_out()`: Handles outgoing transfers
  - `process_incoming_payment()`: Handles incoming transfers
  - Transaction data stored in account JSON files

## 4. Credit Management

### Requirements from Smartphone Bank Aufgabe.md
- Credit opened via credit transaction (6a)
- 1-year credit term (6b)
- Credit limits: CHF 1,000-15,000 (6c)
- CHF 250 credit fee (6d)
- 15% annual interest (6f)
- Manual and automatic repayments (6g-h)
- Account blocking for missed payments (6i)
- All credits approved (6j)
- Credit data format (6k)
- Credit management generates repayment transactions (6l)

### Implementation
- `src/credit_service.py`:
  - `request_credit()`: Implements credit creation and fee charging
  - `process_manual_credit_repayment()`: Handles manual repayments
  - `process_monthly_credit_payments()`: Handles automatic repayments
  - `calculate_daily_penalties()`: Implements penalty calculation
  - `write_off_bad_credits()`: Handles non-performing loans

## 5. Bank Accounting System

### Requirements from Smartphone Bank Aufgabe.md
- Customer liability account (7a)
- Central bank asset account (7b)
- Credit asset account (7c)
- Income account for fees and interest (7d)
- Write-off after 6 months of non-payment (7e)

### Implementation
- `src/ledger_service.py`:
  - `load_bank_ledger()`: Initializes bank accounting system
  - `update_bank_ledger()`: Updates financial accounts
  - `validate_bank_system()`: Verifies system integrity
  - Ledger data stored in `/data/bank_ledger/ledger.json`

## 6. Time Simulation

### Requirements from Smartphone Bank Aufgabe.md
- Time transaction for new time (8a)
- Transaction ordering by timestamp (8b)
- Internal time adjustment (8c)

### Implementation
- `src/time_processing_service.py`:
  - `process_time_event()`: Handles time advancement
  - System date stored in `/data/system_date.json`

## 7. Data Storage

### Requirements from Smartphone Bank Aufgabe.md
- JSON file storage (9a)
- Transaction history in account files (9b)
- No signing/hashing required (9c)

### Implementation
- All data stored in JSON format in `/data/` directory
- Transaction history maintained in account JSON files
- No cryptographic operations implemented

## 8. Scale Requirements

### Requirements from Smartphone Bank Aufgabe.md
- ~50 customers (10a)
- 2-year time simulation (10b)
- Transaction files provided (10c)
- ~20 transactions per customer per month (10d)
- Test data for 10 customers (10e)

### Implementation
- `src/generate_test_data.py`: Generates test data
- `test_data/scripted_test.py`: Implements test scenarios
- `test_data/test_transactions.json`: Contains test transactions

## 9. Software Architecture

### Requirements from Smartphone Bank Aufgabe.md
- Function-based (no OOP) (11a)
- JSON data structures (11b)
- No UI/UX required (11c)

### Implementation
- All code implemented as functions in Python modules
- All data structures use JSON format
- No UI/UX components implemented 