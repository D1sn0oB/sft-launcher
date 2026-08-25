
# === config.py ===
"""启动器全局配置管理。

负责：
- 管理全局设置（下载源、Java 路径、账号信息等）
- 管理多实例数据（实例列表、每个实例的独立配置）
- 维护目录结构（versions / instances / libraries / java 等）

配置以 JSON 存储，路径：<根目录>/launcher.json
"""
from __future__ import annotations

import json
import os
import platform
from pathlib import Path
from typing import Any, Optional

APP_NAME = "SFT 启动器"
APP_VERSION = "0.1.0"

# 支持的下载源
SOURCES = {
    "mojang": {
        "label": "Mojang 官方源",
        "version_manifest": "https://launchermeta.mojang.com/mc/game/version_manifest_v2.json",
        "library_base": "https://libraries.minecraft.net/",
        "resource_base": "https://resources.download.minecraft.net/",
        "meta_base": None,  # 官方无独立的元数据服务器
    },
    "bmclapi": {
        "label": "BMCLAPI 国内镜像",
        "version_manifest": "https://bmclapi2.bangbang93.com/mc/game/version_manifest_v2.json",
        "library_base": "https://bmclapi2.bangbang93.com/maven/",
        "resource_base": "https://bmclapi2.bangbang93.com/assets/",
        "meta_base": "https://bmclapi2.bangbang93.com/meta/",
    },
}


def default_root() -> Path:
    """返回默认的启动器根目录（用户目录下的 .mc-launcher）。"""
    if platform.system() == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home()))
        return base / ".mc-launcher"
    return Path.home() / ".mc-launcher"


class LauncherConfig:
    """启动器配置 + 实例数据的总入口。"""

    def __init__(self, root: Optional[Path] = None):
        self.root = Path(root) if root else default_root()
        self.config_file = self.root / "launcher.json"
        # 目录结构
        self.versions_dir = self.root / "versions"
        self.libraries_dir = self.root / "libraries"
        self.resources_dir = self.root / "resources"       # assets
        self.instances_dir = self.root / "instances"
        self.java_dir = self.root / "java"
        self.cache_dir = self.root / "cache"
        self.logs_dir = self.root / "logs"
        for d in (self.versions_dir, self.libraries_dir, self.resources_dir,
                  self.instances_dir, self.java_dir, self.cache_dir, self.logs_dir):
            d.mkdir(parents=True, exist_ok=True)

        # 全局设置
        self.settings: dict[str, Any] = {}
        # 实例列表：[{...}]
        self.instances: list[dict[str, Any]] = []
        self._load()

    # ---------- 持久化 ----------
    def _load(self) -> None:
        if self.config_file.exists():
            try:
                data = json.loads(self.config_file.read_text(encoding="utf-8"))
                self.settings = data.get("settings", {})
                self.instances = data.get("instances", [])
            except (json.JSONDecodeError, OSError):
                self.settings = {}
                self.instances = []
        else:
            self.settings = {}
            self.instances = []

    def save(self) -> None:
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        data = {"version": APP_VERSION, "settings": self.settings, "instances": self.instances}
        self.config_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---------- 全局设置 ----------
    def get_setting(self, key: str, default: Any = None) -> Any:
        return self.settings.get(key, default)

    def set_setting(self, key: str, value: Any) -> None:
        self.settings[key] = value
        self.save()

    @property
    def source(self) -> str:
        """当前下载源 key。"""
        return self.settings.get("source", "bmclapi")

    @property
    def source_config(self) -> dict:
        return SOURCES.get(self.source, SOURCES["bmclapi"])

    # ---------- 实例 ----------
    def all_instances(self) -> list[dict[str, Any]]:
        return self.instances

    def get_instance(self, inst_id: str) -> Optional[dict[str, Any]]:
        for inst in self.instances:
            if inst.get("id") == inst_id:
                return inst
        return None

    def add_instance(self, inst: dict[str, Any]) -> None:
        self.instances.append(inst)
        self.save()

    def update_instance(self, inst_id: str, **fields: Any) -> bool:
        inst = self.get_instance(inst_id)
        if not inst:
            return False
        inst.update(fields)
        self.save()
        return True

    def remove_instance(self, inst_id: str) -> bool:
        inst = self.get_instance(inst_id)
        if not inst:
            return False
        # 删除实例目录
        import shutil
        inst_dir = self.instances_dir / inst_id
        if inst_dir.exists():
            shutil.rmtree(inst_dir, ignore_errors=True)
        self.instances = [i for i in self.instances if i.get("id") != inst_id]
        self.save()
        return True

    # ---------- 实例目录 ----------
    def instance_dir(self, inst_id: str) -> Path:
        return self.instances_dir / inst_id

    def instance_game_dir(self, inst_id: str) -> Path:
        """每个实例的独立游戏目录（版本分离）。"""
        return self.instances_dir / inst_id / "game"

    # ---------- 便捷 ----------
    def next_instance_id(self) -> str:
        n = len(self.instances) + 1
        while any(i.get("id") == f"instance{n}" for i in self.instances):
            n += 1
        return f"instance{n}"


def new_instance(name: str, version_id: str, source: str) -> dict[str, Any]:
    """创建一个实例的默认数据结构。"""
    import uuid
    return {
        "id": "inst_" + uuid.uuid4().hex[:8],
        "name": name,
        "version": version_id,
        "loader": None,          # "fabric" / "forge" / None
        "loader_version": None,
        "java_path": None,       # 手动指定 Java
        "memory_mb": 2048,       # 分配内存
        "resolution": [1280, 720],
        "auth_type": "offline",  # offline / microsoft
        "username": "",
        "extra_args": [],
        "created": None,
    }

# === downloader.py ===
"""下载引擎：负责网络请求、下载进度回调、重试等基础能力。"""

import hashlib
import io
import time
from pathlib import Path
from typing import Callable, Optional

import requests

# 进度回调：已下载字节, 总字节, 文件路径
ProgressCallback = Callable[[int, int, str], None]


class DownloadError(Exception):
    pass


def _headers() -> dict:
    return {
        "User-Agent": "SFTLauncher/0.1.0",
    }


def http_get(url: str, timeout: float = 30.0) -> bytes:
    try:
        resp = requests.get(url, headers=_headers(), timeout=timeout)
        resp.raise_for_status()
        return resp.content
    except requests.RequestException as e:
        raise DownloadError(f"请求失败 {url}: {e}") from e


def http_get_json(url: str, timeout: float = 30.0, headers: Optional[dict] = None):
    import json
    h = dict(_headers())
    if headers:
        h.update(headers)
    resp = requests.get(url, headers=h, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def sha1_hex(path: Path) -> Optional[str]:
    """计算文件 sha1；文件不存在返回 None。"""
    if not path.exists():
        return None
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 256), b""):
            h.update(chunk)
    return h.hexdigest()


def download_file(url: str, dest: Path, sha1: Optional[str] = None,
                  progress: Optional[ProgressCallback] = None) -> bool:
    """下载文件到 dest。若 sha1 匹配则跳过。返回 True 表示成功/已存在。"""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if sha1 and sha1_hex(dest) == sha1:
        return True

    try:
        resp = requests.get(url, headers=_headers(), timeout=60, stream=True)
        resp.raise_for_status()
        total = int(resp.headers.get("Content-Length") or 0)
        written = 0
        tmp = dest.with_suffix(dest.suffix + ".part")
        with open(tmp, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 128):
                if not chunk:
                    continue
                f.write(chunk)
                written += len(chunk)
                if progress:
                    progress(written, total, str(dest))
        tmp.replace(dest)
        if sha1 and sha1_hex(dest) != sha1:
            raise DownloadError(f"校验失败 {dest.name}")
        return True
    except requests.RequestException as e:
        raise DownloadError(f"下载失败 {dest.name}: {e}") from e


def retry_download(url: str, dest: Path, sha1: Optional[str] = None,
                   progress: Optional[ProgressCallback] = None,
                   retries: int = 3, delay: float = 1.0) -> bool:
    """带重试的下载。"""
    for attempt in range(retries):
        try:
            return download_file(url, dest, sha1, progress)
        except DownloadError:
            if attempt < retries - 1:
                time.sleep(delay)
                continue
            raise
    return False

# === compat.py ===
"""版本 JSON 兼容性解析：库文件规则、参数替换等。

负责将 MC version JSON 中的 library 定义解析为具体的下载目标，
并根据当前系统规则判断该库是否需要加载。
"""

import platform
import re
from typing import Optional

_OS = platform.system().lower()  # windows / darwin / linux
_ARCH = platform.machine().lower()


def _rule_allows(rules: Optional[list]) -> bool:
    """根据 os rules 判断当前系统是否允许该库/参数。

    无 rules 时返回 True。
    """
    if not rules:
        return True
    allow = False
    for rule in rules:
        action = rule.get("action")
        os_rule = rule.get("os", {})
        # 架构匹配
        arch = os_rule.get("arch")
        if arch:
            arch_ok = ("64" in _ARCH) if arch == "x86" else (arch not in ("x86",))
            if arch == "x86" and "64" in _ARCH:
                continue
        os_name = os_rule.get("name")
        version_re = os_rule.get("version")
        os_ok = (os_name is None) or (os_name == _OS)
        if version_re and not re.search(version_re, platform.platform().lower()):
            os_ok = False
        if os_ok and (os_name is None or (arch and arch_ok) or not arch):
            matched = True
        else:
            matched = False
        if action == "allow":
            if matched:
                allow = True
        elif action == "disallow":
            if matched:
                allow = False
    return allow


def parse_library(raw: dict) -> Optional[tuple]:
    """将 version JSON 中的一条 library 解析为
    (name, path, url, sha1, size)；当前系统不适用、为 natives、或仅含 classifier 时返回 None。

    natives（包含平台的动态库）返回 None 交由单独处理。
    """
    if not _rule_allows(raw.get("rules")):
        return None
    if "natives" in raw:
        return None  # 由 natives 下载单独处理
    downloads = raw.get("downloads", {})
    artifact = downloads.get("artifact")
    name = raw.get("name", "")
    # 带 natives classifier 的库（LWJGL3 风格）由 natives 单独处理
    if "natives-" in name:
        return None
    if artifact and artifact.get("path"):
        return (
            name,
            artifact["path"],
            artifact.get("url", ""),
            artifact.get("sha1"),
            artifact.get("size", 0),
        )
    # 无 artifact 的库（老版本）通过 name 推导路径
    path = name_to_path(name)
    if not path:
        return None
    return (name, path, "", None, 0)


def name_to_path(name: str) -> Optional[str]:
    """把 maven 坐标 com.example:foo:1.0 转成相对路径。"""
    parts = name.split(":")
    if len(parts) < 3:
        return None
    group, artifact, version = parts[0], parts[1], parts[2]
    if "@" in version:
        version, ext = version.split("@", 1)
    else:
        ext = "jar"
    return f"{group.replace('.', '/')}/{artifact}/{version}/{artifact}-{version}.{ext}"


# ---------- natives ----------
def _platform_tag() -> str:
    """返回平台标识：windows / linux / osx。"""
    s = _OS
    if s == "darwin":
        return "osx"
    return s


def platform_classifier_name(raw: dict) -> Optional[str]:
    """返回当前平台对应的 natives classifier 文件名（用于下载）。

    支持两种格式：
    - 老风格（LWJGL2）：`natives` 字段 -> 平台 classifier 名
    - LWJGL3 风格：name 中形如 `artifact:natives-windows` 的 classifier
    返回 None 表示不是当前平台的 native 库。
    """
    # 老风格：natives 字段
    natives = raw.get("natives")
    if natives:
        key = _platform_tag()
        if "windows" in _OS and "x86" in _OS and "64" not in _ARCH:
            # 32位windows特殊处理
            pass
        classifier = natives.get(key)
        if classifier and "${arch}" in str(classifier):
            classifier = classifier.replace("${arch}", "64" if "64" in _ARCH else "32")
        return classifier
    # LWJGL3 风格：name 含 :natives-<platform>
    name = raw.get("name", "")
    marker = f"natives-{_platform_tag()}"
    if f":{marker}" in name or f":{marker}-" in name:
        # 需要匹配规则（如 arm64 vs x86）
        if not _rule_allows(raw.get("rules")):
            return None
        if "windows" in _OS:
            # 区分 windows-arm64
            if "arm64" in name and "aarch64" not in _ARCH:
                return None
            if "arm64" not in name and "aarch64" in _ARCH:
                return None
        elif "osx" in name and "darwin" not in _OS:
            return None
        return name.split(":", 3)[3]  # 得到 natives-windows
    return None


def native_download_info(raw: dict, base_url: str = "") -> Optional[tuple]:
    """返回 (下载url, 相对路径, sha1) 或 None（无 natives 或非本平台）。

    优先使用 downloads.classifiers[classifier]；否则从 name 推导。
    """
    cls = platform_classifier_name(raw)
    if not cls:
        return None
    classifiers = raw.get("downloads", {}).get("classifiers", {})
    if cls in classifiers:
        info = classifiers[cls]
        return (info.get("url") or base_url + info.get("path", ""),
                info.get("path"), info.get("sha1"))
    # 推导路径（LWJGL3 名字带 classifier）
    name = raw.get("name", "")
    if ":" in name and "natives" in name:
        parts = name.split(":")
        group, artifact = parts[0], parts[1]
        version = parts[2] if len(parts) >= 3 else ""
        if not version:
            return None
        group_path = group.replace(".", "/")
        path = f"{group_path}/{artifact}/{version}/{artifact}-{version}-{cls}.jar"
        return (base_url + path, path, None)
    return None

# === java_manager.py ===
"""Java 运行时管理：检测本机 Java、按版本需求选择、触发下载提示。

MC 版本与 Java 版本对应关系（简化）：
- 1.16 及以下（不含 1.16.5 某些）：Java 8
- 1.16.5 - 1.20.x：Java 17
- 1.20.5+：Java 21
"""

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional



def java_major_version(path: str) -> Optional[int]:
    """检测给定 java 可执行文件的版本主号，失败返回 None。"""
    try:
        out = subprocess.run([path, "-version"], capture_output=True, text=True, timeout=10)
        text = (out.stdout + out.stderr)
        # 匹配 "version \"1.8.0_xxx\"" 或 "version \"17.0.x\""
        m = re.search(r'version\s+"([^"]+)"', text)
        if not m:
            return None
        ver = m.group(1)
        if ver.startswith("1."):
            return int(ver.split(".")[1])
        return int(ver.split(".")[0])
    except Exception:
        return None


def version_to_java(version_id: str) -> int:
    """根据 MC 版本返回推荐的 Java 主版本（启发式，供离线/无 JSON 时使用）。

    优先级：version JSON 的 javaVersion.majorVersion > 本启发式。
    """
    # 解析主版本号
    m = re.match(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?", version_id)
    if not m:
        return 17
    major = int(m.group(1))
    minor = int(m.group(2) or 0)
    if major == 1:
        if minor <= 16:
            return 8
        elif minor == 17:
            return 16
        elif minor <= 20:
            return 17
        else:
            return 21
    else:  # 1.x+ 新命名，如 25.x / 26.x
        if major >= 26:
            return 25
        elif major >= 25:
            return 25
        return 17


class JavaManager:
    """负责查找可用的 Java。"""

    def __init__(self, config: LauncherConfig):
        self.config = config

    def find_java(self, prefer_version: Optional[int] = None) -> Optional[str]:
        """寻找一个可用的 Java 路径。优先匹配 prefer_version。"""
        candidates: list[str] = []

        # 1. 启动器自管理目录（自动下载的）
        candidates += [str(p) for p in self._bundled_javas()]

        # 2. 本机 JAVA_HOME
        jh = os.environ.get("JAVA_HOME")
        if jh:
            candidates.append(str(Path(jh) / ("bin/java.exe" if os.name == "nt" else "bin/java")))
            candidates.append(str(Path(jh) / ("bin/java" if os.name == "nt" else "bin/java")))

        # 3. PATH 中的 java
        which = shutil.which("java")
        if which:
            candidates.append(which)

        # 4. 常见安装路径（Windows）
        if os.name == "nt":
            pf = Path(os.environ.get("ProgramFiles", "C:/Program Files"))
            pf86 = Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)"))
            for base in (pf / "Java", pf86 / "Java", pf / "Eclipse Adoptium",
                         pf86 / "Eclipse Adoptium", pf / "Microsoft", pf86 / "Microsoft"):
                if base.exists():
                    for sub in base.iterdir():
                        j = sub / "bin" / "java.exe"
                        if j.exists():
                            candidates.append(str(j))

        # 去重并检测版本
        seen = set()
        if prefer_version is not None:
            for c in candidates:
                if c in seen:
                    continue
                seen.add(c)
                if java_major_version(c) == prefer_version:
                    return c
        for c in candidates:
            if c in seen:
                continue
            seen.add(c)
            if java_major_version(c) is not None:
                return c
        return None

    def _bundled_javas(self) -> list[Path]:
        """启动器自管理的 Java 目录中的可执行文件。"""
        results = []
        java_root = self.config.java_dir
        if java_root.exists():
            for sub in java_root.iterdir():
                if sub.is_dir():
                    exe = sub / ("bin/java.exe" if os.name == "nt" else "bin/java")
                    if exe.exists():
                        results.append(exe)
        return results

    def has_any_java(self) -> bool:
        return self.find_java() is not None

# === auth.py ===
"""账号认证：离线账号 + 微软账号（OAuth 设备码流程）。

微软登录链路（四步）：
  1. 微软 OAuth 获取 access_token（设备码流程）
  2. 用 access_token 换 XBL 3.0 token
  3. 用 XBL token 换 XSTS token
  4. 用 XSTS token 换 Minecraft access_token + profile

注意：需要 Azure 应用注册的 Client ID。可自定义，
见 docs/microsoft-auth.md 中的注册说明。
"""

import json
import uuid
from pathlib import Path
from typing import Optional

import requests


# Azure 应用 Client ID（设备码流程）
# 说明：正式发布时请替换为你自己的 Azure 应用注册 Client ID
MS_CLIENT_ID = "00000000-0000-0000-0000-000000000000"
MS_SCOPE = "XboxLive.signin offline_access"
AUTH_URL = "https://login.microsoftonline.com/consumers/oauth2/v2.0/devicecode"
TOKEN_URL = "https://login.microsoftonline.com/consumers/oauth2/v2.0/token"
XBL_URL = "https://user.auth.xboxlive.com/user/authenticate"
XSTS_URL = "https://xsts.auth.xboxlive.com/xsts/authorize"
MC_LOGIN_URL = "https://api.minecraftservices.com/authentication/login_with_xbox"
MC_PROFILE_URL = "https://api.minecraftservices.com/minecraft/profile"


class AuthError(Exception):
    pass


def offline_auth(username: str) -> dict:
    """生成离线账号信息。UUID 由用户名哈希派生，保证同一用户 UUID 稳定。"""
    derived = uuid.uuid5(uuid.NAMESPACE_DNS, f"offline:{username}")
    return {
        "type": "offline",
        "username": username,
        "uuid": str(derived),
        "access_token": "0",
    }


class MicrosoftAuth:
    """微软账号 OAuth（设备码流程）客户端。"""

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.token_file = cache_dir / "microsoft_token.json"

    # ---------- 已保存账号 ----------
    def has_saved_account(self) -> bool:
        return self.token_file.exists()

    def load_saved(self) -> Optional[dict]:
        if not self.token_file.exists():
            return None
        try:
            return json.loads(self.token_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def save_account(self, account: dict) -> None:
        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        self.token_file.write_text(json.dumps(account, ensure_ascii=False, indent=2),
                                   encoding="utf-8")

    def logout(self) -> None:
        if self.token_file.exists():
            self.token_file.unlink()

    # ---------- 设备码流程 ----------
    def request_device_code(self) -> dict:
        """请求设备码，返回 {device_code, user_code, verification_uri, interval, expires_in}。"""
        resp = requests.post(AUTH_URL, data={
            "client_id": MS_CLIENT_ID,
            "scope": MS_SCOPE,
        }, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def poll_token(self, device_code: str, interval: float = 5.0, timeout: float = 600) -> dict:
        """轮询用户是否完成授权，成功后返回微软 token 响应。"""
        import time
        elapsed = 0
        while elapsed < timeout:
            time.sleep(interval)
            elapsed += interval
            resp = requests.post(TOKEN_URL, data={
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "client_id": MS_CLIENT_ID,
                "device_code": device_code,
            }, timeout=30)
            data = resp.json()
            if "access_token" in data:
                return data
            err = data.get("error")
            if err == "authorization_pending":
                continue
            if err == "slow_down":
                interval += 5
                continue
            if err in ("authorization_declined", "expired_token"):
                raise AuthError("用户取消或授权过期")
            raise AuthError(f"授权失败: {data.get('error_description', err)}")
        raise AuthError("授权超时")

    # ---------- 四步兑换 ----------
    def _xbl_token(self, access_token: str) -> str:
        data = http_get_json_post(XBL_URL, {
            "Properties": {
                "AuthMethod": "RPS",
                "SiteName": "user.auth.xboxlive.com",
                "RpsTicket": "d=" + access_token,
            },
            "RelyingParty": "http://auth.xboxlive.com",
            "TokenType": "JWT",
        })
        return data["Token"]

    def _xsts_token(self, xbl_token: str) -> str:
        data = http_get_json_post(XSTS_URL, {
            "Properties": {"SandboxId": "RETAIL", "UserTokens": [xbl_token]},
            "RelyingParty": "rp://api.minecraftservices.com/",
            "TokenType": "JWT",
        })
        return data["Token"]

    def _mc_token(self, xsts_token: str) -> dict:
        data = http_get_json_post(MC_LOGIN_URL, {"identityToken": "XBL3.0 x=" + xsts_token})
        return data  # {username, access_token, token_type, expires_in}

    def _mc_profile(self, mc_token: str) -> dict:
        return http_get_json(MC_PROFILE_URL, headers={"Authorization": "Bearer " + mc_token})

    # ---------- 完整登录 ----------
    def login_device_flow(self, device_code: dict) -> dict:
        """在用户已授权后，用 device_code 完成微软登录，返回 MC 账号信息。"""
        tokens = self.poll_token(device_code["device_code"])
        return self.finish_login(tokens["access_token"])

    def finish_login(self, ms_access_token: str) -> dict:
        """从微软 access_token 完成到 MC 账号的完整兑换。"""
        xbl = self._xbl_token(ms_access_token)
        xsts = self._xsts_token(xbl)
        mc = self._mc_token(xsts)
        profile = self._mc_profile(mc["access_token"])
        account = {
            "type": "microsoft",
            "username": profile.get("name", mc.get("username", "Steve")),
            "uuid": profile.get("id"),
            "access_token": mc["access_token"],
            "mc_expires_in": mc.get("expires_in"),
            "refresh_token": None,  # 需要 oauth refresh_token，暂用 access_token 直登
        }
        self.save_account(account)
        return account

    def refresh_account(self, account: dict) -> Optional[dict]:
        """尝试用已有账号刷新（简化：直接复用 access_token）。"""
        return account


def http_get_json_post(url: str, payload: dict, headers: Optional[dict] = None) -> dict:
    """POST JSON 并返回 JSON（用于 XBL/XSTS/MC 接口）。"""
    h = {"Content-Type": "application/json", "Accept": "application/json"}
    if headers:
        h.update(headers)
    resp = requests.post(url, json=payload, headers=h, timeout=30)
    resp.raise_for_status()
    return resp.json()

# === version.py ===
"""版本管理：拉取版本清单、下载版本 JSON、库文件、资源对象。"""

import json
from pathlib import Path
from typing import Callable, Optional


# 进度回调：(已完成, 总数, 当前文件名)
TaskProgress = Callable[[int, int, str], None]


class VersionManager:
    """负责版本清单与版本文件的下载。"""

    def __init__(self, config: LauncherConfig):
        self.config = config
        self._manifest_cache: Optional[dict] = None

    # ---------- 版本清单 ----------
    def _manifest_path(self) -> Path:
        return self.config.cache_dir / "version_manifest_v2.json"

    def fetch_version_manifest(self, force: bool = False, timeout: float = 30.0) -> dict:
        """获取版本清单（内存缓存 + 磁盘缓存）。

        优先使用内存缓存；若磁盘有缓存则先用之，同时尝试网络刷新。
        网络失败时回退到磁盘缓存。
        """
        if self._manifest_cache and not force:
            return self._manifest_cache
        # 磁盘缓存
        disk = self._manifest_path()
        if disk.exists() and not force:
            try:
                data = json.loads(disk.read_text(encoding="utf-8"))
                self._manifest_cache = data
            except (json.JSONDecodeError, OSError):
                data = None
        else:
            data = None
        # 尝试网络刷新
        try:
            url = self.config.source_config["version_manifest"]
            fresh = http_get_json(url, timeout=timeout)
            self._manifest_cache = fresh
            disk.parent.mkdir(parents=True, exist_ok=True)
            disk.write_text(json.dumps(fresh, ensure_ascii=False), encoding="utf-8")
            return fresh
        except Exception:
            if data is not None:
                return data
            raise

    def list_versions(self, timeout: float = 30.0) -> list[dict]:
        """返回版本列表：[{id, type, url, time}]，release 在前。"""
        manifest = self.fetch_version_manifest(timeout=timeout)
        versions = manifest.get("versions", [])
        # release 优先，按时间排序
        order = {"release": 0, "snapshot": 1, "old_beta": 2, "old_alpha": 3}
        versions = sorted(
            versions,
            key=lambda v: (order.get(v.get("type"), 9), v.get("time", ""), v.get("id", "")),
        )
        return versions

    def latest_version_id(self) -> Optional[str]:
        manifest = self.fetch_version_manifest()
        latest = manifest.get("latest", {})
        return latest.get("release") or latest.get("snapshot")
    # ---------- 版本 JSON ----------
    def version_dir(self, version_id: str) -> Path:
        return self.config.versions_dir / version_id

    def version_json_path(self, version_id: str) -> Path:
        return self.version_dir(version_id) / f"{version_id}.json"

    def version_jar_path(self, version_id: str) -> Path:
        return self.version_dir(version_id) / f"{version_id}.jar"

    def get_version_json(self, version_id: str, fetch_if_missing: bool = True) -> dict:
        """读取本地版本 JSON；不存在则从清单 URL 拉取。"""
        path = self.version_json_path(version_id)
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        if not fetch_if_missing:
            raise FileNotFoundError(f"版本 {version_id} 未下载")
        url = self._version_url(version_id)
        if not url:
            raise DownloadError(f"未找到版本 {version_id} 的下载地址")
        data = http_get_json(url)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return data

    def _version_url(self, version_id: str) -> Optional[str]:
        for v in self.list_versions():
            if v.get("id") == version_id:
                return v.get("url")
        return None

    # ---------- 版本完整性检查 ----------
    def version_files_present(self, version_id: str) -> bool:
        """检查版本 jar 是否已下载。"""
        return self.version_jar_path(version_id).exists()

    # ---------- 下载完整版本 ----------
    def download_version(self, version_id: str,
                         progress: Optional[TaskProgress] = None) -> None:
        """下载版本 jar + 全部库文件 + 资源对象。

        若已下载完成则跳过（通过 sha1 判断）。
        """
        vjson = self.get_version_json(version_id)
        total_tasks = 1  # jar
        # 统计库文件
        total_tasks += len(self._libraries_needed(vjson))
        # 统计资源对象（客户端需要的）
        assets = self._asset_index(vjson)
        total_tasks += self._assets_needed_count(assets)
        done = 0

        def tick(name: str):
            nonlocal done
            done += 1
            if progress:
                progress(done, total_tasks, name)

        # 1. 版本 jar
        jar_url = vjson.get("downloads", {}).get("client", {}).get("url")
        jar_sha1 = vjson.get("downloads", {}).get("client", {}).get("sha1")
        if jar_url:
            jar_path = self.version_jar_path(version_id)
            retry_download(jar_url, jar_path, jar_sha1)
        tick(f"{version_id}.jar")

        # 2. 库文件
        for lib in self._libraries_needed(vjson):
            self._download_library(lib)
            tick(lib.name)

        # 3. natives（平台动态库，解压到 natives 目录）
        self._download_natives(version_id, vjson)
        tick("natives")

        # 4. 资源对象
        self._download_assets(assets)
        tick("assets")

    # ---------- natives ----------
    def natives_dir(self, version_id: str) -> Path:
        return self.config.cache_dir / f"natives-{version_id}"

    def _download_natives(self, version_id: str, vjson: dict) -> None:
        """下载并解压平台 native 库到 natives 目录。

        支持 LWJGL2（natives 字段）和 LWJGL3（name classifier）两种格式。
        """
        from .compat import native_download_info
        import zipfile
        import shutil

        natives_dir = self.natives_dir(version_id)
        natives_dir.mkdir(parents=True, exist_ok=True)
        base = self.config.source_config.get("library_base", "https://libraries.minecraft.net/")
        tmp_dir = self.config.cache_dir / "_native_dl"
        tmp_dir.mkdir(parents=True, exist_ok=True)

        errors = []
        for raw in vjson.get("libraries", []):
            info = native_download_info(raw, base)
            if not info:
                continue
            url, rel_path, sha1 = info
            dest = tmp_dir / Path(rel_path).name
            try:
                retry_download(url, dest, sha1)
            except DownloadError as e:
                errors.append(f"{rel_path}: {e}")
                continue
            try:
                with zipfile.ZipFile(dest) as zf:
                    for member in zf.namelist():
                        if member.startswith("META-INF/"):
                            continue
                        if member.endswith("/"):
                            continue
                        target = natives_dir / member
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with zf.open(member) as src, open(target, "wb") as out:
                            shutil.copyfileobj(src, out)
            except Exception as e:
                errors.append(f"解压 {rel_path}: {e}")
                continue
        if errors:
            # 记录但不阻断（个别 native 失败不至于导致整个版本无法启动）
            try:
                (self.config.logs_dir / "native_errors.log").write_text(
                    "\n".join(errors), encoding="utf-8")
            except OSError:
                pass

    # ---------- 库文件 ----------
    class _Library:
        def __init__(self, name: str, path: str, url: str, sha1: Optional[str], size: int):
            self.name = name
            self.path = path  # 相对 libraries 目录的路径
            self.url = url
            self.sha1 = sha1
            self.size = size

    def _libraries_needed(self, vjson: dict) -> list["_Library"]:
        """解析 version JSON 中需要下载的库文件。"""
        from .compat import parse_library
        libs = []
        for raw in vjson.get("libraries", []):
            parsed = parse_library(raw)
            if parsed is None:
                continue
            libs.append(self._Library(*parsed))
        return libs

    def _download_library(self, lib: "_Library") -> None:
        dest = self.config.libraries_dir / lib.path
        if lib.sha1 and _sha1_matches(dest, lib.sha1):
            return
        # 优先使用下载源的库基址，回退到原始 url
        base = self.config.source_config.get("library_base")
        url = lib.url
        if base and lib.path.startswith("com/"):
            url = base + lib.path
        retry_download(url, dest, lib.sha1)

    # ---------- 资源对象 (assets) ----------
    def _asset_index(self, vjson: dict) -> Optional[dict]:
        assets_info = vjson.get("assetIndex", {})
        if not assets_info:
            return None
        index_path = self.config.resources_dir / "indexes" / (assets_info.get("id") + ".json")
        if index_path.exists():
            return json.loads(index_path.read_text(encoding="utf-8"))
        data = http_get_json(assets_info["url"])
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return data

    def _assets_needed_count(self, assets: Optional[dict]) -> int:
        if not assets:
            return 0
        objs = assets.get("objects", {})
        return sum(1 for k, v in objs.items() if not v.get("virtual"))

    def _download_assets(self, assets: Optional[dict]) -> None:
        if not assets:
            return
        base = self.config.source_config.get("resource_base", "https://resources.download.minecraft.net/")
        objs = assets.get("objects", {})
        for key, meta in objs.items():
            if meta.get("virtual"):
                continue
            h = meta.get("hash")
            if not h:
                continue
            dest = self.config.resources_dir / "objects" / h[:2] / h
            if dest.exists():
                continue
            url = base + h[:2] + "/" + h
            try:
                retry_download(url, dest, h)
            except DownloadError:
                # 单个资源失败不阻断整个流程
                continue


def _sha1_matches(path: Path, sha1: str) -> bool:
    from .downloader import sha1_hex
    try:
        return sha1_hex(path) == sha1
    except Exception:
        return False

# === launcher.py ===
"""游戏启动：组装参数、启动进程、离线/微软账号。

启动参数组装逻辑遵循 MC 官方 version JSON 中的 arguments / minecraftArguments。
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional



class GameLaunchError(Exception):
    pass


class GameLauncher:
    """负责将实例启动为 Minecraft 进程。"""

    def __init__(self, config: LauncherConfig):
        self.config = config
        self.vm = VersionManager(config)
        self.jm = JavaManager(config)

    # ---------- 启动主入口 ----------
    def launch(self, instance: dict, auth: dict) -> subprocess.Popen:
        """启动游戏。auth 包含账号信息（offline/microsoft）。

        auth: {"type": "offline"|"microsoft", "username": "...", "uuid": "...", "access_token": "..."}
        """
        version_id = instance["version"]
        vjson = self.vm.get_version_json(version_id)

        # 确保版本已下载
        if not self.vm.version_files_present(version_id):
            raise GameLaunchError("游戏版本未下载完成，请先下载")

        # 选择 Java
        java_exe = instance.get("java_path")
        if not java_exe:
            # 优先使用 version JSON 的权威 javaVersion，否则用启发式
            jv = vjson.get("javaVersion")
            prefer = jv.get("majorVersion") if jv else version_to_java(version_id)
            java_exe = self.jm.find_java(prefer)
        if not java_exe:
            raise GameLaunchError("未找到可用的 Java，请在设置中指定 Java 路径或下载 Java")

        # 组装启动命令
        cmd = self._build_command(instance, vjson, java_exe, auth)
        game_dir = self.config.instance_game_dir(instance["id"])
        game_dir.mkdir(parents=True, exist_ok=True)

        # 写日志
        log_path = self.config.logs_dir / f"{instance['id']}.log"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write("\n===== 启动 " + instance["name"] + " =====\n")
            f.write(" ".join(cmd) + "\n")

        kwargs = {}
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
        proc = subprocess.Popen(
            cmd, cwd=str(game_dir),
            stdout=open(log_path, "a", encoding="utf-8", errors="replace"),
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            **kwargs,
        )
        return proc

    # ---------- 组装命令 ----------
    def _build_command(self, instance: dict, vjson: dict, java_exe: str, auth: dict) -> list[str]:
        game_dir = self.config.instance_game_dir(instance["id"])
        version_id = instance["version"]

        classpath = self._build_classpath(instance, vjson)
        mem = int(instance.get("memory_mb", 2048))
        res_w, res_h = instance.get("resolution", [1280, 720])
        user = auth.get("username", "Steve")
        uuid = auth.get("uuid", "00000000-0000-0000-0000-000000000000")
        access_token = auth.get("access_token", "0")
        auth_type = auth.get("type", "offline")

        # 基础 java 参数
        base = [
            java_exe,
            f"-Xms{mem}M",
            f"-Xmx{mem}M",
            "-Djava.library.path=" + str(self._natives_path(instance, vjson)),
            "-Dminecraft.launcher.brand=sftlauncher",
            "-Dminecraft.launcher.version=0.1.0",
        ]

        # 从 version json 取 arguments / minecraftArguments
        tail: list[str] = []
        arguments = vjson.get("arguments")
        if arguments and "game" in arguments:
            tail = self._expand_args(arguments["game"], instance, vjson, auth)
        else:
            # 老版本：minecraftArguments
            legacy = vjson.get("minecraftArguments")
            if legacy:
                tail = self._expand_legacy(legacy, game_dir, version_id, user, uuid,
                                           access_token, res_w, res_h)

        full = base + self._clean_tail(tail)
        return [str(x) for x in full]

    @staticmethod
    def _clean_tail(tail: list[str]) -> list[str]:
        """清理孤立的快速启动（quickPlay）参数：删除丢失了值的 --quickPlay* 标志。"""
        cleaned: list[str] = []
        skip_next = False
        for arg in tail:
            if skip_next:
                skip_next = False
                continue
            if arg.startswith("--quickPlay"):
                skip_next = True  # 跳过该 flag 及紧随其后的值
                continue
            cleaned.append(arg)
        return cleaned

    def _expand_args(self, args: list, instance: dict, vjson: dict, auth: dict) -> list[str]:
        """展开新版 arguments.game 中的规则和变量。"""
        game_dir = self.config.instance_game_dir(instance["id"])
        version_id = instance["version"]
        user = auth.get("username", "Steve")
        uuid = auth.get("uuid", "00000000-0000-0000-0000-000000000000")
        access_token = auth.get("access_token", "0")
        res_w, res_h = instance.get("resolution", [1280, 720])

        result: list[str] = []
        for item in args:
            if isinstance(item, str):
                expanded = self._substitute(item, game_dir, version_id, user, uuid,
                                            access_token, res_w, res_h)
                if self._is_resolved(expanded):
                    result.append(expanded)
            elif isinstance(item, dict):
                # 带规则的对象：只展开适用的
                rules = item.get("rules")
                if rules and not self._rules_allow(rules):
                    continue
                values = item.get("value")
                if isinstance(values, str):
                    values = [values]
                for val in values or []:
                    expanded = self._substitute(val, game_dir, version_id, user, uuid,
                                                access_token, res_w, res_h)
                    if self._is_resolved(expanded):
                        result.append(expanded)
        return result

    @staticmethod
    def _is_resolved(s: str) -> bool:
        """含未替换占位符的参数（如 ${quickPlayPath}）不传给游戏。"""
        return "${" not in s

    def _substitute(self, s: str, game_dir, version_id, user, uuid, access_token, w, h) -> str:
        reps = {
            "${version_name}": version_id,
            "${version_type}": "release",
            "${game_directory}": str(game_dir),
            "${assets_root}": str(self.config.resources_dir),
            "${assets_index_name}": self._asset_index_name(version_id),
            "${auth_player_name}": user,
            "${auth_session}": "token:" + access_token + ":" + uuid,
            "${auth_access_token}": access_token,
            "${auth_uuid}": uuid,
            "${clientid}": "00000000-0000-0000-0000-000000000000",
            "${resolution_width}": str(w),
            "${resolution_height}": str(h),
            "${user_type}": "legacy",
            "${user_properties}": "{}",
            "${version_type}": "release",
            "${natives_directory}": str(self._natives_path_for(version_id)),
            "${classpath_separator}": os.pathsep,
            "${auth_xuid}": "0",
            "${launcher_name}": "sftlauncher",
            "${launcher_version}": "0.1.0",
        }
        for k, v in reps.items():
            s = s.replace(k, v)
        return s

    def _expand_legacy(self, legacy: str, game_dir, version_id, user, uuid, access_token, w, h) -> list[str]:
        s = self._substitute(legacy, game_dir, version_id, user, uuid, access_token, w, h)
        # 拆分成参数
        return s.split()

    def _rules_allow(self, rules: list) -> bool:
        from .compat import _rule_allows
        return _rule_allows(rules)

    # ---------- classpath ----------
    def _build_classpath(self, instance: dict, vjson: dict) -> str:
        cp = []
        # 版本 jar
        cp.append(str(self.vm.version_jar_path(instance["version"])))
        # 库文件
        from .compat import parse_library, name_to_path
        for raw in vjson.get("libraries", []):
            parsed = parse_library(raw)
            if parsed is None:
                continue
            _, path, url, sha1, size = parsed
            lib_path = self.config.libraries_dir / path
            if lib_path.exists():
                cp.append(str(lib_path))
        return os.pathsep.join(cp)

    # ---------- natives ----------
    def _natives_path(self, instance: dict, vjson: dict) -> str:
        return self._natives_path_for(instance["version"])

    def _natives_path_for(self, version_id: str) -> Path:
        return self.config.cache_dir / f"natives-{version_id}"
    def _asset_index_name(self, version_id: str) -> str:
        try:
            vjson = self.vm.get_version_json(version_id)
            return vjson.get("assetIndex", {}).get("id", "legacy")
        except Exception:
            return "legacy"

# === app.py ===
"""应用上下文：协调各核心模块的单例入口。"""



class App:
    """启动器全局应用对象。"""

    def __init__(self, root=None):
        self.config = LauncherConfig(root)
        self.versions = VersionManager(self.config)
        self.java = JavaManager(self.config)
        self.launcher = GameLauncher(self.config)
        self.auth = MicrosoftAuth(self.config.cache_dir)

    # 便捷转发
    @property
    def instances(self):
        return self.config.instances
