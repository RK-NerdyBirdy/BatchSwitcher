from pwdlib import PasswordHash
from pwdlib.hashers.bcrypt import BcryptHasher

# Initialize the modern password hasher
password_hash = PasswordHash((BcryptHasher(),))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return password_hash.hash(password)
