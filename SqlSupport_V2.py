# Python Script to Scan a List of MySQL Databases Grouped by Host
#
# v12: This is the final, stable version. It includes fixes for:
# - Robustly handling all tables without cursor state issues.
# - Correctly decoding all text and byte data from the database.
# - Finding formatted PANs (with spaces/dashes) by sanitizing the text.
# - An improved regular expression for maximum compatibility.
#
# This script connects to specified MySQL hosts, iterates through a list of databases,
# and scans text-based columns for credit card numbers.

import mysql.connector
import pandas as pd
import re
import sys

# --- HOST & DATABASE CONFIGURATIONS ---
# IMPORTANT: For each host, provide a list of databases you want to scan.
HOST_CONFIGS = [
    {
        'name': 'Localhost Server',
        'user': 'root',
        'password': 'pass',      # <-- REPLACE WITH YOUR MYSQL PASSWORD
        'host': '127.0.0.1',
        'databases': [           # <-- LIST DATABASES TO SCAN ON THIS HOST
            'master',
            'customer_data',
        ]
    },    
    # {
    #     'name': 'Staging Server',
    #     'user': 'scanner_user',
    #     'password': 'Password123!', # <-- REPLACE
    #     'host': '192.168.1.50',
    #     'databases': []
    # },
]

# --- OUTPUT FILE ---
OUTPUT_FILENAME = 'pci_scan_results_final.xlsx'

def is_luhn_valid(card_number):
    """Validates a credit card number using the Luhn algorithm."""
    try:
        num_digits = len(card_number)
        n_sum = 0
        is_second = False
        for i in range(num_digits - 1, -1, -1):
            d = int(card_number[i])
            if is_second:
                d = d * 2
            n_sum += d // 10
            n_sum += d % 10
            is_second = not is_second
        return (n_sum % 10 == 0)
    except (ValueError, TypeError):
        return False

def mask_pan(pan):
    """Masks a PAN, showing only the first 6 and last 4 digits."""
    if not isinstance(pan, str) or len(pan) < 10:
        return "Invalid PAN"
    return f"{pan[:6]}{'*' * (len(pan) - 10)}{pan[-4:]}"

def scan_hosts_and_databases():
    """Main function to connect to hosts, scan specified DBs, and generate a report."""
    all_findings = []
    print("Starting PCI DSS database scan with hosts and grouped databases...")

    # Regex to find any sequence of 13 to 19 digits.
    pan_regex = re.compile(r'\d{13,19}')

    # Iterate over each host configuration
    for host_config in HOST_CONFIGS:
        host_identifier = host_config.get('name', host_config['host'])
        print(f"\n{'='*50}\n[INFO] Processing Host: {host_identifier}\n{'='*50}")

        if not host_config.get('databases'):
            print(f"[INFO] No databases listed for host '{host_identifier}'. Skipping.")
            continue

        for db_name in host_config['databases']:
            conn = None
            try:
                print(f"\n--- Attempting to connect to database: {db_name} ---")
                conn = mysql.connector.connect(
                    user=host_config['user'],
                    password=host_config['password'],
                    host=host_config['host'],
                    database=db_name
                )
                print(f"    [SUCCESS] Connected to database '{db_name}'.")

                # First, get a list of all tables in the database
                tables_cursor = conn.cursor()
                tables_cursor.execute("SHOW TABLES")
                tables = [table[0] for table in tables_cursor.fetchall()]
                tables_cursor.close()
                print(f"    -> Found tables: {tables}")

                # Now, loop through the list of tables, creating a new cursor for each.
                for table_name in tables:
                    table_cursor = None
                    try:
                        print(f"       -> Scanning table: {table_name}...")
                        
                        # Use a new, buffered cursor for each table to ensure a clean state
                        table_cursor = conn.cursor(buffered=True)
                        
                        table_cursor.execute(f"DESCRIBE `{table_name}`")
                        columns_to_scan = [col[0] for col in table_cursor.fetchall() if any(t in (col[1].decode() if isinstance(col[1], bytes) else str(col[1])).upper() for t in ['CHAR', 'VARCHAR', 'TEXT', 'TINYTEXT', 'MEDIUMTEXT', 'LONGTEXT', 'JSON'])]

                        if not columns_to_scan:
                            print(f"          -> No scannable columns in {table_name}. Skipping.")
                            continue
                        
                        table_cursor.execute(f"SELECT * FROM `{table_name}`")
                        rows = table_cursor.fetchall()
                        column_names = [i[0] for i in table_cursor.description]

                        for row_index, row in enumerate(rows):
                            for col_name in columns_to_scan:
                                col_index = column_names.index(col_name)
                                
                                cell_value_raw = row[col_index]
                                cell_value = ""
                                if cell_value_raw is not None:
                                    if isinstance(cell_value_raw, (bytes, bytearray)):
                                        cell_value = cell_value_raw.decode('utf-8', errors='ignore')
                                    else:
                                        cell_value = str(cell_value_raw)

                                # Sanitize the value by removing spaces and dashes
                                sanitized_value = cell_value.replace(' ', '').replace('-', '')

                                for pan in pan_regex.findall(sanitized_value):
                                    if is_luhn_valid(pan):
                                        location = (f"Host: {host_config['host']}, DB: {db_name}, "
                                                    f"Table: {table_name}, Column: {col_name}, Row: {row_index + 1}")
                                        all_findings.append({'PAN': pan, 'Location': location})
                                        print(f"                 [!] LUHN-VALID PAN FOUND in {location}")
                    except mysql.connector.Error as table_err:
                        print(f"          [ERROR] An error occurred while scanning table {table_name}: {table_err}", file=sys.stderr)
                    finally:
                        if table_cursor:
                            table_cursor.close()

            except mysql.connector.Error as err:
                print(f"    [ERROR] Could not process database '{db_name}': {err}", file=sys.stderr)
                continue
            
            finally:
                if conn and conn.is_connected():
                    conn.close()
                    print(f"    -> Connection to {db_name} closed.")

    if not all_findings:
        print("\n\nScan complete. No potential PANs found across all specified databases!")
        return

    print(f"\n{'='*50}\n[SUMMARY] Scan complete. Found a total of {len(all_findings)} potential PANs.\n{'='*50}")
    
    df = pd.DataFrame(all_findings)
    df['Result #'] = range(1, len(df) + 1)
    df['Masked PAN'] = df['PAN'].apply(mask_pan)
    report_df = df[['Result #', 'Masked PAN', 'Location']]
    
    try:
        report_df.to_excel(OUTPUT_FILENAME, index=False)
        print(f"[SUCCESS] Successfully created report: {OUTPUT_FILENAME}")
    except Exception as e:
        print(f"[ERROR] Could not write to Excel file: {e}", file=sys.stderr)


if __name__ == "__main__":
    scan_hosts_and_databases()
