# Banking System Architecture Guide

This document provides instructions for building a banking system similar to the Haifisch Bank System. It details the system's components, architecture, and data formats.

## System Overview

The banking system is designed around the following core functionalities:

1. **Customer Management**: Create and manage customer profiles
2. **Account Management**: Handle deposit accounts and credit accounts
3. **Transaction Processing**: Process various financial transactions
4. **Credit Management**: Issue loans and manage repayments
5. **Time Simulation**: Process time-dependent events
6. **Ledger Accounting**: Maintain financial integrity through double-entry bookkeeping

## System Architecture

The system is structured as a modular application with the following components:

### 1. Data Storage Layer

The system uses file-based JSON storage for simplicity:
- `/data/customers/`: Customer profiles
- `/data/accounts/`: Regular and credit accounts
- `/data/transactions/`: Transaction records
- `/data/bank_ledger/`: Bank's financial ledger
- `/data/system_date.json`: Current system date for time simulation

### 2. Core Functions

#### Customer Management
- `create_customer`: Register new customers
- `update_customer`: Modify customer details
- `get_customer`: Retrieve customer information

#### Account Management
- `create_account`: Create new deposit accounts with associated credit accounts
- `get_account`: Retrieve account information
- `get_customer_account`: Find a customer's main account

#### Transaction Processing
- `process_transfer`: Handle outgoing transfers
- `process_incoming_payment`: Handle incoming transfers
- `process_transaction_file`: Process batches of transactions

#### Credit Management
- `request_credit`: Process loan requests
- `process_credit_repayment`: Handle loan repayments

#### Time Simulation
- `process_time_event`: Advance system time and trigger periodic operations
- `process_monthly_credit_payments`: Process scheduled credit repayments
- `process_quarterly_fees`: Charge account maintenance fees
- `calculate_daily_penalties`: Apply penalties to blocked accounts
- `write_off_bad_credits`: Handle non-performing loans

#### Ledger Management
- `load_bank_ledger`: Initialize the bank's accounting system
- `update_bank_ledger`: Update financial accounts
- `get_bank_ledger`: Retrieve current ledger state
- `validate_bank_system`: Verify system integrity

## Data Formats

### Customer Data Format

```json
{
  "customer_id": "C20250402160312",
  "name": "John Doe",
  "address": "123 Main Street, Anytown",
  "birth_date": "1985-05-15",
  "created_at": "2025-04-02T16:03:12",
  "status": "active"
}
```

### Account Data Format

#### Regular Account
```json
{
  "account_id": "CH20250402160312",
  "customer_id": "C20250402160312",
  "balance": "5000.00",
  "status": "active",
  "created_at": "2025-04-02T16:03:12",
  "last_fee_date": "2025-04-02T16:03:12",
  "transactions": [
    {...transaction objects...}
  ]
}
```

#### Credit Account
```json
{
  "account_id": "CRCH20250402160312",
  "customer_id": "C20250402160312",
  "balance": "10000.00",
  "status": "active",
  "created_at": "2025-04-02T16:03:12",
  "credit_start_date": "2025-04-02T16:03:12",
  "credit_end_date": "2026-04-02T16:03:12",
  "monthly_payment": "889.32",
  "monthly_rate": "0.0125",
  "remaining_payments": 12,
  "amortization_schedule": [
    {
      "payment_number": 1,
      "payment_amount": "889.32",
      "principal": "764.32",
      "interest": "125.00",
      "remaining_balance": "9235.68"
    },
    {...more payments...}
  ],
  "transactions": [
    {...transaction objects...}
  ]
}
```

### Transaction Data Formats

#### Transfer Out
```json
{
  "transaction_id": "TR20250402160415",
  "type": "transfer_out",
  "from_account": "CH20250402160312",
  "to_iban": "CH9999999999999",
  "amount": "1000.00",
  "timestamp": "2025-04-02T16:04:15",
  "status": "completed",
  "balance_before": "5000.00",
  "balance_after": "4000.00"
}
```

#### Transfer In
```json
{
  "transaction_id": "TR20250402160520",
  "type": "transfer_in",
  "to_account": "CH20250402160312",
  "from_iban": "CH8888888888888",
  "amount": "2000.00",
  "timestamp": "2025-04-02T16:05:20",
  "status": "completed",
  "balance_before": "4000.00",
  "balance_after": "6000.00"
}
```

#### Credit Request
```json
{
  "transaction_id": "CR20250402160630",
  "type": "credit_disbursement",
  "credit_account": "CRCH20250402160312",
  "main_account": "CH20250402160312",
  "amount": "10000.00",
  "timestamp": "2025-04-02T16:06:30",
  "status": "completed"
}
```

#### Credit Fee
```json
{
  "transaction_id": "FE20250402160631",
  "type": "credit_fee",
  "from_account": "CH20250402160312",
  "amount": "250.00",
  "timestamp": "2025-04-02T16:06:31",
  "status": "completed",
  "balance_before": "6000.00",
  "balance_after": "5750.00"
}
```

#### Credit Repayment
```json
{
  "transaction_id": "RP20250502160312",
  "type": "credit_repayment",
  "credit_account": "CRCH20250402160312",
  "main_account": "CH20250402160312",
  "amount": "889.32",
  "principal_amount": "764.32",
  "interest_amount": "125.00",
  "timestamp": "2025-05-02T16:03:12",
  "status": "completed",
  "credit_balance_before": "10000.00",
  "credit_balance_after": "9235.68",
  "account_balance_before": "5750.00",
  "account_balance_after": "4860.68"
}
```

#### Rejected Credit Repayment
```json
{
  "transaction_id": "PN20250502160312",
  "type": "credit_penalty",
  "credit_account": "CRCH20250402160312",
  "main_account": "CH20250402160312",
  "amount": "889.32",
  "timestamp": "2025-05-02T16:03:12",
  "status": "rejected",
  "reason": "Insufficient funds - account blocked"
}
```

#### Interest Accrual (For Missed Payments)
```json
{
  "transaction_id": "IA20250502160312",
  "type": "interest_accrual",
  "credit_account": "CRCH20250402160312",
  "amount": "125.00",
  "timestamp": "2025-05-02T16:03:12",
  "status": "completed",
  "credit_balance_before": "10000.00",
  "credit_balance_after": "10125.00",
  "note": "Interest accrued on unpaid balance"
}
```

#### Quarterly Fee
```json
{
  "transaction_id": "QF20250702160312",
  "type": "quarterly_fee",
  "account": "CH20250402160312",
  "amount": "25.00",
  "timestamp": "2025-07-02T16:03:12",
  "status": "completed",
  "balance_before": "4860.68",
  "balance_after": "4835.68"
}
```

#### Time Event
```json
{
  "type": "time_event",
  "date": "2025-05-02T00:00:00"
}
```

### Bank Ledger Format

```json
{
  "customer_liabilities": {"balance": "468323.07"},
  "central_bank_assets": {"balance": "439540.20"},
  "credit_assets": {"balance": "34335.91"},
  "income": {"balance": "5503.04"}
}
```

## Implementation Steps

1. **Set up the directory structure**:
   ```
   /data
     /accounts
     /customers
     /transactions
     /bank_ledger
   ```

2. **Implement helper functions** for JSON handling:
   - `save_json`: Write data to JSON files
   - `load_json`: Read data from JSON files
   - `DecimalEncoder`: Custom JSON encoder for Decimal values

3. **Implement customer management functions**:
   - Customer creation with unique IDs
   - Customer profile updates and retrieval

4. **Implement account management functions**:
   - Account creation linked to customers
   - Associated credit account creation
   - Account retrieval methods

5. **Implement transaction processing**:
   - Transfer handling with appropriate checks
   - Balance updates and transaction recording

6. **Implement credit management**:
   - Loan disbursement with amortization calculation
   - Repayment processing with principal/interest breakdown
   - Special handling for missed payments

7. **Implement time simulation**:
   - Date advancement with periodic operations
   - Monthly credit payment processing
   - Quarterly fee charging
   - Daily penalty calculation
   - Bad credit write-offs

8. **Implement ledger management**:
   - Double-entry bookkeeping
   - Transaction impact on financial accounts
   - System validation and consistency checks

9. **Implement transaction file processing**:
   - Batch transaction handling
   - Error management and reporting

## Financial Principles

### Double-Entry Bookkeeping

The system follows double-entry bookkeeping principles:

1. **Customer Deposits**:
   - Increase customer_liabilities
   - Increase central_bank_assets

2. **Customer Withdrawals**:
   - Decrease customer_liabilities
   - Decrease central_bank_assets

3. **Credit Disbursement**:
   - Increase customer_liabilities (deposit to customer)
   - Increase credit_assets (loan receivable)
   - Increase income by fee amount
   - Decrease customer_liabilities by fee amount

4. **Credit Repayment**:
   - Decrease customer_liabilities (payment from customer)
   - Decrease credit_assets by principal amount
   - Increase income by interest amount

5. **Missed Credit Payment**:
   - Block customer account
   - Increase credit_assets by accrued interest
   - No immediate impact on income (recognized only when received)

6. **Credit Write-Off**:
   - Decrease credit_assets (removing bad loan)
   - Decrease income (recognizing loss)

### Amortization Calculation

The system uses the standard amortization formula:
```
PMT = P × r × (1 + r)^n / ((1 + r)^n - 1)
```

Where:
- PMT = monthly payment
- P = principal (loan amount)
- r = monthly interest rate (annual rate / 12)
- n = number of payments (12 for a 1-year loan)

For each payment:
1. Interest component = Outstanding balance × Monthly interest rate
2. Principal component = Monthly payment - Interest component
3. New outstanding balance = Previous balance - Principal component

## Testing the System

1. **Create test customers and accounts**
2. **Simulate various transactions**:
   - Regular transfers
   - Credit requests
   - Credit repayments
   - Insufficient funds scenarios
3. **Test time simulation**:
   - Process monthly payments
   - Apply quarterly fees
   - Simulate missed payments
   - Test credit write-offs
4. **Validate system integrity**:
   - Check customer account totals against ledger
   - Verify credit asset calculations
   - Ensure balanced accounting entries 

python -m src.generate_test_data

from src.main import process_transactions
from datetime import datetime, timedelta
from src import config

# Startdatum setzen
start_date = datetime.now()
end_date = start_date + timedelta(days=365*2)  # 2 Jahre simulieren

# Transaktionen verarbeiten
process_transactions(start_date, end_date) 