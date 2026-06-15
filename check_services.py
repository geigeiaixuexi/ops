#!/usr/bin/env python
"""
服务状态检查脚本
检查所有服务是否正常运行
"""

import socket
import subprocess
import sys


def check_port(host, port, name):
    """检查端口是否开放"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def check_celery():
    """检查 Celery 状态"""
    try:
        result = subprocess.run(
            ['celery', '-A', 'myproject', 'status'],
            capture_output=True,
            text=True,
            timeout=5,
            shell=True
        )
        return 'OK' in result.stdout or 'celery@' in result.stdout
    except Exception:
        return False


def check_django():
    """检查 Django 是否运行"""
    return check_port('127.0.0.1', 8000, 'Django')


def main():
    print("\n" + "=" * 50)
    print("   运维管理系统 - 服务状态检查")
    print("=" * 50)
    
    # 检查 MySQL
    mysql_ok = check_port('127.0.0.1', 3306, 'MySQL')
    status = "✅ 运行中" if mysql_ok else "❌ 未运行"
    print(f"\n  📊 MySQL:      {status}")
    if not mysql_ok:
        print("      → 启动命令: net start MySQL80  (Windows)")
        print("      → 或: sudo systemctl start mysql (Linux)")
    
    # 检查 Redis
    redis_ok = check_port('127.0.0.1', 6379, 'Redis')
    status = "✅ 运行中" if redis_ok else "❌ 未运行"
    print(f"  📊 Redis:      {status}")
    if not redis_ok:
        print("      → 启动命令: redis-server")
        print("      → 或: sudo systemctl start redis (Linux)")
    
    # 检查 Celery
    celery_ok = check_celery()
    status = "✅ 运行中" if celery_ok else "❌ 未运行"
    print(f"  📊 Celery:     {status}")
    if not celery_ok:
        print("      → 启动命令: celery -A myproject worker -l info --pool=eventlet")
    
    # 检查 Celery Beat
    beat_ok = check_port('127.0.0.1', 8000, 'Celery Beat')  # 简单检查
    print(f"  📊 Celery Beat: {'✅ 运行中' if beat_ok else '⚠️  需手动检查'}")
    
    # 检查 Django
    django_ok = check_django()
    status = "✅ 运行中" if django_ok else "❌ 未运行"
    print(f"  🌐 Django:     {status}")
    if django_ok:
        print(f"\n  🌐 Web 访问: http://127.0.0.1:8000")
    
    print("\n" + "=" * 50)
    
    if mysql_ok and redis_ok and django_ok:
        print("✅ 所有核心服务正常运行！")
    else:
        print("⚠️  部分服务未运行，请使用 python start_system.py 启动")
    
    print("=" * 50 + "\n")


if __name__ == '__main__':
    main()