import logging
import os
from typing import List
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

# Logger setup
logger = logging.getLogger("storage")
logger.setLevel(logging.INFO)

# S3/MinIO configuration
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL", "http://minio:9000")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "minioadmin")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "minioadmin")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "animal-vocalizations")
S3_REGION = os.getenv("S3_REGION", "us-east-1")

# AES-256 encryption key (must be 32 bytes)
AES_KEY = os.getenv("AES_KEY", "THIS_IS_A_DEMO_KEY_CHANGE_ME_32BYTES!!").encode("utf-8")
AES_IV = os.getenv("AES_IV", "THIS_IS_A_DEMO_IV_16BYTES").encode("utf-8")  # Must be 16 bytes

# Supported audio formats
SUPPORTED_AUDIO_FORMATS = ["wav", "mp3", "flac"]

def get_supported_audio_formats() -> List[str]:
    """
    Returns the list of supported audio file formats.
    """
    return SUPPORTED_AUDIO_FORMATS

def get_s3_client():
    """
    Returns a boto3 S3 client configured for MinIO/AWS S3.
    """
    return boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT_URL,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        region_name=S3_REGION,
    )

def encrypt_bytes(data: bytes) -> bytes:
    """
    Encrypts bytes using AES-256-CBC.
    """
    backend = default_backend()
    cipher = Cipher(algorithms.AES(AES_KEY), modes.CBC(AES_IV), backend=backend)
    encryptor = cipher.encryptor()
    # PKCS7 padding
    pad_len = 16 - (len(data) % 16)
    padded_data = data + bytes([pad_len] * pad_len)
    encrypted = encryptor.update(padded_data) + encryptor.finalize()
    return encrypted

def decrypt_bytes(data: bytes) -> bytes:
    """
    Decrypts bytes using AES-256-CBC.
    """
    backend = default_backend()
    cipher = Cipher(algorithms.AES(AES_KEY), modes.CBC(AES_IV), backend=backend)
    decryptor = cipher.decryptor()
    decrypted = decryptor.update(data) + decryptor.finalize()
    # Remove PKCS7 padding
    pad_len = decrypted[-1]
    return decrypted[:-pad_len]

def store_encrypted_audio_file(object_key: str, file_bytes: bytes, content_type: str) -> None:
    """
    Encrypts and stores an audio file in S3/MinIO.
    """
    s3 = get_s3_client()
    encrypted_bytes = encrypt_bytes(file_bytes)
    try:
        s3.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=object_key,
            Body=encrypted_bytes,
            ContentType=content_type,
            ServerSideEncryption="AES256",  # S3-side encryption (optional, double encryption)
        )
        logger.info(f"Stored encrypted audio file: {object_key}")
    except (BotoCoreError, ClientError) as e:
        logger.error(f"Failed to store audio file in S3: {e}")
        raise

def retrieve_encrypted_audio_file(object_key: str) -> bytes:
    """
    Retrieves and decrypts an audio file from S3/MinIO.
    """
    s3 = get_s3_client()
    try:
        response = s3.get_object(Bucket=S3_BUCKET_NAME, Key=object_key)
        encrypted_bytes = response["Body"].read()
        decrypted_bytes = decrypt_bytes(encrypted_bytes)
        logger.info(f"Retrieved and decrypted audio file: {object_key}")
        return decrypted_bytes
    except (BotoCoreError, ClientError) as e:
        logger.error(f"Failed to retrieve audio file from S3: {e}")
        raise

def ensure_bucket_exists():
    """
    Ensures the S3/MinIO bucket exists.
    """
    s3 = get_s3_client()
    try:
        s3.head_bucket(Bucket=S3_BUCKET_NAME)
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            s3.create_bucket(Bucket=S3_BUCKET_NAME)
            logger.info(f"Created S3 bucket: {S3_BUCKET_NAME}")
        else:
            logger.error(f"Failed to ensure S3 bucket exists: {e}")
            raise

# Exported symbols
__all__ = [
    "store_encrypted_audio_file",
    "retrieve_encrypted_audio_file",
    "get_supported_audio_formats",
    "ensure_bucket_exists",
]