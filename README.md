# WorkBuddy MC 启动器

一个基于 Python + PyQt6 的 Minecraft Java 版启动器，目标平台 Windows，支持打包为 `.exe`。

## 功能

- **多实例管理**：每个实例独立配置，版本分离（mod / 资源包 / 光影独立目录）
- **版本下载**：任意 MC 版本，Mojang 官方源 + BMCLAPI 国内镜像可切换
- **离线登录**：免账号，输入用户名即可玩（离线 UUID 稳定）
- **微软登录**：微软账号 OAuth 设备码流程（见 docs/microsoft-auth.md）
- **模组加载器**：一键安装 Fabric / Forge
- **下载中心**：从 Modrinth（免配置）/ CurseForge 搜索下载 Mod 与资源包
- **Java 自动管理**：按游戏版本自动推荐对应 Java（8/16/17/21/25）
- **下载引擎**：SHA1 校验、断点重试、natives 自动解压

## 运行

### 源码运行
```bash
pip install PyQt6 requests
python main.py
```

### 打包为 exe（Windows）
双击运行 `build.bat`，生成 `dist/WorkBuddyMC启动器.exe`。

> 详细使用说明见 `docs/使用说明.md`。

## 项目结构

```
mc-launcher/
├── main.py                 # 入口
├── mc-launcher.spec        # PyInstaller 打包配置
├── build.bat               # Windows 一键打包脚本
├── requirements.txt
├── docs/                   # 文档
│   ├── 使用说明.md
│   ├── microsoft-auth.md   # 微软登录配置
│   └── curseforge-api.md   # CurseForge Key 配置
└── src/
    ├── core/               # 核心引擎
    │   ├── app.py          # 应用上下文
    │   ├── auth.py         # 账号认证（离线/微软）
    │   ├── compat.py       # MC 版本 JSON / natives 解析
    │   ├── config.py       # 配置与多实例管理
    │   ├── downloader.py   # 下载器
    │   ├── java_manager.py # Java 检测
    │   ├── launcher.py     # 游戏启动命令组装
    │   └── version.py      # 版本下载管理
    ├── gui/                # 图形界面 (PyQt6)
    │   ├── main_window.py  # 主窗口 + 侧边栏导航
    │   ├── theme.py        # 深色卡片主题
    │   ├── widgets.py      # 复用组件
    │   └── pages/
    │       ├── home.py     # 首页（实例管理 + 登录）
    │       ├── versions.py # 版本下载
    │       ├── mods.py     # 下载中心
    │       ├── loader.py   # 加载器安装
    │       └── settings.py # 设置
    ├── api/                # 第三方 API
    │   ├── modrinth.py     # Modrinth 客户端
    │   └── curseforge.py   # CurseForge 客户端
    └── mods/               # 模组加载器
        ├── fabric.py
        └── forge.py
```

## 数据目录

数据保存在用户目录下 `.mc-launcher/`：
- `versions/` 游戏版本
- `libraries/` 库文件
- `resources/` 资源对象
- `instances/<id>/game/` 各实例独立游戏目录
- `java/` 自动下载的 Java
- `cache/` natives 等缓存
- `logs/` 启动日志

## 开发状态

v0.1.0 已完成全部核心功能（版本下载、启动、加载器、下载中心、打包配置）。
打包需要在 Windows 上运行 `build.bat` 生成 `.exe`。
