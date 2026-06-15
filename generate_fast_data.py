"""
快速生成测试数据（直接运行）
python generate_fast_data.py
"""
import os
import django
import random
from datetime import datetime, timedelta

# 设置 Django 环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from server_mgr.models import Server, Metric

def generate_fast_data():
    servers = Server.objects.filter(status='active')
    if not servers.exists():
        print("❌ 没有找到服务器，请先添加")
        return
    
    days = 60
    interval_seconds = 5
    records_per_day = 24 * 3600 // interval_seconds  # 17280条/天
    total_per_server = days * records_per_day  # 1,036,800条/服务器
    
    print(f"📊 将生成 {total_per_server:,} 条/服务器，共 {servers.count()} 台")
    
    for server in servers:
        print(f"\n📡 生成 {server.hostname} 的数据...")
        
        # 批量生成
        batch = []
        batch_size = 10000
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        current = start_date
        count = 0
        
        while current <= end_date:
            # 模拟数据
            hour = current.hour
            if 9 <= hour <= 18:
                cpu = random.uniform(30, 80)
                mem = random.uniform(40, 75)
            else:
                cpu = random.uniform(5, 40)
                mem = random.uniform(20, 50)
            
            # 偶尔高峰
            if random.random() < 0.005:
                cpu = random.uniform(90, 100)
            
            batch.append(Metric(
                server=server,
                cpu_usage_percent=round(cpu, 2),
                memory_usage_percent=round(mem, 2),
                collect_time=current
            ))
            count += 1
            current += timedelta(seconds=interval_seconds)
            
            # 批量插入
            if len(batch) >= batch_size:
                Metric.objects.bulk_create(batch, ignore_conflicts=True)
                print(f"  已生成 {count:,} / {total_per_server:,}")
                batch = []
        
        # 插入剩余
        if batch:
            Metric.objects.bulk_create(batch, ignore_conflicts=True)
        
        print(f"✅ {server.hostname} 完成: {count:,} 条")

if __name__ == '__main__':
    generate_fast_data()
    print("\n🎉 数据生成完成！")