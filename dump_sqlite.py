# save as dump_sqlite.py
import os
import json
import sqlite3
import django
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'business_permit_system.settings')  # Change to your project's settings module
django.setup()

from django.conf import settings

# Get the SQLite database path from Django settings
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = os.path.join(BASE_DIR, 'db.sqlite3')  # Adjust if your path is different


# Function to get data from a table
def get_table_data(table_name, app_name, model_name):
    try:
        # Create a new connection for each table
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get all rows
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()

        result = []
        for row in rows:
            # Convert row to dictionary
            row_dict = {key: row[key] for key in row.keys()}
            pk = row_dict.get('id')

            # For UUID primary keys, ensure they're properly formatted
            if app_name == 'documents' and model_name == 'document':
                # Ensure UUID is properly formatted for document model
                pk = str(pk)

            # Create entry in Django dumpdata format
            entry = {
                'model': f"{app_name}.{model_name}",
                'pk': pk,
                'fields': {k: v for k, v in row_dict.items() if k != 'id'}
            }
            result.append(entry)

        # Close connection when done
        conn.close()
        return result
    except Exception as e:
        print(f"Error processing table {table_name}: {e}")
        if 'conn' in locals():
            conn.close()
        return []


# Main execution
print("Starting data export...")

# Define your app models mapping
model_mapping = [
    {'table': 'applications_businessapplication', 'app': 'applications', 'model': 'businessapplication'},
    {'table': 'documents_document', 'app': 'documents', 'model': 'document'},
    {'table': 'documents_documentverificationresult', 'app': 'documents', 'model': 'documentverificationresult'},
    {'table': 'documents_documentactivity', 'app': 'documents', 'model': 'documentactivity'},
    # Add other models as needed
]

# Export data
all_data = []
for model in model_mapping:
    print(f"Exporting data from {model['table']}...")
    table_data = get_table_data(model['table'], model['app'], model['model'])
    all_data.extend(table_data)
    print(f"Exported {len(table_data)} records from {model['table']}")

# Write to file
with open('custom_data_dump.json', 'w') as f:
    json.dump(all_data, f, indent=2)

print(f"Data export completed. Total records: {len(all_data)}")