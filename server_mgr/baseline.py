"""
服务器安全基线检查模块
"""
from .collector import ServerCollector


class BaselineChecker:
    """基线检查器"""
    
    def __init__(self, server):
        self.server = server
        self.collector = ServerCollector(server)
        self.results = []
    
    def check_all(self):
        """执行所有检查项"""
        if not self.collector.connect():
            return [{
                'check_item': 'connection',
                'is_pass': False,
                'detail': f'无法连接服务器 {self.server.ip_address}'
            }]
        
        try:
            # 执行各项检查
            self.check_root_password()
            self.check_ssh_password_auth()
            self.check_ssh_root_login()
            self.check_firewall_status()
            self.check_common_ports()
            
        finally:
            self.collector.close()
        
        return self.results
    
    def check_root_password(self):
        """检查 root 是否设置了密码"""
        try:
            # 检查 /etc/passwd 中 root 的 shell 不是 nologin
            cmd = "cat /etc/passwd | grep '^root:' | cut -d: -f7"
            result = self.collector.execute_command(cmd)
            
            if result and 'nologin' not in result:
                self.results.append({
                    'check_item': 'root_password',
                    'is_pass': True,
                    'detail': 'root 账户已启用'
                })
            else:
                self.results.append({
                    'check_item': 'root_password',
                    'is_pass': False,
                    'detail': 'root 账户未启用或禁止登录'
                })
        except Exception as e:
            self.results.append({
                'check_item': 'root_password',
                'is_pass': False,
                'detail': f'检查失败: {str(e)}'
            })
    
    def check_ssh_password_auth(self):
        """检查 SSH 密码认证是否开启"""
        try:
            cmd = "grep -i '^PasswordAuthentication' /etc/ssh/sshd_config | awk '{print $2}' | head -1"
            result = self.collector.execute_command(cmd)
            
            if result and result.lower() == 'yes':
                self.results.append({
                    'check_item': 'ssh_password_auth',
                    'is_pass': False,
                    'detail': 'SSH 密码认证已开启，建议使用密钥认证'
                })
            else:
                self.results.append({
                    'check_item': 'ssh_password_auth',
                    'is_pass': True,
                    'detail': 'SSH 密码认证已关闭'
                })
        except Exception as e:
            self.results.append({
                'check_item': 'ssh_password_auth',
                'is_pass': False,
                'detail': f'检查失败: {str(e)}'
            })
    
    def check_ssh_root_login(self):
        """检查 SSH root 登录是否允许"""
        try:
            cmd = "grep -i '^PermitRootLogin' /etc/ssh/sshd_config | awk '{print $2}' | head -1"
            result = self.collector.execute_command(cmd)
            
            if result and result.lower() == 'yes':
                self.results.append({
                    'check_item': 'ssh_root_login',
                    'is_pass': False,
                    'detail': '允许 root 直接 SSH 登录，存在安全风险'
                })
            else:
                self.results.append({
                    'check_item': 'ssh_root_login',
                    'is_pass': True,
                    'detail': 'root 直接 SSH 登录已禁用'
                })
        except Exception as e:
            self.results.append({
                'check_item': 'ssh_root_login',
                'is_pass': False,
                'detail': f'检查失败: {str(e)}'
            })
    
    def check_firewall_status(self):
        """检查防火墙状态"""
        try:
            # 检查 iptables 是否有规则
            cmd = "iptables -L -n 2>/dev/null | grep -c 'Chain' || echo '0'"
            result = self.collector.execute_command(cmd)
            
            if result and int(result) > 0:
                self.results.append({
                    'check_item': 'firewall_status',
                    'is_pass': True,
                    'detail': 'iptables 防火墙已配置'
                })
            else:
                self.results.append({
                    'check_item': 'firewall_status',
                    'is_pass': False,
                    'detail': '防火墙未配置'
                })
        except Exception:
            self.results.append({
                'check_item': 'firewall_status',
                'is_pass': False,
                'detail': '防火墙状态检查失败'
            })
    
    def check_common_ports(self):
        """检查常见危险端口"""
        dangerous_ports = [23, 161, 513, 514, 2049]
        open_ports = []
        
        for port in dangerous_ports:
            cmd = f"netstat -tln 2>/dev/null | grep -q ':{port} ' && echo 'open' || echo 'closed'"
            result = self.collector.execute_command(cmd)
            if result and 'open' in result:
                open_ports.append(str(port))
        
        if open_ports:
            self.results.append({
                'check_item': 'dangerous_ports',
                'is_pass': False,
                'detail': f'危险端口已开放: {", ".join(open_ports)}'
            })
        else:
            self.results.append({
                'check_item': 'dangerous_ports',
                'is_pass': True,
                'detail': '未发现危险端口开放'
            })