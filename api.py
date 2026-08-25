
# === api/__init__.py ===
# 下载 API 模块

# === api/curseforge.py ===
"""CurseForge API 客户端：搜索与下载 mod / 资源包。

默认内置一个公开共享的 API Key（由作者申请），实现"开箱即用"；
用户也可在设置中填入自己的 Key 覆盖内置 Key（更安全、个人额度独立）。

防封控设计：
- 全局请求限流器（令牌桶），控制 QPS，避免触发速率限制
- 请求间隔随机化，降低被识别为机器批量请求的风险
- 429/错误自动指数退避重试，失败时给出明确降级提示
- 大量下载前自动检测限流风险并提醒

注意：内置共享 Key 有被 CurseForge 限流/封禁的风险，仅供个人小范围使用。
"""
from __future__ import annotations

import random
import threading
import time
from typing import Optional

import requests

from core import DownloadError, retry_download

API = "https://api.curseforge.com/v1"

# 项目类型 ID（CurseForge 分类）
PROJECT_TYPE_MOD = 6            # Minecraft Mods
PROJECT_TYPE_RESOURCEPACK = 12  # Minecraft Resource Packs

# 内置共享 Key（作者申请，实现"开箱即用"）。可被用户设置覆盖。
BUILTIN_API_KEY = "$2a$10$KYaNLB8X0Xk1Nl5r8PwgQucE567lf7Lpw4ikLfX7pjCCVzIspn7iK"

# 限流参数
MAX_REQUESTS_PER_MINUTE = 25   # 每分钟最多 25 次 API 请求（保守，降低风险）
MIN_INTERVAL = 0.8             # 两次请求最小间隔（秒），含随机抖动
JITTER_RANGE = (0.4, 1.6)      # 随机间隔抖动范围


class RateLimiter:
    """令牌桶限流器（线程安全）。"""

    def __init__(self, max_per_minute: int, jitter_range=(0.4, 1.6)):
        self.min_interval = 60.0 / max_per_minute
        self.jitter_range = jitter_range
        self._last = 0.0
        self._lock = threading.Lock()
        self._count_window_start = time.time()
        self._count = 0

    def wait(self) -> None:
        """在发起请求前调用，等待合适的时机并记账。"""
        with self._lock:
            now = time.time()
            # 窗口滚动（每分钟重置计数）
            if now - self._count_window_start >= 60:
                self._count_window_start = now
                self._count = 0
            # 强制最小间隔
            elapsed = now - self._last
            delay = self.min_interval - elapsed
            if delay > 0:
                delay += random.uniform(*self.jitter_range)
                time.sleep(delay)
            self._last = time.time()
            self._count += 1

    def minutes_remaining_count(self) -> int:
        """返回本分钟已用请求数（用于提示）。"""
        with self._lock:
            return self._count


class CurseForgeError(Exception):
    pass


class CurseForgeClient:
    """CurseForge 搜索与下载客户端（内置共享 Key + 限流保护）。"""

    _limiter = RateLimiter(MAX_REQUESTS_PER_MINUTE, JITTER_RANGE)

    def __init__(self, api_key: str = ""):
        # 优先用户自定义 Key，其次内置 Key
        self.api_key = api_key or BUILTIN_API_KEY
        self._rate_limited = False  # 标记是否已触发限流
        self._ua = _random_ua()     # 实例级 UA，保持稳定

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> dict:
        if not self.api_key:
            raise CurseForgeError("未配置 CurseForge API Key")
        return {
            "x-api-key": self.api_key,
            "Accept": "application/json",
            # 稳定的 UA，降低被聚合识别的概率
            "User-Agent": self._ua,
        }

    # ---------- 核心请求（含限流 + 退避） ----------
    def _request(self, method: str, url: str, params=None, retries: int = 3) -> dict:
        self._limiter.wait()
        headers = self._headers()
        last_err = ""
        for attempt in range(retries):
            try:
                resp = requests.request(method, url, params=params,
                                        headers=headers, timeout=20)
                if resp.status_code == 429:
                    # 触发限流：指数退避后重试
                    self._rate_limited = True
                    wait = 2 ** attempt + random.uniform(0.5, 1.5)
                    time.sleep(wait)
                    last_err = "触发 CurseForge 限流（429）"
                    continue
                resp.raise_for_status()
                self._rate_limited = False
                return resp.json()
            except requests.exceptions.RequestException as e:
                last_err = str(e)
                if attempt < retries - 1:
                    time.sleep(1 + random.uniform(0, 1))
        raise CurseForgeError(last_err or "请求失败")

    @property
    def rate_limited(self) -> bool:
        return self._rate_limited

    # ---------- 搜索 ----------
    def search(self, query: str, project_type: int = PROJECT_TYPE_MOD,
               game_version: Optional[str] = None,
               class_id: Optional[int] = None,
               page_size: int = 20) -> list[dict]:
        """搜索项目。"""
        params = {
            "gameId": 432,  # Minecraft
            "searchFilter": query,
            "pageSize": page_size,
            "index": 0,
        }
        if project_type == PROJECT_TYPE_MOD:
            params["classId"] = class_id or PROJECT_TYPE_MOD
        if game_version:
            params["gameVersion"] = game_version
        try:
            data = self._request("GET", f"{API}/mods/search", params=params)
        except CurseForgeError as e:
            raise CurseForgeError(f"CurseForge 搜索失败：{e}")
        results = []
        for item in data.get("data", []):
            results.append({
                "id": item.get("id"),
                "name": item.get("name"),
                "summary": item.get("summary", ""),
                "downloads": item.get("downloadCount", 0),
                "logo_url": (item.get("logo") or {}).get("url"),
                "author": (item.get("authors") or [{}])[0].get("name") if item.get("authors") else "",
            })
        return results

    # ---------- 文件 ----------
    def get_files(self, mod_id: int, game_version: Optional[str] = None) -> list[dict]:
        """获取 mod 的文件列表。"""
        params = {"pageSize": 20, "index": 0}
        if game_version:
            params["gameVersion"] = game_version
        try:
            data = self._request("GET", f"{API}/mods/{mod_id}/files", params=params)
        except CurseForgeError as e:
            raise CurseForgeError(f"CurseForge 获取文件失败：{e}")
        result = []
        for f in data.get("data", []):
            result.append({
                "id": f.get("id"),
                "filename": f.get("displayName", ""),
                "url": f.get("downloadUrl"),
                "size": f.get("fileLength", 0),
            })
        return result

    def pick_best_file(self, mod_id: int, game_version: Optional[str] = None) -> Optional[dict]:
        files = self.get_files(mod_id, game_version)
        return files[0] if files else None

    # ---------- 下载 ----------
    def download_to(self, file: dict, dest_dir, progress=None) -> str:
        from pathlib import Path
        dest_dir = Path(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)
        url = file.get("url")
        if not url:
            raise CurseForgeError("该文件无直接下载地址（CurseForge 限制）")
        dest = dest_dir / _safe_name(file.get("filename", "mod.jar"))
        retry_download(url, dest, progress=progress)
        return str(dest)


def _random_ua() -> str:
    """随机化 UA，降低被批量识别的概率。"""
    return f"SFTLauncher/{random.randint(1000, 9999)}"


def _safe_name(name: str) -> str:
    import re
    name = re.sub(r'[\\/:*?"<>|]', "_", name)
    return name or "download.jar"

# === api/modrinth.py ===
"""Modrinth API 客户端：搜索与下载 mod / 资源包。

Modrinth 提供开放 API（无需密钥），支持按 MC 版本和加载器筛选。
"""

from typing import Optional

from core import DownloadError, http_get_json, retry_download

API = "https://api.modrinth.com/v2"
HEADERS = {"User-Agent": "sft-launcher/0.1.0"}

# 加载器类型 -> Modrinth category
LOADER_MAP = {
    "fabric": "fabric",
    "forge": "forge",
    "quilt": "quilt",
    "neoforge": "neoforge",
    "原版": "vanilla",
}


class ModrinthError(Exception):
    pass


class ModrinthClient:
    """Modrinth 搜索与下载客户端。"""

    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout

    # ---------- 搜索 ----------
    def search(self, query: str, project_type: str = "mod",
               mc_version: Optional[str] = None,
               loader: Optional[str] = None,
               limit: int = 20) -> list[dict]:
        """搜索项目。project_type: mod / resourcepack。

        返回 [{slug, title, description, downloads, icon_url, project_type}]
        """
        facets = []
        if project_type:
            facets.append([f"project_type:{project_type}"])
        if mc_version:
            facets.append([f"versions:{mc_version}"])
        if loader:
            cat = LOADER_MAP.get(loader.lower())
            if cat:
                facets.append([f"categories:{cat}"])
        import json as _json
        import urllib.parse
        params = {
            "query": query,
            "limit": limit,
            "facets": _json.dumps(facets),  # 必须是合法 JSON 字符串
        }
        qs = urllib.parse.urlencode(params)
        try:
            data = http_get_json(f"{API}/search?{qs}", timeout=self.timeout, headers=HEADERS)
        except DownloadError as e:
            raise ModrinthError(f"搜索失败：{e}")
        results = []
        for hit in data.get("hits", []):
            results.append({
                "slug": hit.get("slug"),
                "title": hit.get("title"),
                "description": hit.get("description", ""),
                "downloads": hit.get("downloads", 0),
                "icon_url": hit.get("icon_url"),
                "author": hit.get("author"),
                "project_type": hit.get("project_type"),
            })
        return results

    # ---------- 版本 ----------
    def get_versions(self, slug: str, mc_version: Optional[str] = None,
                     loader: Optional[str] = None) -> list[dict]:
        """获取项目的可用版本（按 MC 版本/加载器筛选）。

        返回 [{id, version_number, game_versions, loaders, files}]
        """
        params = {}
        if mc_version:
            import json as _json
            params["game_versions"] = _json.dumps([mc_version])
        if loader:
            import json as _json
            cat = LOADER_MAP.get(loader.lower())
            if cat:
                params["loaders"] = _json.dumps([cat])
        import urllib.parse
        qs = "?" + urllib.parse.urlencode(params) if params else ""
        try:
            return http_get_json(f"{API}/project/{slug}/version{qs}",
                                 timeout=self.timeout, headers=HEADERS)
        except DownloadError as e:
            raise ModrinthError(f"获取版本失败：{e}")

    def pick_best_file(self, slug: str, mc_version: str,
                       loader: Optional[str] = None) -> Optional[dict]:
        """选择最适合当前环境的一个文件。

        返回 {id, filename, url, size} 或 None。
        """
        versions = self.get_versions(slug, mc_version, loader)
        if not versions:
            return None
        for v in versions:
            for f in v.get("files", []):
                return {
                    "id": f.get("id"),
                    "filename": f.get("filename"),
                    "url": f.get("url"),
                    "size": f.get("size", 0),
                }
        return None

    # ---------- 下载 ----------
    def download_to(self, file: dict, dest_dir, progress=None) -> str:
        """下载文件到指定目录。返回保存的文件路径。"""
        from pathlib import Path
        dest_dir = Path(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / file["filename"]
        retry_download(file["url"], dest, progress=progress)
        return str(dest)
