import httpx
from typing import Dict, Any, Optional
from app.config import settings


class N8NService:
    def __init__(self, base_url: str, api_key: Optional[str] = None, mode: str = "production"):
        self.base_url = base_url.rstrip("/")
        self.mode = mode  # mocker / test / production
        self.headers = {}
        if api_key:
            self.headers["X-N8N-API-Key"] = api_key

    def _get_webhook_url(self, workflow_id: str) -> str:
        """根据模式组装不同的 webhook URL"""
        if self.mode == "test":
            # Test webhook: /webhook-test/{workflow_id}
            return f"{self.base_url}/webhook-test/{workflow_id}"
        else:
            # Production webhook: /webhook/{workflow_id}
            return f"{self.base_url}/webhook/{workflow_id}"

    async def execute_workflow(
        self,
        workflow_id: str,
        node_id: str,
        inputs: Dict[str, Any],
        timeout: int = settings.N8N_DEFAULT_TIMEOUT
    ) -> Dict[str, Any]:
        """触发 N8N 工作流执行"""
        url = self._get_webhook_url(workflow_id)

        # 直接将 inputs 作为请求体发送（扁平化 JSON）
        payload = inputs if inputs else {}

        async with httpx.AsyncClient(timeout=timeout) as client:
            print(f"[N8N] Calling URL: {url}")
            print(f"[N8N] Request payload: {payload}")
            try:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self.headers
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                raise Exception(f"N8N API 错误: {e.response.status_code} - {e.response.text}")
            except httpx.TimeoutException as e:
                raise Exception(f"N8N 调用超时: {str(e)}")
            except Exception as e:
                raise Exception(f"N8N 调用失败: {type(e).__name__} - {str(e)}")

    async def test_connection(self) -> bool:
        """测试 N8N 连接"""
        url = f"{self.base_url}/rest"
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                response = await client.get(url, headers=self.headers)
                return response.status_code == 200
            except Exception:
                return False


def get_n8n_service(base_url: str, api_key: Optional[str] = None, mode: str = "production") -> N8NService:
    return N8NService(base_url, api_key, mode)