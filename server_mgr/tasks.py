"""
Celery 定时任务
"""
import logging
from celery import shared_task
from datetime import datetime
from decimal import Decimal

from .models import Server, Metric
from .collector import ServerCollector

from .utils.email_alert import EmailAlert
from .models import Alert

logger = logging.getLogger(__name__)


def collect_server_metrics(server):
    """
    采集单台服务器的 CPU 和内存使用率
    返回: (cpu_usage_percent, memory_usage_percent)
    """
    collector = ServerCollector(server)
    
    if not collector.connect():
        print(f"连接失败: {server.hostname}")
        return None, None
    
    try:
        # ========== CPU 使用率 ==========
        cpu_usage = None
        cmd = "top -bn1 | grep '%Cpu' | awk -F 'id,' '{print $1}' | awk '{print $NF}'"
        result = collector.execute_command(cmd)
        if result and result.replace('.', '').replace('-', '').isdigit():
            idle = float(result)
            cpu_usage = round(100 - idle, 2)
            cpu_usage = max(0, min(100, cpu_usage))
            print(f"CPU采集成功: {cpu_usage}%")
        
        # 备选 CPU 命令
        if cpu_usage is None:
            cmd = "mpstat 1 1 | tail -1 | awk '{print $NF}'"
            result = collector.execute_command(cmd)
            if result and result.replace('.', '').isdigit():
                idle = float(result)
                cpu_usage = round(100 - idle, 2)
                print(f"CPU采集成功(mpstat): {cpu_usage}%")
        
        # ========== 内存使用率 ==========
        mem_usage = None
        
        # 使用测试成功的命令
        cmd = "LC_ALL=C free | awk 'NR==2{printf \"%.2f\", $3/$2 * 100}'"
        result = collector.execute_command(cmd)
        print(f"内存命令原始返回: '{result}'")
        
        if result:
            try:
                mem_usage = float(result)
                mem_usage = round(mem_usage, 2)
                mem_usage = max(0, min(100, mem_usage))
                print(f"内存采集成功: {mem_usage}%")
            except ValueError as e:
                print(f"内存转换失败: {e}, 原始值: '{result}'")
        
        # 备选内存命令
        if mem_usage is None:
            cmd = "awk '/MemTotal/{total=$2} /MemAvailable/{avail=$2} END{printf \"%.2f\", (total-avail)/total*100}' /proc/meminfo"
            result = collector.execute_command(cmd)
            if result:
                try:
                    mem_usage = float(result)
                    mem_usage = round(mem_usage, 2)
                    print(f"内存采集成功(/proc): {mem_usage}%")
                except ValueError:
                    pass
        
        print(f"✅ 最终结果: CPU={cpu_usage}%, MEM={mem_usage}%")
        return cpu_usage, mem_usage
        
    except Exception as e:
        print(f"❌ 采集异常: {e}")
        import traceback
        traceback.print_exc()
        return None, None
    finally:
        collector.close()

def check_and_alert(server, cpu_usage, mem_usage, current_time):
    """检查并发送告警"""
    cpu_threshold = 90
    mem_threshold = 85
    
    # 获取最近一次告警记录
    recent_alerts = Alert.objects.filter(
        server=server,
        is_resolved=False
    )
    
    # CPU 告警检测
    if cpu_usage is not None and cpu_usage > cpu_threshold:
        # 检查是否已经告警过
        if not recent_alerts.filter(alert_type='cpu_high').exists():
            # 创建告警记录
            Alert.objects.create(
                server=server,
                alert_type='cpu_high',
                severity='critical',
                detail=f'CPU使用率超过阈值: {cpu_usage}% > {cpu_threshold}%',
                email_sent=True
            )
            # 发送邮件
            EmailAlert.send_cpu_alert(server, cpu_usage, cpu_threshold)
    else:
        # CPU 恢复正常，清除告警
        cpu_alerts = recent_alerts.filter(alert_type='cpu_high')
        if cpu_alerts.exists():
            cpu_alerts.update(is_resolved=True, resolved_at=current_time)
            # 发送恢复通知
            EmailAlert.send_recovery_alert(server, 'cpu', cpu_usage)
    
    # 内存告警检测
    if mem_usage is not None and mem_usage > mem_threshold:
        if not recent_alerts.filter(alert_type='memory_high').exists():
            Alert.objects.create(
                server=server,
                alert_type='memory_high',
                severity='warning',
                detail=f'内存使用率超过阈值: {mem_usage}% > {mem_threshold}%',
                email_sent=True
            )
            EmailAlert.send_memory_alert(server, mem_usage, mem_threshold)
    else:
        mem_alerts = recent_alerts.filter(alert_type='memory_high')
        if mem_alerts.exists():
            mem_alerts.update(is_resolved=True, resolved_at=current_time)
            EmailAlert.send_recovery_alert(server, 'memory', mem_usage)

@shared_task
def collect_metrics_task():
    """采集所有服务器的 CPU/内存使用率，并检测告警"""
    servers = Server.objects.filter(status='active')
    current_time = datetime.now()
    
    success_count = 0
    fail_count = 0
    
    print(f"\n{'='*50}")
    print(f"开始采集任务 - {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    for server in servers:
        try:
            cpu_usage, mem_usage = collect_server_metrics(server)
            
            if cpu_usage is not None or mem_usage is not None:
                # 保存数据
                Metric.objects.create(
                    server=server,
                    cpu_usage_percent=Decimal(str(cpu_usage)) if cpu_usage is not None else Decimal('0'),
                    memory_usage_percent=Decimal(str(mem_usage)) if mem_usage is not None else Decimal('0'),
                    collect_time=current_time
                )
                success_count += 1
                print(f"  ✅ 保存成功: CPU={cpu_usage}%, MEM={mem_usage}%")
                
                # 检测告警
                check_and_alert(server, cpu_usage, mem_usage, current_time)
            else:
                fail_count += 1
                print(f"  ❌ 采集失败: 无法获取数据")
                
        except Exception as e:
            fail_count += 1
            print(f"  ❌ 异常: {e}")
    
    print(f"\n任务完成: 成功={success_count}, 失败={fail_count}")
    
    return {
        'success': success_count,
        'fail': fail_count,
        'time': current_time.strftime('%Y-%m-%d %H:%M:%S')
    }