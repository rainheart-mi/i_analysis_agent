import httpx
from typing import Dict, Any, Optional
from app.config import settings


class N8NService:
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.headers = {}
        if api_key:
            self.headers["X-N8N-API-Key"] = api_key

    async def execute_workflow(
        self,
        workflow_id: str,
        node_id: str,
        inputs: Dict[str, Any],
        timeout: int = settings.N8N_DEFAULT_TIMEOUT
    ) -> Dict[str, Any]:
        """触发 N8N 工作流执行"""
        url = f"{self.base_url}/webhook/{workflow_id}"

        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.post(
                    url,
                    json=inputs,
                    headers=self.headers
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                raise Exception(f"N8N API 错误: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                raise Exception(f"N8N 调用失败: {str(e)}")

    async def test_connection(self) -> bool:
        """测试 N8N 连接"""
        url = f"{self.base_url}/rest"
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                response = await client.get(url, headers=self.headers)
                return response.status_code == 200
            except Exception:
                return False


def get_n8n_service(base_url: str, api_key: Optional[str] = None) -> N8NService:
    return N8NService(base_url, api_key)