import os
import time
import numpy as np
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
# --- NEW IMPORT ---
from cryptography.exceptions import InvalidTag 

# --- SECURITY LAYER ---
def get_shared_key():
    return b'\x00' * 32 

def encrypt_data(data_array):
    key = get_shared_key()
    iv = os.urandom(12)
    plaintext = data_array.tobytes()
    encryptor = Cipher(algorithms.AES(key), modes.GCM(iv), backend=default_backend()).encryptor()
    ciphertext = encryptor.update(plaintext) + encryptor.finalize()
    return iv, ciphertext, encryptor.tag

def decrypt_data(iv, ciphertext, tag, shape):
    key = get_shared_key()
    decryptor = Cipher(algorithms.AES(key), modes.GCM(iv, tag), backend=default_backend()).decryptor()
    decrypted_bytes = decryptor.update(ciphertext) + decryptor.finalize()
    return np.frombuffer(decrypted_bytes).reshape(shape)

# --- MATH LAYER (Atomic Writes & Retry Logic) ---
def save_packet(filename, data_array):
    """Atomic write to prevent race conditions."""
    iv, ciphertext, tag = encrypt_data(data_array)
    temp_filename = filename + ".tmp"
    
    # Write to temp file
    with open(temp_filename, 'wb') as f:
        np.savez(f, iv=iv, ciphertext=ciphertext, tag=tag, shape=data_array.shape)
        f.flush()
        os.fsync(f.fileno()) # Force write to disk

    # Atomic swap
    os.replace(temp_filename, filename)

def load_packet(filename):
    """Stubborn load function that retries on File Locks AND Crypto Errors."""
    max_retries = 15 # Increased retries
    for attempt in range(max_retries):
        try:
            packet = np.load(filename)
            iv = packet['iv'].item()
            ciphertext = packet['ciphertext'].item()
            tag = packet['tag'].item()
            shape = packet['shape']
            return decrypt_data(iv, ciphertext, tag, shape)
            
        # --- THE FIX: Catch InvalidTag here ---
        except (OSError, ValueError, EOFError, KeyError, InvalidTag) as e:
            if attempt < max_retries - 1:
                # Exponential Backoff: Wait longer each time (0.2, 0.4, 0.8...)
                sleep_time = 0.2 * (1.5 ** attempt)
                time.sleep(sleep_time)
                continue
            raise IOError(f"Failed to load {filename} after {max_retries} attempts. Last Error: {e}")