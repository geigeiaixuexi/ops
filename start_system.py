#!/usr/bin/env python
"""
运维管理系统一键启动脚本
自动检查并启动 Redis、Celery Worker、Celery Beat、Django
"""

import os
import sys
import subprocess
import time
import socket
import signal
import atexit

# 配置
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_PYTHON = os.path.join(PROJECT_DIR, 'venv', 'Scripts', 'python.exe')
VENV_CELERY = os.path.join(PROJECT_DIR, 'venv', 'Scripts', 'celery.exe')

# 存储子进程
processes = []


def print_banner():
    """打印启动横幅"""
    banner = """
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║           运维管理系统 - 一键启动脚本                        ║
    ║           Operation Management System                       ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_status(service, status, message=""):
    """打印服务状态"""
    status_icon = "✅" if status else "❌"
    status_text = "运行中" if status else "未运行"
    print(f"  {status_icon} {service:<20} {status_text:<10} {message}")


def check_redis():
    """检查 Redis 是否运行"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((REDIS_HOST, REDIS_PORT))
        sock.close()
        return result == 0
    except Exception:
        return False


def start_redis():
    """启动 Redis"""
    print("\n📦 正在启动 Redis...")
    try:
        # Windows 下启动 Redis
        subprocess.Popen(
            ["redis-server"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=True
        )
        time.sleep(2)
        if check_redis():
            print("   ✅ Redis 启动成功")
            return True
        else:
            print("   ❌ Redis 启动失败，请手动启动 Redis")
            return False
    except FileNotFoundError:
        print("   ❌ 未找到 redis-server，请确保 Redis 已安装")
        print("      提示: 可以使用 Memurai 或 Docker 安装 Redis")
        return False


def check_celery_worker():
    """检查 Celery Worker 是否运行"""
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


def start_celery_worker():
    """启动 Celery Worker"""
    print("\n🔄 正在启动 Celery Worker...")
    try:
        proc = subprocess.Popen(
            [VENV_CELERY, '-A', 'myproject', 'worker', '-l', 'info', '--pool=eventlet'],
            cwd=PROJECT_DIR,
            creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == 'win32' else 0
        )
        processes.append(('Celery Worker', proc))
        time.sleep(2)
        print("   ✅ Celery Worker 已启动（新窗口）")
        return True
    except Exception as e:
        print(f"   ❌ Celery Worker 启动失败: {e}")
        return False


def start_celery_beat():
    """启动 Celery Beat"""
    print("\n⏰ 正在启动 Celery Beat...")
    try:
        proc = subprocess.Popen(
            [VENV_CELERY, '-A', 'myproject', 'beat', '-l', 'info'],
            cwd=PROJECT_DIR,
            creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == 'win32' else 0
        )
        processes.append(('Celery Beat', proc))
        time.sleep(2)
        print("   ✅ Celery Beat 已启动（新窗口）")
        return True
    except Exception as e:
        print(f"   ❌ Celery Beat 启动失败: {e}")
        return False


def start_django():
    """启动 Django"""
    print("\n🌐 正在启动 Django...")
    try:
        proc = subprocess.Popen(
            [VENV_PYTHON, 'manage.py', 'runserver', '0.0.0.0:8000'],
            cwd=PROJECT_DIR
        )
        processes.append(('Django', proc))
        time.sleep(3)
        print("   ✅ Django 启动成功")
        return True
    except Exception as e:
        print(f"   ❌ Django 启动失败: {e}")
        return False


def check_mysql():
    """检查 MySQL 是否运行"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(('127.0.0.1', 3306))
        sock.close()
        return result == 0
    except Exception:
        return False


def cleanup():
    """清理子进程"""
    print("\n\n🛑 正在停止所有服务...")
    for name, proc in processes:
        try:
            proc.terminate()
            print(f"   ✅ 已停止 {name}")
        except:
            pass
    print("   所有服务已停止")


def main():
    """主函数"""
    print_banner()
    
    # 检查 Python 环境
    print("🔍 检查环境...")
    print_status("Python 环境", True, f"虚拟环境: {VENV_PYTHON}")
    
    # 检查 MySQL
    mysql_ok = check_mysql()
    print_status("MySQL", mysql_ok, "端口 3306" if mysql_ok else "请确保 MySQL 已启动")
    if not mysql_ok:
        print("\n⚠️  警告: MySQL 未运行，请手动启动 MySQL 服务")
        print("   启动命令: net start MySQL80  (Windows)")
    
    # 检查并启动 Redis
    redis_ok = check_redis()
    print_status("Redis", redis_ok, f"端口 {REDIS_PORT}" if redis_ok else "")
    
    if not redis_ok:
        print("   Redis 未运行，正在尝试启动...")
        redis_ok = start_redis()
    
    # 启动 Celery Worker
    celery_worker_ok = start_celery_worker()
    
    # 启动 Celery Beat
    celery_beat_ok = start_celery_beat()
    
    # 启动 Django
    django_ok = start_django()
    
    # 打印最终状态
    print("\n" + "=" * 60)
    print("📊 服务状态汇总")
    print("=" * 60)
    print_status("MySQL", mysql_ok, "需要手动启动" if not mysql_ok else "")
    print_status("Redis", redis_ok, "")
    print_status("Celery Worker", celery_worker_ok, "采集任务执行器")
    print_status("Celery Beat", celery_beat_ok, "定时任务调度器")
    print_status("Django", django_ok, "Web 服务")
    
    if not mysql_ok or not redis_ok:
        print("\n⚠️  部分服务未启动，请检查后重新运行")
    
    print("\n" + "=" * 60)
    print("✅ 系统启动完成！")
    print("   访问地址: http://127.0.0.1:8000")
    print("   按 Ctrl+C 停止所有服务")
    print("=" * 60)
    
    # 注册退出清理
    atexit.register(cleanup)
    
    # 等待信号
    try:
        signal.pause() if hasattr(signal, 'pause') else time.sleep(999999)
    except KeyboardInterrupt:
        print("\n\n👋 收到停止信号，正在关闭...")


if __name__ == '__main__':
    main()