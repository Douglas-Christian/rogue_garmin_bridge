#!/usr/bin/env python3
"""
Credential Encryption Module for Rogue to Garmin Bridge

Provides symmetric encryption for sensitive data (e.g., Garmin passwords)
stored in the SQLite database. Uses Fernet (AES-128-CBC with HMAC-SHA256)
from the `cryptography` library.

The encryption key is derived from an environment variable or a key file
stored outside the database. This ensures that database exposure alone
does not reveal credentials.
"""

import os
import base64
import logging
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger('credential_encryption')

# Default key file location — sibling to the database directory
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_KEY_FILE = _PROJECT_ROOT / '.credential_key'


def _derive_key(passphrase: bytes, salt: bytes) -> bytes:
    """Derive a Fernet-compatible key from a passphrase and salt."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(passphrase))


def _get_or_create_key() -> bytes:
    """
    Return the Fernet key used for credential encryption.

    Resolution order:
      1. ``CREDENTIAL_KEY`` environment variable (raw Fernet key, base64-encoded).
      2. ``CREDENTIAL_PASSPHRASE`` env var  → derived via PBKDF2 with a
         persisted random salt stored in the key file.
      3. Auto-generated Fernet key persisted to ``_DEFAULT_KEY_FILE``.
    """
    # 1. Explicit key from environment
    env_key = os.environ.get('CREDENTIAL_KEY')
    if env_key:
        return env_key.encode() if isinstance(env_key, str) else env_key

    # 2. Passphrase-derived key
    passphrase = os.environ.get('CREDENTIAL_PASSPHRASE')
    if passphrase:
        salt_file = _DEFAULT_KEY_FILE.with_suffix('.salt')
        if salt_file.exists():
            salt = salt_file.read_bytes()
        else:
            salt = os.urandom(16)
            salt_file.write_bytes(salt)
            os.chmod(str(salt_file), 0o600)
        return _derive_key(passphrase.encode(), salt)

    # 3. Auto-generated key file
    if _DEFAULT_KEY_FILE.exists():
        return _DEFAULT_KEY_FILE.read_bytes().strip()

    key = Fernet.generate_key()
    _DEFAULT_KEY_FILE.write_bytes(key)
    os.chmod(str(_DEFAULT_KEY_FILE), 0o600)
    logger.info("Generated new credential encryption key at %s", _DEFAULT_KEY_FILE)
    return key


def _get_fernet() -> Fernet:
    """Return a cached Fernet instance."""
    # Module-level cache to avoid re-reading the key on every call.
    if not hasattr(_get_fernet, '_instance'):
        _get_fernet._instance = Fernet(_get_or_create_key())
    return _get_fernet._instance


def encrypt_credential(plaintext: str) -> str:
    """
    Encrypt a credential string and return the ciphertext as a
    URL-safe base64 string (prefixed with ``enc:``).
    """
    if not plaintext:
        return ''
    token = _get_fernet().encrypt(plaintext.encode())
    return 'enc:' + token.decode()


def decrypt_credential(stored_value: str) -> str:
    """
    Decrypt a stored credential.

    If *stored_value* does not carry the ``enc:`` prefix it is returned
    as-is (backwards compatibility with pre-encryption databases).
    """
    if not stored_value:
        return ''
    if not stored_value.startswith('enc:'):
        # Legacy plaintext value — return unchanged
        return stored_value
    try:
        token = stored_value[4:].encode()
        return _get_fernet().decrypt(token).decode()
    except InvalidToken:
        logger.error("Failed to decrypt credential — key may have changed")
        return ''


def is_encrypted(value: str) -> bool:
    """Return True if *value* carries the encryption prefix."""
    return bool(value) and value.startswith('enc:')
