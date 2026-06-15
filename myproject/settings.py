import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# ========== 安全配置 ==========
# 生产环境一定要修改为复杂字符串
SECRET_KEY = 'django-insecure-your-secret-key-here-change-it-in-production'

# 开发环境设为 True，生产环境设为 False
DEBUG = True

# 允许访问的主机（生产环境要限制）
ALLOWED_HOSTS = ['*']  # 开发环境用 *，生产环境指定具体 IP

# ========== 应用注册 ==========
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # 第三方应用
    'rest_framework',      # DRF：简化 API 开发
    'corsheaders',         # 跨域支持（开发环境用）
    # 自定义应用
    'server_mgr',          # 服务器管理模块
]

# ========== 中间件配置 ==========
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # 跨域中间件（放在最前面）
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# 根路由配置
ROOT_URLCONF = 'myproject.urls'

# ========== 模板配置 ==========
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # 模板文件目录
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# WSGI 应用
WSGI_APPLICATION = 'myproject.wsgi.application'

# ========== 数据库配置（重点：MySQL）==========
# 方案1：使用 MySQL（作业要求）
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'ops_system',           # 数据库名
        'USER': 'root',                  # MySQL 用户名
        'PASSWORD': '123456',            # MySQL 密码（改成你自己的）
        'HOST': '127.0.0.1',             # MySQL 地址（本地用127.0.0.1）
        'PORT': '3306',                  # MySQL 端口
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'"
        }
    }
}

# 方案2：开发阶段临时用 SQLite3（注释掉上面，取消注释下面）
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }

# ========== 密码验证 ==========
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# ========== 国际化配置 ==========
LANGUAGE_CODE = 'zh-hans'           # 中文
TIME_ZONE = 'Asia/Shanghai'         # 上海时区
USE_I18N = True
USE_TZ = False                       # 关闭 UTC，使用本地时间

# ========== 静态文件配置 ==========
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',              # 开发时的静态文件目录
]
STATIC_ROOT = BASE_DIR / 'staticfiles'  # 生产环境收集静态文件的目录

# 媒体文件（用户上传）
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ========== 默认主键类型 ==========
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ========== 跨域配置（开发环境）==========
CORS_ALLOW_ALL_ORIGINS = True        # 开发环境允许所有跨域
CORS_ALLOW_CREDENTIALS = True

# ========== 邮件配置（用于告警）==========
# 使用 QQ 邮箱示例（需要开启 SMTP）
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.qq.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = '480354050@qq.com'        # 改成你的邮箱
EMAIL_HOST_PASSWORD = 'reflkruldflbcbci'        # 授权码，不是QQ密码
DEFAULT_FROM_EMAIL = '480354050@qq.com'
ADMIN_EMAILS = ['y1514687348@163.com']
# 开发环境可以改用控制台输出（不真正发邮件）
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ========== Redis 配置（用于 Celery）==========
# ========== Celery 配置 ==========
CELERY_BROKER_URL = 'redis://127.0.0.1:6379/0'  # Redis 作为消息中间件
CELERY_RESULT_BACKEND = 'redis://127.0.0.1:6379/0'  # 存储任务结果
CELERY_TIMEZONE = 'Asia/Shanghai'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 任务超时30分钟
CELERY_BEAT_SCHEDULE = {
    'collect_metrics_every_5_seconds': {
        'task': 'server_mgr.tasks.collect_metrics_task',
        'schedule': 5.0,  # 每5秒执行一次
    },
}


# Celery 配置（稍后启用）
# CELERY_BROKER_URL = 'redis://127.0.0.1:6379/0'
# CELERY_RESULT_BACKEND = 'redis://127.0.0.1:6379/0'
# CELERY_TIMEZONE = 'Asia/Shanghai'
# CELERY_TASK_TRACK_STARTED = True
# CELERY_TASK_TIME_LIMIT = 30 * 60

# ========== 日志配置 ==========
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'server_mgr': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# 创建日志目录
LOGS_DIR = BASE_DIR / 'logs'
if not LOGS_DIR.exists():
    LOGS_DIR.mkdir()