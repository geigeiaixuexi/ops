"""
服务器信息采集器
通过 SSH 远程执行命令获取硬件信息
"""
import paramiko
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)


class ServerCollector:
    """服务器信息采集器"""
    
    def __init__(self, server):
        """
        初始化采集器
        server: Server 模型实例
        """
        self.server = server
        self.ssh_client = None
    
    def connect(self):
        """建立 SSH 连接"""
        try:
            self.ssh_client = paramiko.SSHClient()
            # 自动添加主机密钥（生产环境应该验证）
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # 解密密码（Django 加密的密码需要验证方式，这里直接使用）
            # 注意：paramiko 需要明文密码，我们需要存储明文或使用密钥
            # 临时方案：从数据库获取明文（需要修改存储方式）
            password = self._get_password()
            
            self.ssh_client.connect(
                hostname=self.server.ip_address,
                port=self.server.ssh_port,
                username=self.server.ssh_user,
                password=password,
                timeout=10
            )
            return True
        except Exception as e:
            logger.error(f"连接服务器 {self.server.ip_address} 失败: {e}")
            return False
    
    def _get_password(self):
        """获取明文密码（自动解密）"""
        return self.server.get_password()
    
    def execute_command(self, command, timeout=5):
        """执行命令并返回输出（设置较短超时）"""
        try:
            stdin, stdout, stderr = self.ssh_client.exec_command(command, timeout=timeout)
            output = stdout.read().decode('utf-8').strip()
            return output
        except Exception as e:
            logger.error(f"执行命令失败: {e}")
            return None
    
    def close(self):
        """关闭连接"""
        if self.ssh_client:
            self.ssh_client.close()
    
    def get_cpu_cores(self):
        """获取 CPU 核心数"""
        commands = [
            "nproc",
            "cat /proc/cpuinfo | grep 'processor' | wc -l",
            "lscpu | grep '^CPU(s):' | awk '{print $2}'"
        ]
        
        for cmd in commands:
            result = self.execute_command(cmd)
            if result and result.isdigit():
                return int(result)
        return None
    
    def get_os_version(self):
        """获取操作系统版本"""
        commands = [
            "cat /etc/os-release | grep 'PRETTY_NAME' | cut -d'=' -f2 | tr -d '\"'",
            "cat /etc/debian_version | head -1",
            "uname -a"
        ]
        
        for cmd in commands:
            result = self.execute_command(cmd)
            if result and result.strip():
                return result[:200]  # 限制长度
        return "Unknown"
    
    def get_memory_total(self):
        """获取总内存（GB）"""
        cmd = "cat /proc/meminfo | grep 'MemTotal' | awk '{print $2}'"
        result = self.execute_command(cmd)
        if result and result.isdigit():
            memory_kb = int(result)
            memory_gb = Decimal(memory_kb / 1024 / 1024).quantize(Decimal('0.01'))
            return memory_gb
        return None
    
    def get_disk_total(self):
        """获取磁盘总容量（GB）"""
        cmd = "df / | tail -1 | awk '{print $2}'"
        result = self.execute_command(cmd)
        if result and result.isdigit():
            disk_kb = int(result)
            disk_gb = Decimal(disk_kb / 1024 / 1024).quantize(Decimal('0.01'))
            return disk_gb
        return None
    
    def collect_server_info(self):
        """采集所有服务器信息"""
        if not self.connect():
            return False
        
        try:
            # 采集各项数据
            self.server.cpu_cores = self.get_cpu_cores()
            self.server.os_version = self.get_os_version()
            self.server.memory_total_gb = self.get_memory_total()
            self.server.disk_total_gb = self.get_disk_total()
            
            # 保存到数据库
            self.server.save(update_fields=['cpu_cores', 'os_version', 
                                            'memory_total_gb', 'disk_total_gb',
                                            'updated_at'])
            
            logger.info(f"成功采集服务器 {self.server.hostname} 的信息")
            return True
        except Exception as e:
            logger.error(f"采集服务器信息失败: {e}")
            return False
        finally:
            self.close()