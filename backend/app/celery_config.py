from app.config import settings

# Redis broker & result
broker_url = settings.REDIS_URL
result_backend = settings.REDIS_URL

# 强制 RESP2 + 适配阿里云 Redis 5.0 兼容内核
broker_transport_options = {
    'protocol': 2,
    'socket_timeout': 30,
    'socket_connect_timeout': 30,
    'visibility_timeout': 3600,
}
result_backend_transport_options = {
    'protocol': 2,
    'socket_timeout': 30,
    'socket_connect_timeout': 30,
}

task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
timezone = 'Asia/Shanghai'
task_track_started = True
broker_connection_retry_on_startup = True