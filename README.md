CDD-MYSQL-supportThis repository contains a Python script for scanning MySQL databases to find and report potential credit card numbers (Primary Account Numbers, or PANs). The tool is designed to assist developers and security teams in identifying unencrypted sensitive data as part of PCI DSS compliance efforts.It systematically connects to multiple servers, scans specified databases, and validates potential findings using the Luhn algorithm to ensure accuracy.Core FeaturesMulti-Host Scanning: Configure the script to scan across multiple MySQL servers in a single execution.Targeted Database Lists: Specify exactly which databases to scan on each configured host.Luhn Algorithm Validation: Reduces false positives by mathematically validating any number sequences that look like a credit card number.Formatted PAN Detection: Finds credit card numbers even if they contain spaces or dashes (e.g., 5555-5555-5555-5555).Secure Reporting: All discovered PANs are masked in the final report to protect sensitive data (e.g., 555555******5555).Excel Export: Generates a clear and organized .xlsx file detailing the exact location (Host, DB, Table, Column, Row) of each potential PAN.PrerequisitesPython 3.6+The following Python libraries: mysql-connector-python, pandas, and openpyxl.InstallationYou can install the required libraries using pip:pip install mysql-connector-python pandas openpyxl
How to ConfigureAll settings are managed within the SqlSupport_V2.py file.Set Up Host ConnectionsUpdate the HOST_CONFIGS list with the details for each MySQL server you need to scan. Create a new dictionary for each server.Important: Replace placeholder values with your actual credentials and database names.# --- HOST & DATABASE CONFIGURATIONS ---
HOST_CONFIGS = [
    {
        'name': 'Localhost Server',
        'user': 'root',
        'password': 'Your_Password_Here',  # <-- REPLACE
        'host': '127.0.0.1',
        'databases': [
            'master',
            'customer_data',
            'archived_sales'
        ]
    },
    {
        'name': 'Staging Server',
        'user': 'scanner_user',
        'password': 'Staging_Server_Password', # <-- REPLACE
        'host': '192.168.1.50',
        'databases': [
            'staging_db'
        ]
    },
]
Define Output Filename (Optional)You can change the name of the generated Excel report by editing the OUTPUT_FILENAME variable.# --- OUTPUT FILE ---
OUTPUT_FILENAME = 'pci_scan_results_final.xlsx'
How to Run the ScriptOpen a terminal or command prompt, navigate to the script's directory, and run the following command:python SqlSupport_V2.py
The script will display its progress in the terminal, showing which hosts and databases are being processed.Understanding the ReportAfter the scan is complete, an Excel file will be created in the same directory. The report will have the following columns:Result #Masked PANLocation1499273******3456Host: 127.0.0.1, DB: customer_data, Table: users, Column: notes, Row: 422510001******1010Host: 192.168.1.50, DB: staging_db, Table: transactions, Column: payment_details, Row: 1337DisclaimerThis tool is intended to aid in security auditing and should be used responsibly. It is not a substitute for a complete PCI DSS audit. The results should be handled as sensitive information and reviewed carefully. The authors are not responsible for any misuse of this script.
