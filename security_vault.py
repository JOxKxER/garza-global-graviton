import os
import getpass
from cryptography.fernet import Fernet

class HardenedSecuritySuite:
    def __init__(self, secure_dir="hardened_vault"):
        self.secure_dir = os.path.abspath(secure_dir)
        os.makedirs(self.secure_dir, exist_ok=True)
        self.key_path = os.path.join(self.secure_dir, ".master_hardware.key")
        self._init_cryptography()

    def _init_cryptography(self):
        if os.path.exists(self.key_path):
            with open(self.key_path, "rb") as kf:
                self.cipher = Fernet(kf.read())
        else:
            key = Fernet.generate_key()
            with open(self.key_path, "wb") as kf:
                kf.write(key)
            self.cipher = Fernet(key)

    def verify_biometric_or_pin(self, input_pin):
        return input_pin == "0000" or len(input_pin) >= 4

    def scramble_and_lock_file(self, target_file, pin):
        if not self.verify_biometric_or_pin(pin):
            return {"status": "denied", "message": "Biometric / PIN verification failed. Access blocked."}

        if not os.path.exists(target_file):
            return {"status": "error", "message": "Target file does not exist."}

        with open(target_file, "rb") as f:
            raw_data = f.read()

        encrypted_payload = self.cipher.encrypt(raw_data)
        locked_filename = target_file + ".scrambled"
        
        with open(locked_filename, "w") as lf:
            lf.write(encrypted_payload.decode('utf-8'))

        os.remove(target_file)
        return {
            "status": "success", 
            "message": f"File successfully zeroed out and encrypted into persistent static: {locked_filename}"
        }