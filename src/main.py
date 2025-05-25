# Main execution file for the banking system
import os
import sys
from utils import setup_directories
from ledger_service import load_bank_ledger, validate_bank_system
from time_processing_service import get_system_date
from transaction_service import process_transaction_file

def run_simulation(transaction_files_list):
    """Runs the simulation by processing a list of transaction files in order."""
    setup_directories()
    load_bank_ledger()  # Initialize ledger if needed
    get_system_date()  # Initialize system date if needed
    
    for file_path in transaction_files_list:
        if os.path.exists(file_path):
            process_transaction_file(file_path)
        else:
            print(f"Warning: Transaction file not found: {file_path}")
    
    # Final validation after all transactions
    validate_bank_system()

if __name__ == "__main__":
    print("Smart-Phone Haifisch Bank System")
    print("---------------------------------")
    
    # Define the sequence of transaction files TO PROCESS for this run
    print("\n--- Simulation Run ---")
    
    # STEP 1: Create Customers
    transaction_files_to_process = [
        "../example_transactions_create_customers.json",  # Rerun customer creation (harmless)
        "../example_transactions_create_accounts.json"  # Add this file after editing it
    ]
    
    print(f"Planning to process: {transaction_files_to_process}")
    
    # Check which files actually exist
    existing_files = []
    for f in transaction_files_to_process:
        if os.path.exists(f):
            existing_files.append(f)
        else:
            print(f"ERROR: Required transaction file not found: {f}")
            print(f"       Please create the file or check the filename.")
            # Stop processing if a required file is missing
            existing_files = [] # Clear the list to prevent partial run
            break
    
    # Run the simulation if all files were found
    if existing_files:
        print(f"Starting processing with files: {existing_files}")
        # Run the simulation using the defined file list
        run_simulation(existing_files)
    else:
        print("Simulation aborted due to missing files.")