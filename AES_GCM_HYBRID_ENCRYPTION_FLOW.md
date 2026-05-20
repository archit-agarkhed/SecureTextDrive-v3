# AES-GCM Hybrid Encryption Flow for SecureTextDrive

This document explains the improved encryption, hashing, signing, verification, and decryption flow for SecureTextDrive if the project is upgraded from direct RSA file encryption to a production-style hybrid encryption model.

The goal is to make the full flow easy to explain in an interview, easy to implement later, and easy to connect back to the current project.

## 1. Big Picture

The improved design uses three main cryptographic tools:

```text
AES-GCM       -> encrypts the actual file/message content
RSA-OAEP      -> encrypts the AES key
RSA Signature -> proves the encrypted package was not tampered with
SHA-256       -> creates a digest/fingerprint before signing
```

In one line:

```text
AES-GCM protects the file, RSA-OAEP protects the AES key, and RSA signatures prove authenticity.
```

## 2. Why Not Encrypt The Whole File With RSA?

RSA is not designed for encrypting large files directly.

RSA is good for:

- Encrypting small secrets
- Encrypting symmetric keys
- Digital signatures
- Key exchange/key wrapping

RSA is not ideal for:

- Large files
- Long messages
- Fast bulk encryption
- Efficient storage encryption

AES is designed for bulk data encryption.

So the better design is:

```text
Use AES-GCM to encrypt the file.
Use RSA-OAEP to encrypt the AES key.
```

This is called hybrid encryption.

## 3. What Is Hybrid Encryption?

Hybrid encryption combines symmetric and asymmetric cryptography.

Symmetric encryption:

```text
Same key encrypts and decrypts.
Example: AES
```

Asymmetric encryption:

```text
Public key encrypts.
Private key decrypts.
Example: RSA
```

Hybrid encryption uses both:

```text
File content -> AES-GCM -> ciphertext
AES key      -> RSA-OAEP -> encrypted AES key
```

The encrypted file and encrypted AES key are stored together.

## 4. Important Terms

### Plaintext

The original readable file content.

Example:

```text
Hello, this is my private note.
```

### AES Key

A random secret key generated for encrypting one file.

This key must stay secret.

Example idea:

```text
AES key = 256 random bits
```

### Ciphertext

The encrypted unreadable output produced by AES-GCM.

Example idea:

```text
plaintext -> AES-GCM -> ciphertext
```

### Nonce / IV

A random value used with AES-GCM encryption.

It is not secret, but it must be unique for the same AES key.

In AES-GCM, a 96-bit nonce is commonly used.

### Authentication Tag

AES-GCM produces an authentication tag.

The tag is used to detect tampering.

If the ciphertext, nonce, tag, or additional authenticated data is changed, decryption fails.

### RSA Public Key

Used to encrypt the AES key.

It can be stored on the backend.

### RSA Private Key

Used to decrypt the encrypted AES key.

It must stay with the user/client side.

### SHA-256 Digest

A fixed-size fingerprint of data.

If the input changes, the digest changes completely.

### Digital Signature

A cryptographic proof created using a signing private key.

It proves:

- The signed data was not changed
- The signer had the signing private key

## 5. Keys Used In The Improved Design

There are ideally three different keys or key pairs involved.

### 5.1 AES File Key

Generated randomly for each uploaded file.

Purpose:

```text
Encrypt and decrypt the file content.
```

Stored:

```text
Never stored raw in the database.
Only stored after being encrypted with RSA-OAEP.
```

### 5.2 RSA Encryption Key Pair

Used for protecting the AES key.

```text
RSA public encryption key  -> encrypts AES key
RSA private encryption key -> decrypts AES key
```

The backend can store:

```text
RSA public key
encrypted AES key
```

The backend should not store:

```text
RSA private key
raw AES key
```

### 5.3 RSA Signing Key Pair

Used for signatures.

```text
RSA signing private key -> signs digest
RSA signing public key  -> verifies signature
```

Ideally, signing and encryption use separate RSA key pairs.

Why?

Because encryption and signing are different cryptographic purposes.

Using separate keys makes the system cleaner and safer.

## 6. Complete Upload Flow

This is what happens when a user uploads a file.

```text
User selects file
   |
   v
Frontend reads plaintext content
   |
   v
Frontend generates random AES key
   |
   v
Frontend generates random AES-GCM nonce
   |
   v
Frontend encrypts plaintext with AES-GCM
   |
   v
Frontend encrypts AES key with RSA-OAEP public key
   |
   v
Frontend creates encrypted package
   |
   v
Frontend hashes package with SHA-256
   |
   v
Frontend signs digest with RSA signing private key
   |
   v
Frontend sends package to backend
   |
   v
Backend verifies signature
   |
   v
Backend stores encrypted package in database
```

## 7. Upload Flow In Detail

### Step 1: User Selects A File

The user uploads a text file.

Example plaintext:

```text
My bank PIN is not actually here, this is just a demo file.
```

At this point, the content is readable.

### Step 2: Frontend Generates A Random AES Key

The frontend generates a new AES key for this file.

Recommended:

```text
AES-256 key = 32 random bytes
```

This key is unique per file.

That means each file gets its own encryption key.

Why this is good:

- If one file key is compromised, other files are still protected.
- Key rotation is easier.
- File encryption is isolated.

### Step 3: Frontend Generates A Nonce / IV

AES-GCM needs a nonce.

Recommended:

```text
Nonce = 12 random bytes
```

The nonce is not secret, but it must be stored because decryption needs it.

Important rule:

```text
Never reuse the same nonce with the same AES key.
```

Since this design creates a fresh AES key per file, nonce reuse risk is reduced.

### Step 4: Frontend Encrypts The File With AES-GCM

Input:

```text
plaintext file content
AES key
nonce
optional AAD
```

Output:

```text
ciphertext
authentication tag
```

Flow:

```text
Plaintext
   |
   v
AES-GCM(AES key, nonce)
   |
   v
Ciphertext + authentication tag
```

AES-GCM gives:

```text
Confidentiality -> hides the content
Integrity       -> detects tampering
```

So if someone modifies the ciphertext, AES-GCM decryption fails.

### Step 5: Frontend Encrypts The AES Key With RSA-OAEP

The AES key itself is a secret.

So the app encrypts the AES key using RSA-OAEP and the user's RSA public key.

Flow:

```text
Raw AES key
   |
   v
RSA-OAEP public key encryption
   |
   v
Encrypted AES key
```

Only the matching RSA private key can decrypt it.

This is the core hybrid encryption idea.

### Step 6: Frontend Builds The Encrypted Package

The package should contain everything needed for storage and later decryption, except private secrets.

Example package:

```json
{
  "email": "user@example.com",
  "filename": "note.txt",
  "encryption_method": "AES-256-GCM + RSA-OAEP",
  "ciphertext": "...base64...",
  "nonce": "...base64...",
  "tag": "...base64...",
  "encrypted_aes_key": "...base64...",
  "rsa_public_key": "-----BEGIN PUBLIC KEY-----...",
  "signing_public_key": "-----BEGIN PUBLIC KEY-----...",
  "signature": "...base64..."
}
```

The backend can store this because it does not include:

```text
plaintext
raw AES key
RSA private key
signing private key
```

### Step 7: Frontend Hashes The Package

The frontend creates a SHA-256 digest of the important fields.

A good signing input could be:

```text
email
filename
ciphertext
nonce
tag
encrypted_aes_key
encryption_method
key_version
```

Then:

```text
SHA-256(signing input) -> digest
```

The digest is a fingerprint.

If any signed field changes, the digest changes.

### Step 8: Frontend Signs The Digest

The frontend signs the digest using the RSA signing private key.

Flow:

```text
Digest
   |
   v
RSA signing private key
   |
   v
Digital signature
```

The signature proves:

```text
The encrypted package has not changed since it was signed.
```

It also proves:

```text
The signer had the signing private key.
```

### Step 9: Frontend Sends The Package To Backend

The frontend sends:

```text
email
filename
ciphertext
nonce
tag
encrypted AES key
RSA public encryption key
RSA signing public key
signature
metadata
```

The frontend does not send:

```text
plaintext
raw AES key
RSA private encryption key
RSA signing private key
```

### Step 10: Backend Verifies Signature

The backend repeats the same hashing process.

```text
Received package fields
   |
   v
SHA-256
   |
   v
Backend digest
```

Then the backend verifies the signature:

```text
Backend digest + signature + signing public key
   |
   v
RSA signature verification
   |
   v
Valid / invalid
```

If valid:

```text
Store the package.
```

If invalid:

```text
Reject the upload.
```

This is important.

The backend should never store a file whose signature verification failed.

## 8. What The Backend Stores

In the database, the backend stores encrypted data and public metadata.

Possible table columns:

```sql
CREATE TABLE filecon (
    id SERIAL PRIMARY KEY,
    email VARCHAR NOT NULL,
    fpath VARCHAR NOT NULL,
    ciphertext BYTEA NOT NULL,
    nonce BYTEA NOT NULL,
    auth_tag BYTEA NOT NULL,
    encrypted_aes_key BYTEA NOT NULL,
    rsa_public_key TEXT NOT NULL,
    signing_public_key TEXT NOT NULL,
    signature BYTEA NOT NULL,
    encryption_method VARCHAR NOT NULL,
    key_size INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

The backend stores:

```text
Encrypted file content
AES-GCM nonce
AES-GCM authentication tag
Encrypted AES key
Public encryption key
Public signing key
Digital signature
Metadata
```

The backend does not store:

```text
Plaintext file
Raw AES key
RSA private encryption key
RSA signing private key
```

## 9. Complete Download / Preview Flow

This is what happens when the user wants to open a stored file.

```text
User clicks file
   |
   v
Frontend asks backend for encrypted package
   |
   v
Backend returns encrypted package
   |
   v
Frontend verifies signature
   |
   v
Frontend decrypts AES key with RSA private key
   |
   v
Frontend decrypts ciphertext with AES-GCM
   |
   v
Frontend displays plaintext
```

## 10. Download / Preview Flow In Detail

### Step 1: User Clicks A File

The user clicks:

```text
note.txt
```

The frontend sends a request to the backend:

```json
{
  "email": "user@example.com",
  "filename": "note.txt"
}
```

### Step 2: Backend Returns The Encrypted Package

The backend returns:

```json
{
  "filename": "note.txt",
  "ciphertext": "...base64...",
  "nonce": "...base64...",
  "tag": "...base64...",
  "encrypted_aes_key": "...base64...",
  "signing_public_key": "-----BEGIN PUBLIC KEY-----...",
  "signature": "...base64...",
  "encryption_method": "AES-256-GCM + RSA-OAEP"
}
```

The backend still does not send plaintext.

### Step 3: Frontend Verifies The Signature

Before decrypting, the frontend should verify the signature again.

This checks whether the stored encrypted package was changed in the database.

Flow:

```text
Returned package fields
   |
   v
SHA-256
   |
   v
Digest
   |
   v
Verify signature with signing public key
```

If verification fails:

```text
Do not decrypt.
Show an error.
```

If verification succeeds:

```text
Continue to key decryption.
```

### Step 4: Frontend Gets The RSA Private Key

The frontend needs the user's RSA private encryption key.

In your current project style, this might be in the frontend Flask session.

In a stronger real-world design, it would be in:

```text
Browser-side secure storage
OS keystore
User passphrase-encrypted private key
Hardware-backed key store
```

The backend should not have it.

### Step 5: Frontend Decrypts The AES Key

The frontend uses the RSA private key to decrypt the encrypted AES key.

Flow:

```text
Encrypted AES key
   |
   v
RSA-OAEP private key decryption
   |
   v
Raw AES key
```

Now the frontend has the AES key needed for this file.

### Step 6: Frontend Decrypts The File With AES-GCM

The frontend uses:

```text
AES key
ciphertext
nonce
authentication tag
optional AAD
```

Flow:

```text
Ciphertext + nonce + tag
   |
   v
AES-GCM decrypt with AES key
   |
   v
Plaintext
```

If anything was modified, AES-GCM rejects decryption.

That is why AES-GCM is so useful.

It does not just decrypt.

It also checks integrity.

### Step 7: User Sees The File

The frontend displays:

```text
My bank PIN is not actually here, this is just a demo file.
```

At this stage, the user can:

- Preview the text
- Download it
- Summarize it
- Delete it

## 11. Hashing In This Design

Hashing is used to create a digest before signing.

The hash function should be:

```text
SHA-256
```

Hashing does not encrypt.

Hashing does not hide the file.

Hashing creates a fingerprint.

Example:

```text
data -> SHA-256 -> digest
```

If the data changes, the digest changes.

So hashing helps detect changes.

But by itself, hashing does not prove who created the data.

That is why we add a digital signature.

## 12. Signing In This Design

The signature is created over the digest.

Flow:

```text
Package fields
   |
   v
SHA-256 digest
   |
   v
Sign digest with RSA signing private key
   |
   v
Digital signature
```

Verification:

```text
Package fields
   |
   v
SHA-256 digest
   |
   v
Verify signature with RSA signing public key
   |
   v
Valid / invalid
```

The digital signature provides:

```text
Integrity    -> package was not changed
Authenticity -> signer had the private signing key
```

## 13. AES-GCM Integrity vs Digital Signature Integrity

AES-GCM already provides integrity for encrypted content.

So why still sign?

Because AES-GCM and digital signatures answer different questions.

AES-GCM answers:

```text
Was this ciphertext/tag modified before decryption?
```

Digital signature answers:

```text
Was this package signed by the holder of the signing private key?
Did any signed metadata change?
```

AES-GCM protects the encrypted file content.

Digital signatures protect the whole package and prove authenticity.

Recommended signed fields:

```text
email
filename
ciphertext
nonce
tag
encrypted AES key
encryption method
key version
created timestamp if stable
```

## 14. Additional Authenticated Data

AES-GCM supports Additional Authenticated Data, usually called AAD.

AAD is not encrypted, but it is authenticated.

That means if AAD changes, decryption fails.

Good AAD values:

```text
email
filename
file id
encryption method
key version
```

Example idea:

```text
AAD = email + "|" + filename + "|" + encryption_method
```

Then AES-GCM protects against someone moving ciphertext from one filename/user context to another.

## 15. Recommended Stored Package

A practical encrypted file record could look like this:

```json
{
  "email": "archit@example.com",
  "filename": "notes.txt",
  "encryption_method": "AES-256-GCM",
  "key_wrapping_method": "RSA-OAEP-SHA256",
  "signature_method": "RSA-PSS-SHA256",
  "nonce": "base64-encoded nonce",
  "ciphertext": "base64-encoded ciphertext",
  "auth_tag": "base64-encoded tag",
  "encrypted_aes_key": "base64-encoded RSA encrypted AES key",
  "encryption_public_key": "PEM public key",
  "signing_public_key": "PEM public key",
  "signature": "base64-encoded signature"
}
```

If using a Python cryptography library, AES-GCM often returns ciphertext and tag together depending on the API.

The project should choose one representation and document it clearly.

## 16. Recommended Algorithms

### File Encryption

```text
AES-256-GCM
```

Why:

- Fast
- Secure when used correctly
- Designed for large data
- Provides encryption and integrity

### AES Key Wrapping

```text
RSA-OAEP with SHA-256
```

Why:

- RSA should encrypt small data only
- AES key is small
- OAEP is the correct modern RSA encryption padding

### Digital Signature

Recommended:

```text
RSA-PSS with SHA-256
```

Acceptable for demo:

```text
RSA PKCS#1 v1.5 signature with SHA-256
```

Modern alternatives:

```text
Ed25519
ECDSA with P-256
```

### Hashing

```text
SHA-256
```

## 17. Interview Explanation

Short version:

```text
I would use hybrid encryption. The file content is encrypted with AES-GCM because AES is efficient for bulk data and GCM gives integrity through an authentication tag. Then I encrypt the random AES key with the user's RSA public key, so only the matching RSA private key can recover it. For authenticity, I hash the encrypted package with SHA-256 and sign that digest with an RSA signing private key. The backend stores only ciphertext, nonce, tag, encrypted AES key, public keys, signature, and metadata. During preview, the frontend verifies the signature, decrypts the AES key using the RSA private key, and then decrypts the file with AES-GCM.
```

Very short version:

```text
AES-GCM encrypts the file, RSA-OAEP encrypts the AES key, and RSA signatures verify the encrypted package.
```

## 18. End-To-End Example

### Input File

```text
hello from SecureTextDrive
```

### Generate AES Key

```text
AES key = random 32 bytes
```

### Generate Nonce

```text
nonce = random 12 bytes
```

### Encrypt With AES-GCM

```text
plaintext + AES key + nonce
   |
   v
ciphertext + auth tag
```

### Encrypt AES Key With RSA

```text
AES key + RSA public key
   |
   v
encrypted AES key
```

### Create Signing Input

```text
email
filename
ciphertext
nonce
auth tag
encrypted AES key
metadata
```

### Hash Signing Input

```text
signing input
   |
   v
SHA-256 digest
```

### Sign Digest

```text
digest + RSA signing private key
   |
   v
signature
```

### Store In Database

```text
email
filename
ciphertext
nonce
auth tag
encrypted AES key
public encryption key
public signing key
signature
metadata
```

### Decrypt Later

```text
Verify signature
   |
   v
Decrypt AES key with RSA private key
   |
   v
Decrypt ciphertext with AES-GCM
   |
   v
plaintext
```

## 19. How This Maps To The Current Project

The current project already has some of the building blocks:

Current project:

```text
RSA encrypts file content directly
SHA-256 creates digest
RSA signs digest
Backend verifies signature
Backend stores encrypted content
Frontend decrypts with private key
```

Improved project:

```text
AES-GCM encrypts file content
RSA-OAEP encrypts AES key
SHA-256 creates digest of encrypted package
RSA signs digest
Backend verifies signature
Backend stores encrypted package
Frontend decrypts AES key with RSA private key
Frontend decrypts file with AES-GCM
```

Main change:

```text
Replace direct RSA file encryption with AES-GCM file encryption.
Keep RSA for protecting the AES key and for signatures.
```

## 20. Suggested Database Changes

Current-style database stores:

```text
fcon
pubkey
encryption_method
key_size
```

Improved database should store:

```text
ciphertext
nonce
auth_tag
encrypted_aes_key
encryption_public_key
signing_public_key
signature
encryption_method
key_wrapping_method
signature_method
```

Possible migration:

```sql
ALTER TABLE filecon
ADD COLUMN nonce BYTEA,
ADD COLUMN auth_tag BYTEA,
ADD COLUMN encrypted_aes_key BYTEA,
ADD COLUMN signing_public_key TEXT,
ADD COLUMN signature BYTEA,
ADD COLUMN key_wrapping_method VARCHAR,
ADD COLUMN signature_method VARCHAR;
```

## 21. Pseudocode For Upload

```python
def upload_file(plaintext, filename, email):
    # 1. Generate AES key and nonce
    aes_key = os.urandom(32)      # AES-256
    nonce = os.urandom(12)        # GCM recommended nonce size

    # 2. Create AAD
    aad = f"{email}|{filename}|AES-256-GCM".encode()

    # 3. Encrypt plaintext with AES-GCM
    ciphertext, tag = aes_gcm_encrypt(
        key=aes_key,
        nonce=nonce,
        plaintext=plaintext,
        aad=aad
    )

    # 4. Encrypt AES key with RSA-OAEP
    encrypted_aes_key = rsa_oaep_encrypt(
        public_key=user_encryption_public_key,
        data=aes_key
    )

    # 5. Create signing input
    signing_input = canonical_encode({
        "email": email,
        "filename": filename,
        "ciphertext": ciphertext,
        "nonce": nonce,
        "tag": tag,
        "encrypted_aes_key": encrypted_aes_key,
        "encryption_method": "AES-256-GCM",
        "key_wrapping_method": "RSA-OAEP-SHA256"
    })

    # 6. Hash signing input
    digest = sha256(signing_input)

    # 7. Sign digest
    signature = rsa_sign(signing_private_key, digest)

    # 8. Send package to backend
    return {
        "email": email,
        "filename": filename,
        "ciphertext": base64(ciphertext),
        "nonce": base64(nonce),
        "tag": base64(tag),
        "encrypted_aes_key": base64(encrypted_aes_key),
        "signature": base64(signature),
        "signing_public_key": signing_public_key_pem
    }
```

## 22. Pseudocode For Backend Verification

```python
def verify_and_store(package):
    signing_input = canonical_encode({
        "email": package["email"],
        "filename": package["filename"],
        "ciphertext": base64_decode(package["ciphertext"]),
        "nonce": base64_decode(package["nonce"]),
        "tag": base64_decode(package["tag"]),
        "encrypted_aes_key": base64_decode(package["encrypted_aes_key"]),
        "encryption_method": package["encryption_method"],
        "key_wrapping_method": package["key_wrapping_method"]
    })

    digest = sha256(signing_input)

    valid = rsa_verify(
        public_key=package["signing_public_key"],
        digest=digest,
        signature=base64_decode(package["signature"])
    )

    if not valid:
        raise ValueError("Invalid signature")

    database.insert(package)
```

## 23. Pseudocode For Decryption

```python
def decrypt_file(package, rsa_private_key):
    # 1. Verify signature before decrypting
    verify_signature(package)

    # 2. Decrypt AES key
    aes_key = rsa_oaep_decrypt(
        private_key=rsa_private_key,
        ciphertext=base64_decode(package["encrypted_aes_key"])
    )

    # 3. Rebuild AAD
    aad = f"{package['email']}|{package['filename']}|AES-256-GCM".encode()

    # 4. Decrypt file
    plaintext = aes_gcm_decrypt(
        key=aes_key,
        nonce=base64_decode(package["nonce"]),
        ciphertext=base64_decode(package["ciphertext"]),
        tag=base64_decode(package["tag"]),
        aad=aad
    )

    return plaintext
```

## 24. Common Interview Questions

### Why AES-GCM?

AES-GCM is efficient for large data and provides authenticated encryption. That means it hides the file content and detects tampering.

### Why RSA at all?

RSA is used to protect the AES key. AES needs the same key for encryption and decryption, so the AES key must be securely delivered/stored. RSA-OAEP lets us encrypt that small AES key with a public key.

### Why not use RSA for the whole file?

RSA is slower and has size limitations. It is not meant for bulk file encryption. AES is the correct tool for large data.

### Why use SHA-256 if AES-GCM already has integrity?

AES-GCM verifies the ciphertext and tag during decryption. SHA-256 plus a digital signature verifies the whole stored package and proves authenticity before storage or retrieval.

### What does the backend know?

The backend knows:

```text
encrypted data
public keys
metadata
signature
```

The backend should not know:

```text
plaintext
raw AES key
private keys
```

### What happens if the database is leaked?

An attacker sees encrypted data, public keys, encrypted AES keys, signatures, and metadata.

They should not be able to decrypt file contents without the RSA private key.

### What happens if someone changes the ciphertext?

Two protections should catch it:

1. The digital signature verification should fail.
2. AES-GCM decryption should fail because the authentication tag will not match.

### What happens if the encrypted AES key is changed?

Signature verification should fail.

If signature verification is skipped, RSA-OAEP decryption should fail or produce no valid AES key.

### What happens if the nonce is changed?

Signature verification should fail.

If signature verification is skipped, AES-GCM decryption should fail.

### What happens if the tag is changed?

Signature verification should fail.

If signature verification is skipped, AES-GCM decryption should fail.

## 25. Clean Final Explanation

Use this when explaining the improved design:

```text
When a user uploads a file, the frontend generates a random AES-256 key and encrypts the file using AES-GCM. AES-GCM produces ciphertext and an authentication tag, so the content is hidden and tampering can be detected. Since the AES key is required to decrypt the file, the frontend encrypts that AES key using the user's RSA public key with OAEP padding. Then the frontend hashes the encrypted package using SHA-256 and signs the digest with an RSA signing private key. The backend verifies the signature and stores only the ciphertext, nonce, tag, encrypted AES key, public keys, signature, and metadata. Later, when the user opens the file, the frontend verifies the signature, decrypts the AES key using the RSA private key, and then decrypts the file using AES-GCM. The backend never needs the plaintext or the private keys.
```

## 26. One-Line Memory Hook

```text
AES-GCM locks the file, RSA-OAEP locks the AES key, and RSA signatures seal the package.
```

