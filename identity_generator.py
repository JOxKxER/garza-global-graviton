"""
Garza Global Graviton Core Module
Automated Vault Infrastructure Script
"""
import hashlib
import json
from datetime import datetime

def validate_dob(dob):
    try:
        datetime.strptime(dob, '%Y-%m-%d')
        return True
    except ValueError:
        return False

def generate_identity_key(full_name, dob, hardware_salt):
    combined_string = f"{full_name}{dob}{hardware_salt}"
    key = hashlib.sha256(combined_string.encode()).hexdigest()
    return key

def create_output_json(status, key, timestamp):
    output = {
        "status": status,
        "key": key,
        "timestamp": timestamp
    }
    return json.dumps(output, indent=4)

def main():
    full_name = input("Enter Full Name: ")
    dob = input("Enter Date of Birth (YYYY-MM-DD): ")
    hardware_salt = input("Enter Unique Hardware Salt: ")

    if not validate_dob(dob):
        print("Invalid Date of Birth format. Please enter in YYYY-MM-DD format.")
        return

    key = generate_identity_key(full_name, dob, hardware_salt)
    timestamp = datetime.now().isoformat()
    output_json = create_output_json("success", key, timestamp)

    print(output_json)

if __name__ == "__main__":
    main()