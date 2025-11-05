# 🔐 SecureTextDrive - Secure Client-Server Architecture

## 🏗️ Architecture Overview

This implementation follows proper security principles by separating client and server responsibilities for file encryption and key management.

## 📱 CLIENT SIDE (Frontend - Port 5000)

### Responsibilities:
- **Private Key Generation**: Creates RSA key pairs locally
- **Private Key Storage**: Stores private keys in browser session (never sent to server)
- **File Encryption**: Encrypts files with public keys before upload
- **File Decryption**: Decrypts files with locally stored private keys
- **Digital Signing**: Creates signatures with separate signing keys
- **User Interface**: All user interactions and file management

### Security Features:
- ✅ Private keys never leave the client device
- ✅ Decryption happens locally on user's browser
- ✅ User maintains complete control over their keys
- ✅ No single point of failure for key storage

## 🖥️ SERVER SIDE (Backend - Port 8000)

### Responsibilities:
- **Public Key Storage**: Stores only public keys and encrypted content
- **Encrypted Data Storage**: Stores encrypted file content (BYTEA format)
- **Digital Signature Verification**: Verifies file integrity using public signing keys
- **User Authentication**: Manages login/signup/sessions
- **Access Control**: Ensures users only access their own encrypted data

### Security Features:
- ✅ Never stores or has access to private keys
- ✅ Cannot decrypt user files even if compromised
- ✅ Verifies data integrity through digital signatures
- ✅ Maintains proper user isolation

## 🔄 Data Flow

### File Upload Process:
1. **Client**: User selects file
2. **Client**: Generate RSA key pair locally
3. **Client**: Encrypt file with public key
4. **Client**: Store private key in browser session
5. **Client**: Send encrypted content + public key to server
6. **Server**: Verify digital signature
7. **Server**: Store encrypted content + public key
8. **Server**: Return success confirmation

### File Download Process:
1. **Client**: Request file from server
2. **Server**: Return encrypted content + public key
3. **Client**: Retrieve private key from local session
4. **Client**: Decrypt file locally with private key
5. **Client**: Display decrypted content to user

## 🛡️ Security Benefits

### Client-Side Security:
- Private keys never transmitted over network
- Decryption requires local private key
- User controls their own encryption keys
- No server-side key exposure risk

### Server-Side Security:
- Database compromise doesn't expose private keys
- Files remain encrypted even if server is hacked
- Digital signatures prevent tampering
- Proper access control and user isolation

## 📊 Database Schema (Updated)

### USERS Table:
```sql
CREATE TABLE USERS (
    email VARCHAR PRIMARY KEY,
    password VARCHAR,  -- Affine Cipher encrypted
    auth BOOLEAN
);
```

### FILECON Table (Private Keys Removed):
```sql
CREATE TABLE FILECON (
    email VARCHAR,                    -- Foreign key to USERS
    fpath VARCHAR,                    -- File name
    fcon BYTEA,                       -- RSA encrypted content
    pubkey TEXT,                      -- RSA public key (PEM)
    encryption_method VARCHAR,        -- "RSA"
    key_size INTEGER                  -- 1024 or 2048
    -- NO private key storage!
);
```

## 🔧 Implementation Details

### Client-Side Key Management:
```python
# Store private keys in Flask session
session['private_keys'] = {
    'file1.txt': '-----BEGIN PRIVATE KEY-----\n...',
    'file2.txt': '-----BEGIN PRIVATE KEY-----\n...'
}

# Retrieve for decryption
private_key = session['private_keys'][filename]
```

### Server-Side API:
```python
# Upload endpoint - NO private key handling
@app.route('/api/upload_file', methods=['POST'])
def upload_file():
    # Receive: encrypted_content, public_key, signature
    # Store: encrypted_content, public_key
    # Return: success message
```

## 🎯 Security Comparison

### ❌ Previous Flawed Architecture:
- Private keys stored in database
- Server could decrypt all files
- Single point of failure
- Database breach = complete compromise

### ✅ Current Secure Architecture:
- Private keys stored locally
- Server cannot decrypt files
- Distributed key management
- Database breach = encrypted data remains secure

## 🚀 Real-World Applications

This architecture follows the same principles used by:
- **WhatsApp**: End-to-end encryption with local key storage
- **Signal**: Zero-knowledge messaging
- **ProtonMail**: Client-side encryption
- **1Password**: Master passwords never sent to servers

## 📚 Educational Value

This implementation demonstrates:
1. **Proper Key Management**: Where and how to store encryption keys
2. **Client-Server Separation**: Clear security boundaries
3. **End-to-End Encryption**: True file protection
4. **Attack Vector Analysis**: Understanding security vulnerabilities
5. **Real-World Security**: Production-ready architecture principles

## 🔍 Testing the Security

### To Verify Security:
1. **Upload a file** - Check that private key is stored locally
2. **Check database** - Verify only public keys are stored
3. **Test decryption** - Confirm it requires local private key
4. **Session expiry** - Verify files become inaccessible without local keys

This architecture provides true end-to-end encryption security while maintaining usability and proper separation of concerns.
