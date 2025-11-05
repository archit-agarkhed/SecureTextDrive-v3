from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization

# Function to generate RSA key pair
def generate_rsa_key_pair(key_size):
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size,
        backend=default_backend()
    )
    public_key = private_key.public_key()
    return private_key, public_key

def _max_oaep_chunk_size(public_key) -> int:
    key_size_bytes = public_key.key_size // 8
    hash_len = 32  # SHA-256
    return key_size_bytes - 2 * hash_len - 2

# Function to encrypt data using RSA (chunked to support arbitrary length)
def rsa_encrypt(public_key, data: str) -> bytes:
    data_bytes = data.encode('utf-8')
    max_chunk = _max_oaep_chunk_size(public_key)
    chunks = []
    for i in range(0, len(data_bytes), max_chunk):
        chunk = data_bytes[i:i + max_chunk]
        enc = public_key.encrypt(
            chunk,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        chunks.append(enc)
    return b"".join(chunks)

# Serialize the private key to store it if needed
def serialize_private_key(private_key):
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()  # No encryption for storage
    )

# Serialize the public key to store it if needed
def serialize_public_key(public_key):
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
# Decrypt the encrypted bytes
def rsa_decrypt(private_key, encrypted_data: bytes):
    try:
        key_size_bytes = private_key.key_size // 8
        if len(encrypted_data) % key_size_bytes != 0:
            # If not a multiple, attempt single-block decrypt to surface error
            dec = private_key.decrypt(
                encrypted_data,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            return dec.decode('utf-8')

        plaintext_parts = []
        for i in range(0, len(encrypted_data), key_size_bytes):
            block = encrypted_data[i:i + key_size_bytes]
            dec = private_key.decrypt(
                block,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            plaintext_parts.append(dec)
        return b"".join(plaintext_parts).decode('utf-8')
    except Exception as e:
        print(f"Decryption failed: {str(e)}")
        return None