#!/usr/bin/env python
"""测试对外 API"""
import os
import sys
import django

# 设置 Django 环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

import requests
import json
from server_mgr.utils.crypto import encrypt_password,decrypt_password
from server_mgr.models import ApiKey

def test_external_api():
    # 获取 API Key
    api_key_obj = ApiKey.objects.first()
    if not api_key_obj:
        print("请先创建 API Key")
        return
    
    API_KEY = api_key_obj.key
    BASE_URL = "http://127.0.0.1:8000"
    
    print(f"使用 API Key: {API_KEY[:20]}...")
    
    # 1. 测试获取服务器列表
    print("\n=== 测试获取服务器列表 ===")
    response = requests.get(
        f"{BASE_URL}/api/external/servers/",
        headers={"X-API-Key": API_KEY}
    )
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"响应: {data}")
    
    # 2. 测试基线检查
    print("\n=== 测试基线检查 ===")
    data = json.dumps({"server_id": 1})
    encrypted_data = encrypt_password(data)
    
    response = requests.post(
        f"{BASE_URL}/api/external/check/",
        headers={
            "X-API-Key": API_KEY,
            "Content-Type": "application/json"
        },
        json={"data": encrypted_data},
        timeout=60
    )
    
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"响应: {result}")
        
        # 如果有加密数据，解密查看
        if result.get('data'):
            decrypted = decrypt_password(result['data'])
            print(f"\n解密后的检查结果:\n{json.dumps(json.loads(decrypted), indent=2, ensure_ascii=False)}")
    else:
        print(f"错误: {response.text}")

if __name__ == '__main__':
    test_external_api()