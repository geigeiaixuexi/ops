from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('api/servers/', views.server_list, name='server_list'),
    path('api/servers/<int:server_id>/', views.server_detail, name='server_detail'),
    path('api/servers/<int:server_id>/refresh/', views.refresh_server_info, name='refresh'),
    path('api/metrics/<int:server_id>/', views.get_metrics, name='get_metrics'),
    path('api/external/check/', views.external_check, name='external_check'),
    path('api/external/servers/', views.external_get_servers, name='external_servers'),
    path('api/servers/<int:server_id>/baseline/', views.run_baseline_check, name='baseline'),
    path('api/servers/<int:server_id>/baseline/history/', views.get_baseline_history, name='baseline_history'),
    path('api/alerts/', views.get_alerts, name='get_alerts'),
    
]