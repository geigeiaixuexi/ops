"""
AES 加密解密工具
"""
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import base64
from django.conf import settings
import hashlib
import hmac

def get_cipher_key():
    """获取AES密钥（32字节）"""
    key = settings.SECRET_KEY.encode('utf-8')
    if len(key) < 32:
        key = key.ljust(32, b'0')
    elif len(key) > 32:
        key = key[:32]
    return key


def encrypt_password(password: str) -> str:
    """AES加密密码"""
    if not password:
        return ''
    try:
        key = get_cipher_key()
        cipher = AES.new(key, AES.MODE_CBC)
        encrypted = cipher.encrypt(pad(password.encode('utf-8'), AES.block_size))
        result = base64.b64encode(cipher.iv + encrypted).decode('utf-8')
        return result
    except Exception as e:
        print(f"加密失败: {e}")
        return password


def decrypt_password(encrypted_password: str) -> str:
    """AES解密密码"""
    if not encrypted_password:
        return ''
    try:
        raw_data = base64.b64decode(encrypted_password)
        key = get_cipher_key()
        iv = raw_data[:16]
        encrypted = raw_data[16:]
        cipher = AES.new(key, AES.MODE_CBC, iv=iv)
        decrypted = unpad(cipher.decrypt(encrypted), AES.block_size)
        return decrypted.decode('utf-8')
    except Exception as e:
        print(f"解密失败: {e}")
        return encrypted_password

def generate_signature(data: str, secret: str) -> str:
    """生成 HMAC-SHA256 签名"""
    return hmac.new(
        secret.encode('utf-8'),
        data.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()


def verify_signature(data: str, signature: str, secret: str) -> bool:
    """验证签名"""
    expected = generate_signature(data, secret)
    return hmac.compare_digest(expected, signature)