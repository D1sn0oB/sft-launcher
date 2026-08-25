
# === mods/__init__.py ===
# 模组加载器模块

# === mods/fabric.py ===
"""Fabric 模组加载器安装。

通过 Fabric 元数据 API 获取 loader 信息，构建新的版本 JSON 并下载必要库文件。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from core import DownloadError, http_get_json, retry_download, sha1_hex
from core import LauncherConfig
from core import VersionManager

FABRIC_META = "https://meta.fabricmc.net/v2/versions/loader/{mcver}"
FABRIC_LOADER_URL = "https://maven.fabricmc.net/net/fabricmc/fabric-loader/{version}/fabric-loader-{version}.jar"


class FabricError(Exception):
    pass


class FabricInstaller:
    """Fabric 加载器安装器。"""

    def __init__(self, config: LauncherConfig, version_manager: VersionManager):
        self.config = config
        self.vm = version_manager

    # ---------- 元数据 ----------
    def list_loaders(self, mcver: str) -> list[dict]:
        """获取指定 MC 版本可用的 Fabric loader 列表。"""
        try:
            data = http_get_json(FABRIC_META.format(mcver=mcver), timeout=15)
        except DownloadError as e:
            raise FabricError(f"无法获取 Fabric 版本信息：{e}")
        result = []
        for item in data:
            result.append({
                "loader_version": item["loader"]["version"],
                "intermediary_version": item["intermediary"]["version"],
                "stable": item["loader"].get("stable", True),
                "meta": item,
            })
        return result

    def latest_loader(self, mcver: str) -> dict:
        """返回最新稳定 loader。"""
        loaders = self.list_loaders(mcver)
        stable = [l for l in loaders if l["stable"]] or loaders
        return stable[0]

    # ---------- 版本 ID ----------
    def fabric_version_id(self, mcver: str, loader_ver: str) -> str:
        return f"{mcver}-fabric-{loader_ver}"

    # ---------- 安装 ----------
    def install(self, mcver: str, loader_ver: Optional[str] = None,
                progress=None) -> str:
        """为指定 MC 版本安装 Fabric。

        返回生成的 Fabric 版本 ID。
        若 loader_ver 未指定，使用最新稳定版。
        """
        meta = self.latest_loader(mcver) if not loader_ver else \
            next((l for l in self.list_loaders(mcver) if l["loader_version"] == loader_ver), None)
        if not meta:
            raise FabricError(f"未找到 Fabric loader {loader_ver} 对应的元数据")
        lv = meta["loader_version"]
        ver_id = self.fabric_version_id(mcver, lv)

        if progress:
            progress("获取原版版本信息", 0, 1)
        base_json = self.vm.get_version_json(mcver)

        if progress:
            progress("下载 Fabric loader", 0, 2)
        self._download_loader(lv)

        if progress:
            progress("生成 Fabric 版本 JSON", 0, 3)
        new_json = self._build_version_json(mcver, lv, base_json, meta["meta"])
        ver_dir = self.config.versions_dir / ver_id
        ver_dir.mkdir(parents=True, exist_ok=True)
        (ver_dir / f"{ver_id}.json").write_text(
            json.dumps(new_json, ensure_ascii=False, indent=2), encoding="utf-8")

        # 下载 fabric 需要的额外库
        if progress:
            progress("下载 Fabric 依赖库", 0, 4)
        self._download_fabric_libs(meta["meta"])

        # 复制原版 jar 作为 fabric 版本的 jar（指向原版 jar）
        base_jar = self.vm.version_jar_path(mcver)
        if base_jar.exists():
            import shutil
            shutil.copy2(base_jar, ver_dir / f"{ver_id}.jar")

        if progress:
            progress("完成", 1, 1)
        return ver_id

    def _download_loader(self, loader_ver: str) -> Path:
        """下载 fabric-loader jar。"""
        url = FABRIC_LOADER_URL.format(version=loader_ver)
        # 优先 BMCLAPI 镜像
        base = self.config.source_config.get("library_base")
        if base and "bmclapi" in self.config.source:
            url = base + f"net/fabricmc/fabric-loader/{loader_ver}/fabric-loader-{loader_ver}.jar"
        dest = self.config.libraries_dir / f"net/fabricmc/fabric-loader/{loader_ver}/fabric-loader-{loader_ver}.jar"
        retry_download(url, dest)
        return dest

    def _download_fabric_libs(self, meta: dict) -> None:
        """下载 Fabric 需要的额外库。"""
        libs = meta.get("launcherMeta", {}).get("libraries", {})
        all_libs = libs.get("common", []) + libs.get("client", [])
        for lib in all_libs:
            name = lib.get("name", "")
            url = lib.get("url", "")
            sha1 = lib.get("sha1")
            if ":" not in name:
                continue
            path = _maven_path(name)
            if not path:
                continue
            dest = self.config.libraries_dir / path
            if sha1 and sha1_hex(dest) == sha1:
                continue
            if url:
                dl_url = url + path
            else:
                base = self.config.source_config.get("library_base")
                dl_url = (base or "") + path
            try:
                retry_download(dl_url, dest, sha1)
            except DownloadError:
                continue

    def _build_version_json(self, mcver: str, loader_ver: str,
                            base_json: dict, meta: dict) -> dict:
        """基于原版版本 JSON 生成 Fabric 版本 JSON。"""
        import copy
        new = copy.deepcopy(base_json)
        new["id"] = self.fabric_version_id(mcver, loader_ver)
        new["inheritsFrom"] = mcver  # 继承原版
        lm = meta.get("launcherMeta", {})
        # mainClass
        main = lm.get("mainClass", {})
        new["mainClass"] = main.get("client") or base_json.get("mainClass", "net.minecraft.client.main.Main")
        # 追加 fabric 库
        extra_libs = []
        libs = lm.get("libraries", {})
        for lib in libs.get("common", []) + libs.get("client", []):
            entry = {
                "name": lib["name"],
                "url": lib.get("url", ""),
                "downloads": {
                    "artifact": {
                        "path": _maven_path(lib["name"]),
                        "url": lib.get("url", "") + _maven_path(lib["name"]),
                        "sha1": lib.get("sha1"),
                        "size": lib.get("size", 0),
                    }
                },
            }
            extra_libs.append(entry)
        # 加上 fabric-loader jar 自身
        extra_libs.append({
            "name": f"net.fabricmc:fabric-loader:{loader_ver}",
            "downloads": {
                "artifact": {
                    "path": f"net/fabricmc/fabric-loader/{loader_ver}/fabric-loader-{loader_ver}.jar",
                    "url": "", "sha1": None, "size": 0,
                }
            },
        })
        new["libraries"] = base_json.get("libraries", []) + extra_libs
        # arguments 继承原版（去掉可能冲突的 mainClass 相关）
        return new


def _maven_path(name: str) -> str:
    """把 maven 坐标转成路径（含 classifier 处理）。"""
    parts = name.split(":")
    if len(parts) < 3:
        return ""
    group, artifact, version = parts[0], parts[1], parts[2]
    if "@" in version:
        version, ext = version.split("@", 1)
    else:
        ext = "jar"
    base = f"{group.replace('.', '/')}/{artifact}/{version}/{artifact}-{version}"
    if len(parts) >= 4:  # 有 classifier
        base += f"-{parts[3]}"
    return f"{base}.{ext}"

# === mods/forge.py ===
"""Forge 模组加载器安装。

Forge 提供官方版本 JSON（含完整库清单），直接下载使用。
版本 ID 形如 <mcver>-<forgever>。
"""

import json
from pathlib import Path
from typing import Optional

from core import DownloadError, http_get_json, retry_download
from core import LauncherConfig
from core import VersionManager

FORGE_MANIFEST = "https://files.minecraftforge.net/net/minecraftforge/forge/maven-metadata.json"
FORGE_MAVEN = "https://maven.minecraftforge.net/net/minecraftforge/forge/{version}/forge-{version}.json"
# BMCLAPI 镜像
BMCLAPI_FORGE_LIST = "https://bmclapi2.bangbang93.com/forge/minecraft/{mcver}"


class ForgeError(Exception):
    pass


class ForgeInstaller:
    """Forge 加载器安装器。"""

    def __init__(self, config: LauncherConfig, version_manager: VersionManager):
        self.config = config
        self.vm = version_manager

    # ---------- 版本列表 ----------
    def list_versions(self, mcver: str) -> list[dict]:
        """获取指定 MC 版本可用的 Forge 版本列表（含下载 URL）。"""
        url = BMCLAPI_FORGE_LIST.format(mcver=mcver)
        try:
            data = http_get_json(url, timeout=15)
        except DownloadError:
            # 回退官方 manifest
            try:
                data = self._official_versions(mcver)
            except DownloadError as e:
                raise ForgeError(f"无法获取 Forge 版本：{e}")
        result = []
        for item in data:
            ver = item.get("version", "")
            result.append({
                "forge_version": ver,
                "version_id": f"{mcver}-{ver}",
                "build": item.get("build"),
            })
        # 按 build 降序
        result.sort(key=lambda x: x.get("build") or 0, reverse=True)
        return result

    def _official_versions(self, mcver: str) -> list:
        try:
            data = http_get_json(FORGE_MANIFEST, timeout=15)
        except DownloadError:
            return []
        mc_entries = data.get(mcver, [])
        out = []
        for e in mc_entries:
            out.append({"version": e.get("version"), "build": e.get("build", 0)})
        return out

    def latest_version(self, mcver: str) -> Optional[dict]:
        versions = self.list_versions(mcver)
        return versions[0] if versions else None

    # ---------- 安装 ----------
    def install(self, mcver: str, forge_version: Optional[str] = None,
                progress=None) -> str:
        """安装 Forge 到指定 MC 版本。返回 Forge 版本 ID。"""
        ver = self.latest_version(mcver) if not forge_version else \
            next((v for v in self.list_versions(mcver) if v["forge_version"] == forge_version), None)
        if not ver:
            raise ForgeError(f"未找到 Forge 版本 {forge_version}")
        version_id = ver["version_id"]

        if progress:
            progress(f"获取 Forge {version_id} 版本信息", 0, 1)
        vjson = self._fetch_version_json(version_id, ver["forge_version"])

        if progress:
            progress("写入版本 JSON", 0, 2)
        ver_dir = self.config.versions_dir / version_id
        ver_dir.mkdir(parents=True, exist_ok=True)
        (ver_dir / f"{version_id}.json").write_text(
            json.dumps(vjson, ensure_ascii=False, indent=2), encoding="utf-8")

        if progress:
            progress("复制原版 jar", 0, 3)
        base_jar = self.vm.version_jar_path(mcver)
        if base_jar.exists():
            import shutil
            shutil.copy2(base_jar, ver_dir / f"{version_id}.jar")

        if progress:
            progress("完成", 1, 1)
        return version_id

    def _fetch_version_json(self, version_id: str, forge_version: str) -> dict:
        """获取 Forge 官方版本 JSON，多源回退。"""
        urls = [
            # BMCLAPI 镜像
            f"https://bmclapi2.bangbang93.com/version/{version_id}/json",
            f"https://bmclapi2.bangbang93.com/maven/net/minecraftforge/forge/{version_id}/forge-{version_id}.json",
            # 官方 maven
            f"https://maven.minecraftforge.net/net/minecraftforge/forge/{version_id}/forge-{version_id}.json",
            # MCBBS 镜像
            f"https://download.mcbbs.net/maven/net/minecraftforge/forge/{version_id}/forge-{version_id}.json",
        ]
        for url in urls:
            try:
                return http_get_json(url, timeout=20)
            except DownloadError:
                continue
        raise ForgeError(f"无法获取 Forge {version_id} 的版本 JSON（请检查网络或更换下载源）")
