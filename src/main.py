import os
import sys
from .utils import setup_directories
from .ledger_service import load_bank_ledger, validate_bank_system
from .time_processing_service import get_system_date
from .transaction_service import process_transaction_file

# Die run_simulation Funktion bleibt unverändert
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

    # --- Pfad zum Projekt-Stammverzeichnis bestimmen ---
    # __file__ ist der Pfad zur aktuellen Datei (main.py)
    # os.path.abspath(__file__) macht ihn absolut
    # os.path.dirname(...) gibt das Verzeichnis dieser Datei (src)
    # Ein weiteres os.path.dirname(...) geht eine Ebene höher (Bank_Modularisiert)
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # --- Simulationslauf definieren ---
    print("\n--- Simulation Run ---")

    # Definiere die Sequenz der zu verarbeitenden Transaktionsdateien
    # Hier kannst du die Dateien für verschiedene Testphasen anpassen
    transaction_files_to_process_relative = [
        "example_transactions_create_customers.json",
        "example_transactions_create_accounts.json",
        "example_transactions_month1.json" # Füge diese oder andere Dateien hinzu/entferne sie für Tests
    ]

    # Erstelle absolute Pfade zu den Transaktionsdateien
    transaction_files_to_process_absolute = [
        os.path.join(PROJECT_ROOT, f) for f in transaction_files_to_process_relative
    ]

    print(f"Planning to process: {transaction_files_to_process_absolute}")

    # Überprüfe, welche Dateien tatsächlich existieren
    existing_files = []
    for f_abs, f_rel in zip(transaction_files_to_process_absolute, transaction_files_to_process_relative):
        if os.path.exists(f_abs):
            existing_files.append(f_abs)
        else:
            print(f"ERROR: Required transaction file not found: {f_rel} (expected at {f_abs})")
            print(f"       Please create the file or check the filename and its location (should be in {PROJECT_ROOT}).")
            existing_files = []  # Leere die Liste, um einen teilweisen Lauf zu verhindern
            break

    # Führe die Simulation aus, wenn alle Dateien gefunden wurden
    if existing_files:
        print(f"Starting processing with files: {existing_files}")
        run_simulation(existing_files) # Verwende die Liste mit den absoluten Pfaden
    else:
        print("\nSimulation run aborted due to missing transaction files.")
        # Optional: Führe die Validierung trotzdem aus, um den aktuellen Zustand zu sehen
        # print("\nRunning validation on current state...")
        # setup_directories() # Stelle sicher, dass Verzeichnisse für die Validierung existieren
        # validate_bank_system()

    print("\n--- System Finished ---")