"""Password hashing utilities."""
import hashlib

import bcrypt


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Bcrypt has a 72-byte limit, so we first hash with SHA256 to ensure
    consistent length and handle longer passwords.
    """
    # First hash with SHA256 to ensure consistent 32-byte length
    # This allows us to handle passwords of any length
    sha256_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
    # Convert to bytes for bcrypt (hexdigest is already a string, encode it)
    password_bytes = sha256_hash.encode('utf-8')
    # Generate salt and hash with bcrypt
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    # Return as string (bcrypt hash is bytes)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Matches the hashing strategy: SHA256 first, then bcrypt.
    """
    # Hash the plain password with SHA256 first
    sha256_hash = hashlib.sha256(plain_password.encode('utf-8')).hexdigest()
    # Convert to bytes for bcrypt
    password_bytes = sha256_hash.encode('utf-8')
    # Verify against the bcrypt hash
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)

