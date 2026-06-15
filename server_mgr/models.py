from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from .utils.crypto import encrypt_password, decrypt_password

class Server(models.Model):
    """服务器信息表"""
    
    STATUS_CHOICES = [
        ('active', '启用'),
        ('inactive', '停用'),
        ('maintenance', '维护中'),
    ]
    
    id = models.AutoField(primary_key=True, verbose_name='服务器ID')
    
    hostname = models.CharField(max_length=100, verbose_name='主机名')
    ip_address = models.GenericIPAddressField(unique=True, verbose_name='IP地址')
    ssh_port = models.IntegerField(default=22, verbose_name='SSH端口')
    ssh_user = models.CharField(max_length=50, default='root', verbose_name='SSH用户名')
    ssh_password = models.CharField(max_length=500, verbose_name='SSH密码')  # 加长字段，AES加密后更长
    
    os_version = models.CharField(max_length=200, blank=True, null=True, verbose_name='操作系统版本')
    cpu_cores = models.IntegerField(blank=True, null=True, verbose_name='CPU核心数')
    memory_total_gb = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name='内存总容量(GB)')
    disk_total_gb = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name='磁盘总容量(GB)')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name='服务器状态')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'servers'
        verbose_name = '服务器信息'
        verbose_name_plural = '服务器信息'
        indexes = [
            models.Index(fields=['ip_address'], name='idx_ip'),
            models.Index(fields=['status'], name='idx_status'),
        ]
    
    def set_password(self, raw_password):
        """加密存储密码"""
        self.ssh_password = encrypt_password(raw_password)
    
    def get_password(self):
        """解密获取明文密码"""
        return decrypt_password(self.ssh_password)
    
    def check_password(self, raw_password):
        """验证密码是否正确"""
        return self.get_password() == raw_password
    
    def __str__(self):
        return f"{self.hostname} ({self.ip_address})"


class BaselineResult(models.Model):
    """基线检查结果表"""
    
    id = models.AutoField(primary_key=True, verbose_name='基线结果ID')
    server = models.ForeignKey(Server, on_delete=models.CASCADE, related_name='baselines', verbose_name='服务器')
    
    check_item = models.CharField(max_length=100, verbose_name='检查项')
    is_pass = models.BooleanField(verbose_name='是否通过')
    detail = models.TextField(blank=True, verbose_name='详情描述')
    
    checked_at = models.DateTimeField(auto_now_add=True, verbose_name='检查时间')
    
    class Meta:
        db_table = 'baseline_results'
        verbose_name = '基线检查结果'
        verbose_name_plural = '基线检查结果'
        indexes = [
            models.Index(fields=['server', 'checked_at'], name='idx_baseline_server_time'),
        ]
    
    def __str__(self):
        return f"{self.server.hostname} - {self.check_item} - {'通过' if self.is_pass else '不通过'}"


class Metric(models.Model):
    """监控指标表（5秒粒度）"""
    
    id = models.BigAutoField(primary_key=True, verbose_name='指标ID')
    server = models.ForeignKey(Server, on_delete=models.CASCADE, related_name='metrics', verbose_name='服务器')
    
    cpu_usage_percent = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='CPU使用率(%)')
    memory_usage_percent = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='内存使用率(%)')
    
    collect_time = models.DateTimeField(verbose_name='采集时间')
    
    class Meta:
        db_table = 'metrics'
        verbose_name = '监控指标'
        verbose_name_plural = '监控指标'
        indexes = [
            models.Index(fields=['server', 'collect_time'], name='idx_metric_server_time'),
        ]
        unique_together = [['server', 'collect_time']]
    
    def __str__(self):
        return f"{self.server.hostname} - CPU:{self.cpu_usage_percent}% MEM:{self.memory_usage_percent}% @ {self.collect_time}"


class Alert(models.Model):
    """告警记录表"""
    
    SEVERITY_CHOICES = [
        ('warning', '警告'),
        ('critical', '严重'),
    ]
    
    id = models.AutoField(primary_key=True, verbose_name='告警ID')
    server = models.ForeignKey(Server, on_delete=models.CASCADE, related_name='alerts', verbose_name='服务器')
    
    alert_type = models.CharField(max_length=50, verbose_name='告警类型')
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='warning', verbose_name='告警级别')
    detail = models.TextField(verbose_name='告警详情')
    
    is_resolved = models.BooleanField(default=False, verbose_name='是否已恢复')
    email_sent = models.BooleanField(default=False, verbose_name='是否已发送邮件')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='告警时间')
    resolved_at = models.DateTimeField(blank=True, null=True, verbose_name='恢复时间')
    
    class Meta:
        db_table = 'alerts'
        verbose_name = '告警记录'
        verbose_name_plural = '告警记录'
        indexes = [
            models.Index(fields=['is_resolved', 'created_at'], name='idx_unresolved'),
            models.Index(fields=['server'], name='idx_server'),
        ]
    
    def __str__(self):
        return f"{self.server.hostname} - {self.alert_type} - {self.severity}"

 
class ApiKey(models.Model):
    """API 密钥表"""
    
    key = models.CharField(max_length=64, unique=True, verbose_name='API密钥')
    name = models.CharField(max_length=100, verbose_name='应用名称')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    last_used = models.DateTimeField(blank=True, null=True, verbose_name='最后使用时间')
    
    class Meta:
        db_table = 'api_keys'
        verbose_name = 'API密钥'
    
    def __str__(self):
        return f"{self.name} ({self.key[:8]}...)"