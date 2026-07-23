import json
import logging
from pathlib import Path

from fastapi import APIRouter, Query, Depends

from app.api.deps import get_current_user_tenant

logger = logging.getLogger(__name__)
router = APIRouter()


# 启动时一次性加载，避免每次请求都读文件
_CATEGORY_TREE: list[dict] | None = None
_CATEGORY_MEDIUM_CACHE: dict[str, list[dict]] = {}  # mediumId -> [{smallId, smallName}]
_CATEGORY_BIG_CACHE: dict[str, list[dict]] = {}  # bigId -> [{mediumId, mediumName}]


def _load_tree() -> list[dict]:
    """读取 backend/data/category.json 并转换为 AMIS 懒加载格式。

    原始数据结构：
      [
        {
          "code": 200,
          "message": "success",
          "data": [
            {
              "bigId": "920", "bigName": "烟草",
              "mediumList": [
                {
                  "mediumId": "92001", "mediumName": "香烟",
                  "smallList": [{"smallId": "92001001", "smallName": "..."}, ...]
                }
              ]
            }
          ]
        }
      ]

    目标结构（AMIS 懒加载）：
      [
        {
          "label": "烟草", "value": "920",
          "defer": true,
          "children": []
        }
      ]

    同时缓存 mediumId -> smallList 的映射，供 deferApi 查询使用。
    """
    global _CATEGORY_MEDIUM_CACHE, _CATEGORY_BIG_CACHE
    path = Path(__file__).resolve().parents[3] / "data" / "category.json"
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    bigs = raw[0]["data"]  # 剥掉外层 {code, message, data: [...]}

    _CATEGORY_MEDIUM_CACHE = {}
    _CATEGORY_BIG_CACHE = {}
    for big in bigs:
        _CATEGORY_BIG_CACHE[big["bigId"]] = [
            {"label": m["mediumName"], "value": m["mediumId"],
             "defer": True, "children": []}
            for m in big.get("mediumList", [])
        ]
        for m in big.get("mediumList", []):
            mid = m["mediumId"]
            _CATEGORY_MEDIUM_CACHE[mid] = [
                {"label": s["smallName"], "value": s["smallId"]}
                for s in m.get("smallList", [])
            ]

    # 懒加载格式：只返回一级节点，children 为空，标记 defer: true
    return [
        {
            "label": big["bigName"],
            "value": big["bigId"],
            "defer": True,
            "children": [],
        }
        for big in bigs
    ]


@router.on_event("startup")
async def _init():
    """启动时加载分类树和缓存到内存。"""
    global _CATEGORY_TREE
    try:
        _CATEGORY_TREE = _load_tree()
        logger.info(
            "loaded category tree: %d top-level categories, %d medium entries",
            len(_CATEGORY_TREE), len(_CATEGORY_MEDIUM_CACHE),
        )
    except Exception as e:
        logger.exception("failed to load category tree: %s", e)
        _CATEGORY_TREE = []


@router.get("/tree")
async def get_category_tree():
    """返回 AMIS input-tree 兼容的一级分类树（懒加载）。

    只返回一级节点，子节点通过 deferApi 按需拉取。
    响应格式：{status, msg, data: {options: [...]}}
    """
    if _CATEGORY_TREE is None:
        tree = _load_tree()
    else:
        tree = _CATEGORY_TREE
    return {
        "status": 0,
        "msg": "",
        "data": {"options": tree},
    }


@router.get("/defer")
async def get_defer_options(
    value: str = Query(..., description="父节点 value"),
    waitSeconds: float = Query(0.1, description="模拟延迟（秒），用于测试 loading 态"),
    ctx=Depends(get_current_user_tenant),
):
    """AMIS deferApi 端点：根据父节点 value 返回子节点列表。

    规则：
    - value 是大类编码（3位） → 返回中类列表
    - value 是中类编码（5位） → 返回小类列表
    - value 是小类编码（9位） → 返回空列表
    """
    # 简单实现：直接查 _CATEGORY_MEDIUM_CACHE
    # 缓存结构：{ mediumId: [{label, value}] }
    # 大类 → 中类：需要遍历缓存 key
    # 中类 → 小类：直接查 _CATEGORY_MEDIUM_CACHE[value]

    # deferApi 传参：label 是父节点的 label 字段，value 是父节点的 value 字段
    if len(value) == 3:  # 大类编码 3 位
        children = _CATEGORY_BIG_CACHE.get(value, [])
        return {
            "status": 0,
            "msg": "",
            "data": {"options": children},
        }
    elif len(value) == 5:
        # 中类 → 小类：直接查缓存
        children = _CATEGORY_MEDIUM_CACHE.get(value, [])
        return {
            "status": 0,
            "msg": "",
            "data": {"options": children},
        }
    else:
        return {"status": 0, "msg": "", "data": {"options": []}}
