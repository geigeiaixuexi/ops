from django.db import models
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Q
from django.db.models import Avg, Max, Min, Count
from datetime import datetime, timedelta
from django.core.paginator import Paginator
from .models import Server, Metric, BaselineResult, Alert  # 确保导入了 Metric
from .collector import ServerCollector
from .baseline import BaselineChecker
from .models import ApiKey
from .utils.crypto import decrypt_password, encrypt_password
from .utils.email_alert import EmailAlert

import json
import secrets

@csrf_exempt
def index(request):
    """首页 - 服务器管理界面"""
    return render(request, 'index.html')

@csrf_exempt
def server_list(request):
    """
    服务器列表接口
    GET: 获取服务器列表（支持关键词搜索）
    POST: 添加新服务器
    """
    if request.method == 'GET':
        # 获取搜索关键词
        keyword = request.GET.get('keyword', '')
        
        # 查询服务器
        servers = Server.objects.all().order_by('-created_at')
        
        if keyword:
            servers = servers.filter(
                Q(hostname__icontains=keyword) |
                Q(ip_address__icontains=keyword)
            )
        
        # 转换为 JSON
        data = []
        for server in servers:
            data.append({
                'id': server.id,
                'hostname': server.hostname,
                'ip_address': server.ip_address,
                'ssh_port': server.ssh_port,
                'ssh_user': server.ssh_user,
                'os_version': server.os_version if server.os_version else '未采集',
                'cpu_cores': server.cpu_cores if server.cpu_cores else '未采集',
                'memory_total_gb': str(server.memory_total_gb) if server.memory_total_gb else '未采集',
                'disk_total_gb': str(server.disk_total_gb) if server.disk_total_gb else '未采集',
                'status': server.status,
                'created_at': server.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            })
        
        return JsonResponse({
            'code': 200,
            'message': 'success',
            'data': data
        })
    
    elif request.method == 'POST':
        try:
            body = json.loads(request.body)
            
            # 验证必填字段
            if not body.get('hostname'):
                return JsonResponse({'code': 400, 'message': '主机名不能为空'}, status=400)
            if not body.get('ip_address'):
                return JsonResponse({'code': 400, 'message': 'IP地址不能为空'}, status=400)
            if not body.get('ssh_password'):
                return JsonResponse({'code': 400, 'message': '密码不能为空'}, status=400)
            
            # 检查 IP 是否已存在
            if Server.objects.filter(ip_address=body.get('ip_address')).exists():
                return JsonResponse({'code': 400, 'message': '该IP地址已存在'}, status=400)
            
            # 创建服务器
            server = Server(
                hostname=body.get('hostname'),
                ip_address=body.get('ip_address'),
                ssh_port=body.get('ssh_port', 22),
                ssh_user=body.get('ssh_user', 'root'),
            )
            server.set_password(body.get('ssh_password'))
            server.save()
            
            return JsonResponse({
                'code': 200,
                'message': '添加成功',
                'data': {'id': server.id}
            })
        except json.JSONDecodeError:
            return JsonResponse({'code': 400, 'message': '无效的JSON数据'}, status=400)
        except Exception as e:
            return JsonResponse({'code': 500, 'message': f'添加失败: {str(e)}'}, status=500)

@csrf_exempt
def server_detail(request, server_id):
    """服务器详情/删除接口"""
    try:
        server = Server.objects.get(id=server_id)
        
        if request.method == 'GET':
            return JsonResponse({
                'code': 200,
                'data': {
                    'id': server.id,
                    'hostname': server.hostname,
                    'ip_address': server.ip_address,
                    'ssh_port': server.ssh_port,
                    'ssh_user': server.ssh_user,
                    'os_version': server.os_version,
                    'cpu_cores': server.cpu_cores,
                    'memory_total_gb': str(server.memory_total_gb) if server.memory_total_gb else None,
                    'disk_total_gb': str(server.disk_total_gb) if server.disk_total_gb else None,
                    'status': server.status,
                }
            })
        
        elif request.method == 'DELETE':
            hostname = server.hostname
            server.delete()
            return JsonResponse({'code': 200, 'message': f'服务器 {hostname} 已删除'})
        
        elif request.method == 'PUT':
            try:
                body = json.loads(request.body)
                server.hostname = body.get('hostname', server.hostname)
                server.ip_address = body.get('ip_address', server.ip_address)
                server.ssh_port = body.get('ssh_port', server.ssh_port)
                server.ssh_user = body.get('ssh_user', server.ssh_user)
                if body.get('ssh_password'):
                    server.set_password(body.get('ssh_password'))
                server.save()
                return JsonResponse({'code': 200, 'message': '更新成功'})
            except Exception as e:
                return JsonResponse({'code': 500, 'message': f'更新失败: {str(e)}'}, status=500)
            
    except Server.DoesNotExist:
        return JsonResponse({'code': 404, 'message': '服务器不存在'}, status=404)

@csrf_exempt
def refresh_server_info(request, server_id):
    """
    刷新服务器硬件信息（要求5：SSH采集）
    """
    try:
        server = Server.objects.get(id=server_id)
        
        # 创建采集器并执行采集
        collector = ServerCollector(server)
        
        if collector.collect_server_info():
            # 采集成功，返回最新数据
            return JsonResponse({
                'code': 200,
                'message': f'✅ 采集成功！服务器 {server.hostname} 信息已更新',
                'data': {
                    'os_version': server.os_version,
                    'cpu_cores': server.cpu_cores,
                    'memory_total_gb': str(server.memory_total_gb) if server.memory_total_gb else None,
                    'disk_total_gb': str(server.disk_total_gb) if server.disk_total_gb else None,
                }
            })
        else:
            return JsonResponse({
                'code': 500,
                'message': f'❌ 采集失败，无法连接服务器 {server.ip_address}，请检查SSH配置'
            }, status=500)
            
    except Server.DoesNotExist:
        return JsonResponse({'code': 404, 'message': '服务器不存在'}, status=404)
    except Exception as e:
        return JsonResponse({
            'code': 500,
            'message': f'采集异常: {str(e)}'
        }, status=500)
    
@csrf_exempt
def get_metrics(request, server_id):
    """
    获取服务器监控数据（近30天，响应<1秒）
    GET /api/metrics/<server_id>?start=2024-01-01&end=2024-01-31&page=1&page_size=100
    """
    try:
        server = Server.objects.get(id=server_id)
    except Server.DoesNotExist:
        return JsonResponse({'code': 404, 'message': '服务器不存在'}, status=404)
    
    # 获取参数
    start_date = request.GET.get('start')
    end_date = request.GET.get('end')
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 100))
    
    # 默认查询近30天
    if not end_date:
        end_date = datetime.now()
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    
    if not start_date:
        start_date = end_date - timedelta(days=30)
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
    
    # 查询数据（使用索引优化）
    metrics = Metric.objects.filter(
        server=server,
        collect_time__gte=start_date,
        collect_time__lte=end_date
    ).order_by('collect_time')
    
    # 分页
    paginator = Paginator(metrics, page_size)
    page_data = paginator.get_page(page)
    
    # 构建返回数据
    data = []
    for metric in page_data:
        data.append({
            'id': metric.id,
            'cpu_usage': float(metric.cpu_usage_percent),
            'memory_usage': float(metric.memory_usage_percent),
            'collect_time': metric.collect_time.strftime('%Y-%m-%d %H:%M:%S')
        })
    
    # 统计信息（用于前端图表）

    stats = metrics.aggregate(
        avg_cpu=Avg('cpu_usage_percent'),
        max_cpu=Max('cpu_usage_percent'),
        min_cpu=Min('cpu_usage_percent'),
        avg_mem=Avg('memory_usage_percent'),
        max_mem=Max('memory_usage_percent'),
        min_mem=Min('memory_usage_percent'),
        total_count=models.Count('id')
    )
    
    return JsonResponse({
        'code': 200,
        'data': {
            'server': {
                'id': server.id,
                'hostname': server.hostname,
                'ip_address': server.ip_address
            },
            'time_range': {
                'start': start_date.strftime('%Y-%m-%d %H:%M:%S'),
                'end': end_date.strftime('%Y-%m-%d %H:%M:%S')
            },
            'statistics': {
                'avg_cpu': round(float(stats['avg_cpu'] or 0), 2),
                'max_cpu': round(float(stats['max_cpu'] or 0), 2),
                'min_cpu': round(float(stats['min_cpu'] or 0), 2),
                'avg_memory': round(float(stats['avg_mem'] or 0), 2),
                'max_memory': round(float(stats['max_mem'] or 0), 2),
                'min_memory': round(float(stats['min_mem'] or 0), 2),
                'total_records': stats['total_count']
            },
            'pagination': {
                'current_page': page,
                'page_size': page_size,
                'total_pages': paginator.num_pages,
                'total_records': paginator.count
            },
            'records': data
        }
    })

@csrf_exempt
def get_metrics(request, server_id):
    """获取服务器监控数据（近30天，响应<1秒）"""
    try:
        server = Server.objects.get(id=server_id)
    except Server.DoesNotExist:
        return JsonResponse({'code': 404, 'message': '服务器不存在'}, status=404)
    
    # 获取参数
    days = int(request.GET.get('days', 30))
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 100))
    
    # 计算时间范围
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # 查询数据（使用索引优化）
    metrics = Metric.objects.filter(
        server=server,
        collect_time__gte=start_date,
        collect_time__lte=end_date
    ).order_by('-collect_time')
    
    # 统计信息
    stats = metrics.aggregate(
        avg_cpu=Avg('cpu_usage_percent'),
        max_cpu=Max('cpu_usage_percent'),
        min_cpu=Min('cpu_usage_percent'),
        avg_mem=Avg('memory_usage_percent'),
        max_mem=Max('memory_usage_percent'),
        min_mem=Min('memory_usage_percent'),
        total=Count('id')
    )
    
    # 分页
    paginator = Paginator(metrics, page_size)
    page_data = paginator.get_page(page)
    
    # 构建返回数据
    records = []
    for m in page_data:
        records.append({
            'time': m.collect_time.strftime('%Y-%m-%d %H:%M:%S'),
            'cpu': float(m.cpu_usage_percent),
            'memory': float(m.memory_usage_percent)
        })
    
    return JsonResponse({
        'code': 200,
        'data': {
            'server': {
                'id': server.id,
                'hostname': server.hostname,
                'ip': server.ip_address
            },
            'time_range': {
                'start': start_date.strftime('%Y-%m-%d %H:%M:%S'),
                'end': end_date.strftime('%Y-%m-%d %H:%M:%S'),
                'days': days
            },
            'statistics': {
                'cpu_avg': round(float(stats['avg_cpu'] or 0), 2),
                'cpu_max': round(float(stats['max_cpu'] or 0), 2),
                'cpu_min': round(float(stats['min_cpu'] or 0), 2),
                'memory_avg': round(float(stats['avg_mem'] or 0), 2),
                'memory_max': round(float(stats['max_mem'] or 0), 2),
                'memory_min': round(float(stats['min_mem'] or 0), 2),
                'total_records': stats['total']
            },
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_pages': paginator.num_pages,
                'total_records': paginator.count
            },
            'records': records
        }
    })
    """
    刷新服务器硬件信息（要求5：SSH采集）
    """
    try:
        server = Server.objects.get(id=server_id)
        
        # 创建采集器并执行采集
        collector = ServerCollector(server)
        
        if collector.collect_server_info():
            # 采集成功，返回最新数据
            return JsonResponse({
                'code': 200,
                'message': f'✅ 采集成功！服务器 {server.hostname} 信息已更新',
                'data': {
                    'os_version': server.os_version,
                    'cpu_cores': server.cpu_cores,
                    'memory_total_gb': str(server.memory_total_gb) if server.memory_total_gb else None,
                    'disk_total_gb': str(server.disk_total_gb) if server.disk_total_gb else None,
                }
            })
        else:
            return JsonResponse({
                'code': 500,
                'message': f'❌ 采集失败，无法连接服务器 {server.ip_address}，请检查SSH配置'
            }, status=500)
            
    except Server.DoesNotExist:
        return JsonResponse({'code': 404, 'message': '服务器不存在'}, status=404)
    except Exception as e:
        return JsonResponse({
            'code': 500,
            'message': f'采集异常: {str(e)}'
        }, status=500)
    """刷新服务器硬件信息（后续实现SSH采集）"""
    try:
        server = Server.objects.get(id=server_id)
        # TODO: 后续实现 SSH 采集
        return JsonResponse({
            'code': 200,
            'message': f'SSH采集功能开发中，请稍后实现',
            'data': {
                'cpu_cores': server.cpu_cores,
                'memory_total_gb': str(server.memory_total_gb) if server.memory_total_gb else None,
            }
        })
    except Server.DoesNotExist:
        return JsonResponse({'code': 404, 'message': '服务器不存在'}, status=404)
    
@csrf_exempt
def external_check(request):
    """
    对外 API - 远程执行基线检查
    请求格式: POST /api/external/check
    请求头: X-API-Key: xxx
    请求体: {"server_id": 1}  (AES加密)
    """
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'message': 'Method not allowed'}, status=405)
    
    # 1. 验证 API Key
    api_key = request.headers.get('X-API-Key')
    if not api_key:
        return JsonResponse({'code': 401, 'message': 'Missing API Key'}, status=401)
    
    try:
        api_key_obj = ApiKey.objects.get(key=api_key, is_active=True)
        # 更新最后使用时间
        api_key_obj.last_used = datetime.now()
        api_key_obj.save()
    except ApiKey.DoesNotExist:
        return JsonResponse({'code': 401, 'message': 'Invalid API Key'}, status=401)
    
    # 2. 解密请求体
    try:
        body = json.loads(request.body)
        encrypted_data = body.get('data')
        if not encrypted_data:
            return JsonResponse({'code': 400, 'message': 'Missing encrypted data'}, status=400)
        
        # 解密
        decrypted = decrypt_password(encrypted_data)
        params = json.loads(decrypted)
        server_id = params.get('server_id')
        
        if not server_id:
            return JsonResponse({'code': 400, 'message': 'server_id required'}, status=400)
    except Exception as e:
        return JsonResponse({'code': 400, 'message': f'Decryption failed: {str(e)}'}, status=400)
    
    # 3. 获取服务器
    try:
        server = Server.objects.get(id=server_id, status='active')
    except Server.DoesNotExist:
        return JsonResponse({'code': 404, 'message': 'Server not found'}, status=404)
    
    # 4. 执行基线检查
    try:
        checker = BaselineChecker(server)
        results = checker.check_all()
        
        # 5. 保存检查结果到数据库
        for result in results:
            BaselineResult.objects.create(
                server=server,
                check_item=result['check_item'],
                is_pass=result['is_pass'],
                detail=result['detail']
            )
        
        # 6. 加密返回结果
        response_data = {
            'server_id': server.id,
            'hostname': server.hostname,
            'check_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'results': results,
            'summary': {
                'total': len(results),
                'passed': sum(1 for r in results if r['is_pass']),
                'failed': sum(1 for r in results if not r['is_pass'])
            }
        }
        
        encrypted_response = encrypt_password(json.dumps(response_data))
        
        return JsonResponse({
            'code': 200,
            'message': 'success',
            'data': encrypted_response
        })
        
    except Exception as e:
        return JsonResponse({'code': 500, 'message': f'Check failed: {str(e)}'}, status=500)

@csrf_exempt
def external_get_servers(request):
    """
    对外 API - 获取服务器列表
    """
    if request.method != 'GET':
        return JsonResponse({'code': 405, 'message': 'Method not allowed'}, status=405)
    
    # 验证 API Key
    api_key = request.headers.get('X-API-Key')
    if not api_key:
        return JsonResponse({'code': 401, 'message': 'Missing API Key'}, status=401)
    
    try:
        ApiKey.objects.get(key=api_key, is_active=True)
    except ApiKey.DoesNotExist:
        return JsonResponse({'code': 401, 'message': 'Invalid API Key'}, status=401)
    
    servers = Server.objects.filter(status='active').values('id', 'hostname', 'ip_address')
    
    # 加密返回
    encrypted = encrypt_password(json.dumps(list(servers)))
    
    return JsonResponse({
        'code': 200,
        'message': 'success',
        'data': encrypted
    })

@csrf_exempt
def run_baseline_check(request, server_id):
    """执行基线检查"""
    try:
        server = Server.objects.get(id=server_id)
    except Server.DoesNotExist:
        return JsonResponse({'code': 404, 'message': '服务器不存在'}, status=404)
    
    from .baseline import BaselineChecker
    checker = BaselineChecker(server)
    results = checker.check_all()
    
    # 保存结果并检测告警
    failed_items = []
    for r in results:
        BaselineResult.objects.create(
            server=server,
            check_item=r['check_item'],
            is_pass=r['is_pass'],
            detail=r['detail']
        )
        if not r['is_pass']:
            failed_items.append(r['check_item'])
    
    # 发送基线告警
    if failed_items:
        # 检查是否已经告警过（同一服务器30分钟内不重复）
        last_alert = Alert.objects.filter(
            server=server,
            alert_type='baseline_fail',
            created_at__gte=datetime.now() - timedelta(minutes=30)
        ).exists()
        
        if not last_alert:
            Alert.objects.create(
                server=server,
                alert_type='baseline_fail',
                severity='warning',
                detail=f'基线检查不通过: {", ".join(failed_items)}',
                email_sent=True
            )
            EmailAlert.send_baseline_alert(server, failed_items)
    
    return JsonResponse({
        'code': 200,
        'data': {
            'server_id': server.id,
            'hostname': server.hostname,
            'check_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'results': results,
            'summary': {
                'total': len(results),
                'passed': sum(1 for r in results if r['is_pass']),
                'failed': len(failed_items)
            }
        }
    })

@csrf_exempt
def get_baseline_history(request, server_id):
    """获取基线检查历史"""
    try:
        server = Server.objects.get(id=server_id)
    except Server.DoesNotExist:
        return JsonResponse({'code': 404, 'message': '服务器不存在'}, status=404)
    
    history = BaselineResult.objects.filter(server=server).values('checked_at', 'check_item', 'is_pass')
    
    # 按时间分组
    from collections import defaultdict
    grouped = defaultdict(lambda: {'total': 0, 'passed': 0})
    for h in history:
        time_key = h['checked_at'].strftime('%Y-%m-%d %H:%M:%S')
        grouped[time_key]['total'] += 1
        if h['is_pass']:
            grouped[time_key]['passed'] += 1
    
    result = [{'checked_at': k, 'total': v['total'], 'passed': v['passed']} for k, v in grouped.items()]
    result.sort(key=lambda x: x['checked_at'], reverse=True)
    
    return JsonResponse({'code': 200, 'data': result[:10]})

@csrf_exempt
def get_alerts(request):
    """获取告警记录"""
    server_id = request.GET.get('server_id')
    resolved = request.GET.get('resolved')
    
    alerts = Alert.objects.all().order_by('-created_at')
    
    if server_id:
        alerts = alerts.filter(server_id=server_id)
    if resolved is not None:
        alerts = alerts.filter(is_resolved=resolved.lower() == 'true')
    
    from django.core.paginator import Paginator
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 20))
    paginator = Paginator(alerts, page_size)
    page_data = paginator.get_page(page)
    
    data = []
    for alert in page_data:
        data.append({
            'id': alert.id,
            'server_id': alert.server.id,
            'server_name': alert.server.hostname,
            'alert_type': alert.alert_type,
            'severity': alert.severity,
            'detail': alert.detail,
            'is_resolved': alert.is_resolved,
            'email_sent': alert.email_sent,
            'created_at': alert.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'resolved_at': alert.resolved_at.strftime('%Y-%m-%d %H:%M:%S') if alert.resolved_at else None
        })
    
    return JsonResponse({
        'code': 200,
        'data': {
            'records': data,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_pages': paginator.num_pages,
                'total_records': paginator.count
            }
        }
    })