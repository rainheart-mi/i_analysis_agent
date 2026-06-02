"""
原始诊断脚本：绕开 redis-py 握手，直接看网络与协议层
"""
import socket
import time
import sys


def test_dns():
    print("=== 1. DNS 解析 ===")
    try:
        addr = socket.gethostbyname("r-f8zcsffr05p5sdbi2o.redis.rds.aliyuncs.com")
        print(f"  解析结果: {addr}")
        return addr
    except Exception as e:
        print(f"  失败: {e}")
        return None


def test_tcp(addr):
    print("\n=== 2. TCP 端口连通性 ===")
    try:
        start = time.time()
        s = socket.create_connection((addr, 6379), timeout=5)
        s.close()
        print(f"  端口可达 (耗时 {time.time()-start:.2f}s)")
        return True
    except Exception as e:
        print(f"  失败: {type(e).__name__}: {e}")
        return False


def test_raw_ping(addr):
    print("\n=== 3. 裸 PING（不认证）===")
    try:
        s = socket.create_connection((addr, 6379), timeout=5)
        s.sendall(b"*1\r\n$4\r\nPING\r\n")
        resp = s.recv(100)
        s.close()
        # RESP 协议: +PONG 或 -NOAUTH
        print(f"  响应: {resp!r}")
        if b"PONG" in resp:
            print("  ✓ 裸 PING 成功（无需认证）")
        elif b"NOAUTH" in resp:
            print("  → 需要认证，账号/密码模式")
        elif b"NOAUTH" not in resp:
            print(f"  ? 意外响应")
    except Exception as e:
        print(f"  失败: {type(e).__name__}: {e}")


def test_redis_py_minimal():
    print("\n=== 4. redis-py 最小化连接 ===")
    try:
        import redis
        # 关键：直接传参而非 URL，绕开 urlparse
        r = redis.Redis(
            host="r-f8zcsffr05p5sdbi2o.redis.rds.aliyuncs.com",
            port=6379,
            db=5,
            username="shennong_rw",
            password="hongdi!xupu3D!com",
            socket_timeout=10,
            socket_connect_timeout=10,
            protocol=2,
        )
        start = time.time()
        print(f"  PING: {r.ping()}  (耗时 {time.time()-start:.2f}s)")
        print(f"  VERSION: {r.info('server').get('redis_version')}")
    except Exception as e:
        print(f"  失败: {type(e).__name__}: {str(e)[:200]}")


def test_redis_py_legacy_mode():
    print("\n=== 5. redis-py LEGACY 模式（强制 protocol=2）===")
    try:
        import redis
        # 用 URL 但强制 protocol=2
        url = "redis://:shennong_rw:hongdi%21xupu3D%21com@r-f8zcsffr05p5sdbi2o.redis.rds.aliyuncs.com:6379/5"
        r = redis.from_url(url, protocol=2, socket_timeout=10, socket_connect_timeout=10)
        start = time.time()
        print(f"  PING: {r.ping()}  (耗时 {time.time()-start:.2f}s)")
    except Exception as e:
        print(f"  失败: {type(e).__name__}: {str(e)[:200]}")


if __name__ == "__main__":
    addr = test_dns()
    if addr:
        test_tcp(addr)
        test_raw_ping(addr)
    test_redis_py_minimal()
    test_redis_py_legacy_mode()
    print("\n=== 诊断结束 ===")
    print("请将以上完整输出发给我")
