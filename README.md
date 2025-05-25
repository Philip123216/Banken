# Smart-Phone Haifisch Bank - Modulares System

Dies ist ein modulares Banksystem, das im Rahmen des Kurses CDS305 entwickelt wurde. Es simuliert grundlegende Bankfunktionalitäten wie Kunden- und Kontoverwaltung, Transaktionsverarbeitung, Kreditmanagement und Ledger-Buchhaltung.

## Struktur

Das Projekt ist wie folgt strukturiert:
- `data/`: Enthält JSON-Dateien für Kundendaten, Konten, Ledger und Systemdatum.
- `src/`: Enthält den Python-Quellcode, unterteilt in Service-Module.
    - `config.py`: Globale Konfigurationen.
    - `utils.py`: Allgemeine Hilfsfunktionen.
    - `*_service.py`: Spezifische Funktionalitätsmodule.
    - `main.py`: Haupteinstiegspunkt für die Simulation.
- `example_transactions_*.json`: Beispieldateien zur Demonstration der Transaktionsverarbeitung.

## Setup

1. Klonen Sie das Repository:
   ```bash
   git clone https://github.com/Philip123216/Banken.git
   cd Banken 
