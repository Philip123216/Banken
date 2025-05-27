import os
import sys
from src.utils import setup_directories
from src.customer_service import create_customer, get_customer
from src.account_service import create_account, get_account, close_account
from src.transaction_service import process_transaction_file
from src.credit_service import request_credit
from src.ledger_service import update_bank_ledger, validate_bank_system, load_bank_ledger
from src.time_processing_service import get_system_date

def run_simulation(transaction_files_list):
    print(f"run_simulation called with files: {transaction_files_list}")
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
    print("main.py script is running!")
    print("Smart-Phone Haifisch Bank System")
    print("---------------------------------")

    # --- Pfad zum Projekt-Stammverzeichnis bestimmen ---
    print("Determining project root directory...")
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    print(f"Project root: {PROJECT_ROOT}")

    # --- Simulationslauf definieren ---
    print("\n--- Simulation Run ---")

    # Check if a transaction file was provided as a command-line argument
    if len(sys.argv) > 1:
        transaction_file = sys.argv[1]
        transaction_file_absolute = os.path.join(PROJECT_ROOT, transaction_file)
        
        if os.path.exists(transaction_file_absolute):
            print(f"Processing transaction file: {transaction_file_absolute}")
            run_simulation([transaction_file_absolute])
        else:
            print(f"Error: Transaction file not found: {transaction_file_absolute}")
    else:
        # Default to processing example files if no argument provided
        transaction_files_to_process_relative = [
            "example_transactions_create_customers.json",
            "example_transactions_create_accounts.json",
            "example_transactions_month1.json",
            "example_transactions_test_closure.json"
        ]

        # Create absolute paths
        print("Creating absolute paths...")
        transaction_files_to_process_absolute = [
            os.path.join(PROJECT_ROOT, f) for f in transaction_files_to_process_relative
        ]

        print(f"Planning to process: {transaction_files_to_process_absolute}")

        # Check which files exist
        print("\nChecking for existing files...")
        existing_files = []
        for f_abs, f_rel in zip(transaction_files_to_process_absolute, transaction_files_to_process_relative):
            if os.path.exists(f_abs):
                print(f"Found file: {f_abs}")
                existing_files.append(f_abs)
            else:
                print(f"ERROR: Required transaction file not found: {f_rel} (expected at {f_abs})")
                print(f"       Please create the file or check the filename and its location (should be in {PROJECT_ROOT}).")
                existing_files = []  # Clear the list to prevent partial run
                break

        # Run simulation if all files were found
        if existing_files:
            print(f"\nStarting processing with files: {existing_files}")
            run_simulation(existing_files)
        else:
            print("\nSimulation run aborted due to missing transaction files.")

    print("\n--- System Finished ---")