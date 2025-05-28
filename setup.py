import os
import json
from datetime import datetime

def create_directory_structure():
    """Create the necessary directory structure for the banking system."""
    directories = [
        'data',
        'data/customers',
        'data/accounts',
        'data/bank_ledger'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"Created directory: {directory}")

def create_initial_files():
    """Create initial JSON files with default values."""
    # Create system_date.json
    system_date = {
        "current_date": datetime.now().strftime("%Y-%m-%d")
    }
    with open('data/system_date.json', 'w') as f:
        json.dump(system_date, f, indent=4)
    print("Created system_date.json")

    # Create empty bank_ledger.json
    bank_ledger = {
        "transactions": []
    }
    with open('data/bank_ledger/bank_ledger.json', 'w') as f:
        json.dump(bank_ledger, f, indent=4)
    print("Created bank_ledger.json")

def main():
    print("Setting up banking system directory structure...")
    create_directory_structure()
    create_initial_files()
    print("\nSetup complete! The following structure has been created:")
    print("data/")
    print("├── accounts/")
    print("├── customers/")
    print("├── bank_ledger/")
    print("│   └── bank_ledger.json")
    print("└── system_date.json")

if __name__ == "__main__":
    main() 