"""Very small stub for cryptography.fernet.Fernet.
It simply encodes/decodes strings using base64 for demonstration.
No real encryption is performed, but the API matches the real class.
"""
import base64

class Fernet:
    def __init__(self, key: bytes):
        self.key = key
    @staticmethod
    def generate_key() -> bytes:
        # Return a dummy base64 key
        return base64.urlsafe_b64encode(b'dummy_key_1234567890')
    def encrypt(self, data: bytes) -> bytes:
        # Simple reversible operation: base64 encode data with key prefix
        return base64.urlsafe_b64encode(self.key + b':' + data)
    def decrypt(self, token: bytes) -> bytes:
        # Reverse the encrypt operation
        decoded = base64.urlsafe_b64decode(token)
        # token format: key + b':' + data
        _, data = decoded.split(b':', 1)
        return data
