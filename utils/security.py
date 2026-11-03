import io
import os
import pandas as pd

try:
    from cryptography.fernet import Fernet
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False


class DataSecurityManager:
    """Gerencia a leitura segura de arquivos criptografados em memória no back-end."""

    @staticmethod
    def load_encrypted_excel(encrypted_path: str, key: bytes, sheet_name=0) -> pd.DataFrame:
        if not HAS_CRYPTO or not os.path.exists(encrypted_path):
            return None
        f = Fernet(key)
        with open(encrypted_path, "rb") as file:
            encrypted_data = file.read()
        decrypted_data = f.decrypt(encrypted_data)
        return pd.read_excel(io.BytesIO(decrypted_data), sheet_name=sheet_name)