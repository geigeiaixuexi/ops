"""
AES 加密解密工具
用于密码的可逆加密存储
"""
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import base64
from django.conf import settings
import hashlib
import hmac

# 使用 Django 的 SECRET_KEY 作为加密密钥（取前32字节）
def get_cipher_key():
    """获取AES密钥（32字节）"""
    key = settings.SECRET_KEY.encode('utf-8')
    if len(key) < 32:
        key = key.ljust(32, b'0')
    elif len(key) > 32:
        key = key[:32]
    return key


def encrypt_password(password: str) -> str:
    """
    AES加密密码
    返回: Base64编码的加密字符串
    """
    if not password:
        return ''
    
    try:
        key = get_cipher_key()
        # 创建AES cipher对象
        cipher = AES.new(key, AES.MODE_CBC)
        # 加密
        encrypted = cipher.encrypt(pad(password.encode('utf-8'), AES.block_size))
        # 将IV和加密数据拼接并Base64编码
        result = base64.b64encode(cipher.iv + encrypted).decode('utf-8')
        return result
    except Exception as e:
        print(f"加密失败: {e}")
        return password


def decrypt_password(encrypted_password: str) -> str:
    """
    AES解密密码
    参数: Base64编码的加密字符串
    返回: 明文密码
    """
    if not encrypted_password:
        return ''
    
    try:
        # 先检查是否是加密格式（尝试Base64解码）
        try:
            raw_data = base64.b64decode(encrypted_password)
        except:
            # 如果不是Base64格式，可能是明文，直接返回
            return encrypted_password
        
        key = get_cipher_key()
        # 提取IV（前16字节）
        iv = raw_data[:16]
        # 提取加密数据
        encrypted = raw_data[16:]
        # 解密
        cipher = AES.new(key, AES.MODE_CBC, iv=iv)
        decrypted = unpad(cipher.decrypt(encrypted), AES.block_size)
        return decrypted.decode('utf-8')
    except Exception as e:
        print(f"解密失败: {e}")
        return encrypted_password


def is_encrypted(password: str) -> bool:
    """判断密码是否已加密"""
    if not password:
        return False
    try:
        # 尝试Base64解码，如果成功且长度大于32，可能是加密的
        raw = base64.b64decode(password)
        return len(raw) > 32
    except:
        return False
    
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