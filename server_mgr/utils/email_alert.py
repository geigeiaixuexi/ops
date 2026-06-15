"""
邮件告警工具
"""
import logging
from django.core.mail import send_mail
from django.conf import settings
from datetime import datetime

logger = logging.getLogger(__name__)


class EmailAlert:
    """邮件告警发送器"""
    
    # 告警记录（用于防重复）
    _alert_cache = {}
    
    @classmethod
    def send_cpu_alert(cls, server, cpu_usage, threshold=90):
        """发送 CPU 告警邮件"""
        subject = f'[告警] 服务器 {server.hostname} CPU使用率过高'
        message = f"""
        服务器告警通知
        
        服务器名称: {server.hostname}
        服务器IP: {server.ip_address}
        告警类型: CPU 使用率过高
        当前值: {cpu_usage}%
        告警阈值: {threshold}%
        告警时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        
        请及时检查服务器状态！
        """
        return cls._send(subject, message, server.id, 'cpu')
    
    @classmethod
    def send_memory_alert(cls, server, memory_usage, threshold=85):
        """发送内存告警邮件"""
        subject = f'[告警] 服务器 {server.hostname} 内存使用率过高'
        message = f"""
        服务器告警通知
        
        服务器名称: {server.hostname}
        服务器IP: {server.ip_address}
        告警类型: 内存使用率过高
        当前值: {memory_usage}%
        告警阈值: {threshold}%
        告警时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        
        请及时检查服务器状态！
        """
        return cls._send(subject, message, server.id, 'memory')
    
    @classmethod
    def send_baseline_alert(cls, server, failed_items):
        """发送基线检查失败告警"""
        items_list = '\n'.join([f"  - {item}" for item in failed_items])
        subject = f'[告警] 服务器 {server.hostname} 基线检查不通过'
        message = f"""
        基线检查告警通知
        
        服务器名称: {server.hostname}
        服务器IP: {server.ip_address}
        告警类型: 基线检查失败
        不通过项数: {len(failed_items)}
        不通过项目:
        {items_list}
        
        检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        
        请及时修复安全问题！
        """
        return cls._send(subject, message, server.id, 'baseline')
    
    @classmethod
    def send_recovery_alert(cls, server, alert_type, current_value):
        """发送恢复通知邮件"""
        type_names = {'cpu': 'CPU', 'memory': '内存'}
        type_name = type_names.get(alert_type, alert_type)
        
        subject = f'[恢复] 服务器 {server.hostname} {type_name}使用率已恢复正常'
        message = f"""
        服务器恢复通知
        
        服务器名称: {server.hostname}
        服务器IP: {server.ip_address}
        告警类型: {type_name}使用率
        当前值: {current_value}%
        恢复时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        
        服务器已恢复正常状态。
        """
        return cls._send(subject, message, server.id, alert_type, is_recovery=True)
    
    @classmethod
    def _send(cls, subject, message, server_id, alert_type, is_recovery=False):
        """发送邮件（带防重复逻辑）"""
        # 检查是否需要发送（防重复）
        cache_key = f"{server_id}_{alert_type}"
        
        if not is_recovery:
            # 检查是否已发送过未恢复的告警
            if cache_key in cls._alert_cache:
                last_time = cls._alert_cache[cache_key]
                # 5分钟内不重复发送
                if (datetime.now() - last_time).seconds < 300:
                    logger.info(f"跳过重复告警: {cache_key}")
                    return False
        
        try:
            # 发送邮件
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=settings.ADMIN_EMAILS,
                fail_silently=False,
            )
            
            # 更新缓存
            if is_recovery:
                # 恢复时清除缓存
                cls._alert_cache.pop(cache_key, None)
            else:
                cls._alert_cache[cache_key] = datetime.now()
            
            logger.info(f"告警邮件发送成功: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"邮件发送失败: {e}")
            return False
    
    @classmethod
    def clear_alert(cls, server_id, alert_type):
        """清除告警记录（用于恢复）"""
        cache_key = f"{server_id}_{alert_type}"
        cls._alert_cache.pop(cache_key, None)