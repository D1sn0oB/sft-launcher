
# === gui/__init__.py ===
# GUI 模块

# === gui/theme.py ===
"""全局样式（QSS）：现代深色卡片风格。"""
from __future__ import annotations

# 主题色板
COLORS = {
    "bg": "#1e2128",
    "bg_alt": "#262a33",
    "card": "#2b2f3a",
    "card_hover": "#333846",
    "border": "#3a3f4e",
    "text": "#e8eaef",
    "text_dim": "#9aa0af",
    "accent": "#4f8cff",
    "accent_hover": "#6b9dff",
    "accent_press": "#3f74d6",
    "success": "#4caf7d",
    "danger": "#e05b5b",
    "warning": "#e0a34e",
}

QSS = f"""
* {{
    font-family: "Microsoft YaHei", "PingFang SC", "Segoe UI", sans-serif;
    font-size: 13px;
    color: {COLORS['text']};
}}
QMainWindow, QWidget#root {{
    background-color: {COLORS['bg']};
}}
/* 侧边栏 */
QWidget#sidebar {{
    background-color: {COLORS['bg_alt']};
    border-right: 1px solid {COLORS['border']};
}}
QLabel#sidebar_title {{
    color: {COLORS['accent']};
    font-size: 17px;
    font-weight: bold;
    padding: 20px 16px 12px 20px;
}}
QPushButton#nav_btn {{
    background: transparent;
    border: none;
    text-align: left;
    padding: 12px 20px;
    font-size: 14px;
    color: {COLORS['text_dim']};
    border-radius: 0;
}}
QPushButton#nav_btn:hover {{
    background: {COLORS['card']};
    color: {COLORS['text']};
}}
QPushButton#nav_btn:checked {{
    background: {COLORS['card_hover']};
    color: {COLORS['accent']};
    border-left: 3px solid {COLORS['accent']};
}}
/* 内容区 */
QWidget#content {{
    background-color: {COLORS['bg']};
}}
QLabel#page_title {{
    font-size: 22px;
    font-weight: bold;
    color: {COLORS['text']};
}}
QLabel#page_subtitle {{
    color: {COLORS['text_dim']};
    font-size: 13px;
}}
/* 卡片 */
QFrame#card {{
    background-color: {COLORS['card']};
    border: 1px solid {COLORS['border']};
    border-radius: 10px;
}}
QFrame#card:hover {{
    background-color: {COLORS['card_hover']};
}}
QLabel#card_title {{
    font-size: 15px;
    font-weight: bold;
}}
QLabel#card_desc {{
    color: {COLORS['text_dim']};
}}
QLabel#badge {{
    background-color: rgba(79,140,255,0.15);
    color: {COLORS['accent']};
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 11px;
}}
/* 按钮 */
QPushButton {{
    background-color: {COLORS['accent']};
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 18px;
    font-size: 13px;
}}
QPushButton:hover {{ background-color: {COLORS['accent_hover']}; }}
QPushButton:pressed {{ background-color: {COLORS['accent_press']}; }}
QPushButton#ghost {{
    background-color: transparent;
    border: 1px solid {COLORS['border']};
    color: {COLORS['text']};
}}
QPushButton#ghost:hover {{ background-color: {COLORS['card_hover']}; border-color: {COLORS['accent']}; }}
QPushButton#danger {{
    background-color: transparent;
    border: 1px solid {COLORS['danger']};
    color: {COLORS['danger']};
}}
QPushButton#danger:hover {{ background-color: rgba(224,91,91,0.1); }}
/* 输入框 */
QLineEdit, QComboBox, QSpinBox {{
    background-color: {COLORS['bg']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 8px 10px;
    color: {COLORS['text']};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
    border-color: {COLORS['accent']};
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
/* 滚动区 */
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QAbstractScrollArea::viewport {{ background: transparent; }}
QScrollBar:vertical {{
    background: transparent; width: 8px; margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {COLORS['border']}; border-radius: 4px; min-height: 30px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
/* 进度条 */
QProgressBar {{
    background-color: {COLORS['bg']};
    border: none;
    border-radius: 5px;
    height: 10px;
    text-align: center;
}}
QProgressBar::chunk {{
    background-color: {COLORS['accent']};
    border-radius: 5px;
}}
/* 状态栏 */
QStatusBar {{ background: {COLORS['bg_alt']}; color: {COLORS['text_dim']}; }}
/* 分割线 */
QFrame#hsep {{ background: {COLORS['border']}; max-height: 1px; }}
QLabel#dim {{ color: {COLORS['text_dim']}; }}
QLabel#empty_icon {{ color: {COLORS['border']}; font-size: 48px; }}
QCheckBox {{ color: {COLORS['text']}; }}
"""

# === gui/widgets.py ===
"""可复用 UI 组件：卡片、空状态、标题栏等。"""

from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtWidgets import (
    QFrame, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QWidget,
)


class VersionListWorker(QThread):
    """后台加载版本清单（带磁盘缓存回退，不阻塞 UI）。"""
    finished = pyqtSignal(list, str)

    def __init__(self, app):
        super().__init__()
        self.app = app

    def run(self):
        try:
            versions = self.app.versions.list_versions(timeout=8.0)
            self.finished.emit(versions, "")
        except Exception as e:
            self.finished.emit([], f"无法加载版本列表：{e}")


def make_card() -> QFrame:
    """创建一个标准卡片容器。"""
    card = QFrame()
    card.setObjectName("card")
    return card


class Card(QFrame):
    """可点击的卡片容器，无内置布局，由调用方自行填充。"""
    clicked = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._data = None

    def set_data(self, data):
        self._data = data

    def data(self):
        return self._data

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self)
        super().mousePressEvent(e)


class EmptyState(QWidget):
    """空状态提示。"""
    def __init__(self, icon="▢", title="暂无内容", desc="", parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ic = QLabel(icon)
        ic.setObjectName("empty_icon")
        ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(ic)
        t = QLabel(title)
        t.setObjectName("page_title")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(t)
        if desc:
            d = QLabel(desc)
            d.setObjectName("dim")
            d.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lay.addWidget(d)

# === gui/pages/loader.py ===
"""模组加载器安装对话框（Fabric / Forge）。"""

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QProgressBar, QMessageBox,
)


class LoaderInstallWorker(QThread):
    """后台安装加载器线程。"""
    progress = pyqtSignal(str)
    done = pyqtSignal(bool, str)

    def __init__(self, installer, kind, mcver, loader_ver):
        super().__init__()
        self.installer = installer
        self.kind = kind
        self.mcver = mcver
        self.loader_ver = loader_ver

    def run(self):
        try:
            if self.kind == "fabric":
                ver_id = self.installer.install(self.mcver, self.loader_ver,
                                                progress=lambda *a: self.progress.emit(a[0]))
            else:
                ver_id = self.installer.install(self.mcver, self.loader_ver,
                                                progress=lambda *a: self.progress.emit(a[0]))
            self.done.emit(True, ver_id)
        except Exception as e:
            self.done.emit(False, str(e))


class LoaderInstallDialog(QDialog):
    """选择加载器类型与版本并安装。"""

    def __init__(self, app, parent, inst):
        super().__init__(parent)
        self.app = app
        self.inst = inst
        self.setWindowTitle(f"安装模组加载器 - {inst['name']}")
        self.setMinimumWidth(460)
        lay = QVBoxLayout(self)
        lay.setSpacing(12)

        t = QLabel("模组加载器")
        t.setObjectName("page_title")
        lay.addWidget(t)

        d = QLabel(f"为实例「{inst['name']}」（MC {inst['version']}）安装模组加载器。\n"
                   "安装后可在启动器下载 Fabric/Forge 模组。")
        d.setObjectName("dim")
        d.setWordWrap(True)
        lay.addWidget(d)

        # 类型选择
        lay.addWidget(self._field("加载器类型"))
        self.kind_combo = QComboBox()
        self.kind_combo.addItem("Fabric", "fabric")
        self.kind_combo.addItem("Forge", "forge")
        self.kind_combo.currentIndexChanged.connect(self._load_versions)
        lay.addWidget(self.kind_combo)

        # 版本选择
        lay.addWidget(self._field("加载器版本"))
        self.version_combo = QComboBox()
        lay.addWidget(self.version_combo)

        # 进度
        self.bar = QProgressBar()
        self.bar.setVisible(False)
        self.bar.setRange(0, 0)  # 不确定进度
        lay.addWidget(self.bar)
        self.status = QLabel("")
        self.status.setObjectName("dim")
        self.status.setWordWrap(True)
        lay.addWidget(self.status)

        btns = QHBoxLayout()
        self.install_btn = QPushButton("安装")
        self.install_btn.clicked.connect(self._install)
        btns.addWidget(self.install_btn)
        self.cancel_btn = QPushButton("关闭")
        self.cancel_btn.setObjectName("ghost")
        self.cancel_btn.clicked.connect(self.reject)
        btns.addWidget(self.cancel_btn)
        lay.addLayout(btns)

        self._worker = None
        self._load_versions()

    def _field(self, text):
        l = QLabel(text)
        l.setObjectName("dim")
        return l

    def _load_versions(self):
        """根据类型加载版本列表。"""
        kind = self.kind_combo.currentData()
        self.version_combo.clear()
        self.version_combo.addItem("加载中...", None)
        self.install_btn.setEnabled(False)
        try:
            if kind == "fabric":
                from mods.fabric import FabricInstaller
                installer = FabricInstaller(self.app.config, self.app.versions)
                loaders = installer.list_loaders(self.inst["version"])
                self.version_combo.clear()
                for l in loaders[:40]:
                    label = l["loader_version"]
                    self.version_combo.addItem(label, l["loader_version"])
                self._fabric = installer
            else:
                from mods.forge import ForgeInstaller
                installer = ForgeInstaller(self.app.config, self.app.versions)
                vers = installer.list_versions(self.inst["version"])
                self.version_combo.clear()
                for v in vers[:40]:
                    self.version_combo.addItem(v["version_id"], v["forge_version"])
                self._forge = installer
        except Exception as e:
            self.version_combo.clear()
            self.version_combo.addItem(f"无法加载：{e}", None)
        self.install_btn.setEnabled(True)

    def _install(self):
        kind = self.kind_combo.currentData()
        ver = self.version_combo.currentData()
        if not ver:
            QMessageBox.warning(self, "提示", "请选择一个加载器版本")
            return
        installer = self._fabric if kind == "fabric" else self._forge
        self.install_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        self.bar.setVisible(True)
        self.status.setText("正在安装...")

        self._worker = LoaderInstallWorker(installer, kind, self.inst["version"], ver)
        self._worker.progress.connect(lambda s: self.status.setText(s))
        self._worker.done.connect(self._on_done)
        self._worker.start()

    def _on_done(self, ok, msg):
        self.bar.setVisible(False)
        self.install_btn.setEnabled(True)
        self.cancel_btn.setEnabled(True)
        if ok:
            # 更新实例的版本为加载器版本
            ver_id = msg
            self.app.config.update_instance(self.inst["id"], version=ver_id,
                                            loader=self.kind_combo.currentData())
            self.status.setText(f"安装成功：{ver_id}")
            QMessageBox.information(self, "安装成功",
                                    f"加载器已安装，版本：{ver_id}\n现在可以下载对应的模组了。")
            self.accept()
        else:
            self.status.setText(f"安装失败：{msg}")
            QMessageBox.warning(self, "安装失败", msg)

# === gui/pages/home.py ===
"""首页：多实例卡片列表 + 启动/新增/删除。"""

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QGridLayout, QLineEdit, QComboBox, QDialog, QMessageBox, QDialogButtonBox,
)

from core import new_instance
from core import GameLaunchError
from core import offline_auth


class HomePage(QWidget):
    def __init__(self, app, window):
        super().__init__()
        self.app = app
        self.window = window
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(16)

        # 顶部：标题 + 操作按钮
        top = QHBoxLayout()
        left = QVBoxLayout()
        left.setSpacing(2)
        t = QLabel("我的实例")
        t.setObjectName("page_title")
        left.addWidget(t)
        sub = QLabel("创建和管理你的游戏实例")
        sub.setObjectName("page_subtitle")
        left.addWidget(sub)
        top.addLayout(left)
        top.addStretch()

        # 账号状态 + 登录按钮
        self.account_label = QLabel()
        self.account_label.setObjectName("dim")
        top.addWidget(self.account_label)
        self.login_btn = QPushButton()
        self.login_btn.setObjectName("ghost")
        self.login_btn.clicked.connect(self._toggle_login)
        top.addWidget(self.login_btn)

        add_btn = QPushButton("＋ 新建实例")
        add_btn.setObjectName("ghost")
        add_btn.clicked.connect(self._open_new_dialog)
        top.addWidget(add_btn)
        lay.addLayout(top)
        self._update_account_ui()

    def _update_account_ui(self):
        saved = self.app.auth.load_saved()
        if saved:
            self.account_label.setText(f"微软账号：{saved.get('username', '')}")
            self.login_btn.setText("退出登录")
        else:
            self.account_label.setText("未登录")
            self.login_btn.setText("微软登录")

    def _toggle_login(self):
        saved = self.app.auth.load_saved()
        if saved:
            ret = QMessageBox.question(self, "退出登录", "确定退出微软账号登录吗？")
            if ret == QMessageBox.StandardButton.Yes:
                self.app.auth.logout()
                self._update_account_ui()
                self.window.notify("已退出微软登录")
            return
        self._do_microsoft_login()

    def _do_microsoft_login(self):
        """微软设备码登录流程。"""
        try:
            dc = self.app.auth.request_device_code()
        except Exception as e:
            QMessageBox.warning(self, "登录失败", f"无法发起登录：{e}")
            return
        # 打开浏览器
        try:
            import webbrowser
            webbrowser.open(dc["verification_uri"])
        except Exception:
            pass
        # 显示设备码等待用户授权
        dlg = MsAuthDialog(self, dc, self.app.auth)
        dlg.exec()
        self._update_account_ui()
        self._refresh()

        # 实例卡片滚动区
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.cards_host = QWidget()
        self.cards_grid = QGridLayout(self.cards_host)
        self.cards_grid.setContentsMargins(0, 0, 8, 8)
        self.cards_grid.setSpacing(14)
        self.cards_grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self.cards_host)
        lay.addWidget(scroll, 1)

        self._refresh()

    def refresh(self):
        self._refresh()

    def _refresh(self):
        # 清空网格
        while self.cards_grid.count():
            item = self.cards_grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        instances = self.app.config.all_instances()
        if not instances:
            empty = EmptyState(
                icon="⛏",
                title="还没有实例",
                desc="点击右上角「新建实例」创建你的第一个游戏实例",
            )
            self.cards_grid.addWidget(empty, 0, 0)
            return

        versions = {}
        try:
            for v in self.app.versions.list_versions():
                versions[v["id"]] = v
        except Exception:
            pass

        for i, inst in enumerate(instances):
            card = self._make_instance_card(inst, versions)
            r, c = divmod(i, 2)
            self.cards_grid.addWidget(card, r, c)

    def _make_instance_card(self, inst, versions):
        card = Card()
        card.setObjectName("card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(8)

        # 名称 + 徽章
        top = QHBoxLayout()
        name = QLabel(inst["name"])
        name.setObjectName("card_title")
        top.addWidget(name)
        top.addStretch()
        ver_badge = QLabel(inst["version"])
        ver_badge.setObjectName("badge")
        top.addWidget(ver_badge)
        lay.addLayout(top)

        # 描述
        loader = inst.get("loader") or "原版"
        info = QLabel(f"加载器：{loader} · 内存：{inst.get('memory_mb', 2048)}MB")
        info.setObjectName("dim")
        lay.addWidget(info)

        # 按钮
        btns = QHBoxLayout()
        launch = QPushButton("启动游戏")
        launch.clicked.connect(lambda _=False, i=inst: self._launch(i))
        btns.addWidget(launch)
        loader_btn = QPushButton("安装加载器")
        loader_btn.setObjectName("ghost")
        loader_btn.clicked.connect(lambda _=False, i=inst: self._install_loader(i))
        btns.addWidget(loader_btn)
        btns.addStretch()
        del_btn = QPushButton("删除")
        del_btn.setObjectName("danger")
        del_btn.clicked.connect(lambda _=False, i=inst: self._delete(i))
        btns.addWidget(del_btn)
        lay.addLayout(btns)
        return card

    def _install_loader(self, inst):
        dlg = LoaderInstallDialog(self.app, self, inst)
        dlg.exec()
        self._refresh()

    # ---------- 新建实例 ----------
    def _open_new_dialog(self):
        dlg = NewInstanceDialog(self.app, self)
        dlg.exec()

    def _launch(self, inst):
        # 组装账号信息
        auth_type = inst.get("auth_type", "offline")
        if auth_type == "offline":
            auth = offline_auth(inst.get("username") or "Steve")
        else:
            # 微软账号：使用已保存的微软账号
            saved = self.app.auth.load_saved()
            if not saved:
                QMessageBox.information(
                    self, "需要登录",
                    "该实例设为微软登录，但尚未登录微软账号。\n"
                    "请先在首页点击「微软登录」完成登录后再启动。")
                return
            auth = saved
        try:
            self.window.notify(f"正在启动 {inst['name']} ...")
            proc = self.app.launcher.launch(inst, auth)
            self.window.notify(f"已启动 {inst['name']}（PID {proc.pid}）")
        except GameLaunchError as e:
            QMessageBox.warning(self, "启动失败", str(e))

    def _delete(self, inst):
        ret = QMessageBox.question(self, "删除实例",
                                   f"确定删除实例「{inst['name']}」吗？\n该实例的所有数据将被清除。")
        if ret == QMessageBox.StandardButton.Yes:
            self.app.config.remove_instance(inst["id"])
            self._refresh()


class MsAuthDialog(QDialog):
    """微软登录等待授权对话框（设备码流程）。"""
    def __init__(self, parent, device_code, auth_mgr):
        super().__init__(parent)
        self.auth_mgr = auth_mgr
        self.setWindowTitle("微软登录")
        self.setMinimumWidth(460)
        self.setModal(True)
        lay = QVBoxLayout(self)
        lay.setSpacing(10)

        t = QLabel("微软账号登录")
        t.setObjectName("page_title")
        lay.addWidget(t)

        d = QLabel("请在浏览器中打开授权页面，并输入下面的设备代码完成登录。")
        d.setObjectName("dim")
        d.setWordWrap(True)
        lay.addWidget(d)

        code = QLabel(device_code["user_code"])
        code.setStyleSheet(
            "font-size:28px;font-weight:bold;color:#4f8cff;"
            "background:#262a33;border-radius:8px;padding:16px;"
        )
        code.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(code)

        url = QLabel(device_code["verification_uri"])
        url.setObjectName("dim")
        url.setWordWrap(True)
        url.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lay.addWidget(url)

        self.status = QLabel("等待授权...")
        self.status.setObjectName("dim")
        lay.addWidget(self.status)

        cancel = QPushButton("取消")
        cancel.setObjectName("ghost")
        cancel.clicked.connect(self.reject)
        lay.addWidget(cancel)

        # 后台轮询线程
        self._worker = MsPollWorker(self.auth_mgr, device_code)
        self._worker.done.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_done(self, account):
        self.status.setText(f"登录成功：{account.get('username', '')}")
        QTimer.singleShot(800, self.accept)

    def _on_error(self, msg):
        self.status.setText(f"失败：{msg}")


class MsPollWorker(QThread):
    """后台轮询微软授权状态。"""
    done = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, auth_mgr, device_code):
        super().__init__()
        self.auth_mgr = auth_mgr
        self.device_code = device_code

    def run(self):
        from core import AuthError
        try:
            account = self.auth_mgr.login_device_flow(self.device_code)
            self.done.emit(account)
        except AuthError as e:
            self.error.emit(str(e))
        except Exception as e:
            self.error.emit(str(e))


class NewInstanceDialog(QDialog):
    """新建实例对话框。"""
    def __init__(self, app, parent):
        super().__init__(parent)
        self.app = app
        self.setWindowTitle("新建实例")
        self.setMinimumWidth(420)
        lay = QVBoxLayout(self)
        lay.setSpacing(12)

        lay.addWidget(self._field("实例名称"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("例如：我的生存服")
        lay.addWidget(self.name_edit)

        lay.addWidget(self._field("游戏版本"))
        self.version_combo = QComboBox()
        lay.addWidget(self.version_combo)
        self._load_versions()

        lay.addWidget(self._field("分配内存 (MB)"))
        self.mem_spin = _make_mem_spin()
        lay.addWidget(self.mem_spin)

        lay.addWidget(self._field("离线用户名"))
        self.user_edit = QLineEdit("Steve")
        lay.addWidget(self.user_edit)

        lay.addWidget(self._field("登录方式"))
        self.auth_combo = QComboBox()
        self.auth_combo.addItem("离线模式", "offline")
        self.auth_combo.addItem("微软账号", "microsoft")
        lay.addWidget(self.auth_combo)
        self.auth_combo.currentIndexChanged.connect(self._on_auth_change)

        btns = QDialogButtonBox()
        ok = btns.addButton("创建", QDialogButtonBox.ButtonRole.AcceptRole)
        cancel = btns.addButton("取消", QDialogButtonBox.ButtonRole.RejectRole)
        ok.clicked.connect(self._create)
        cancel.clicked.connect(self.reject)
        lay.addWidget(btns)

    def _field(self, text):
        l = QLabel(text)
        l.setObjectName("dim")
        return l

    def _load_versions(self):
        try:
            versions = self.app.versions.list_versions()
            for v in versions:
                if v["type"] in ("release", "snapshot"):
                    self.version_combo.addItem(f"{v['id']}  ({v['type']})", v["id"])
            # 默认选最新 release
            latest = self.app.versions.latest_version_id()
            idx = self.version_combo.findData(latest)
            if idx >= 0:
                self.version_combo.setCurrentIndex(idx)
        except Exception as e:
            self.version_combo.addItem("无法加载版本列表")
            self.warn = str(e)

    def _create(self):
        name = self.name_edit.text().strip() or "未命名实例"
        version_id = self.version_combo.currentData()
        if not version_id:
            QMessageBox.warning(self, "提示", "请选择一个游戏版本")
            return
        inst = new_instance(name, version_id, self.app.config.source)
        inst["memory_mb"] = self.mem_spin.value()
        inst["username"] = self.user_edit.text().strip() or "Steve"
        inst["auth_type"] = self.auth_combo.currentData() or "offline"
        inst["created"] = None
        self.app.config.add_instance(inst)
        self.app.config.instance_game_dir(inst["id"]).mkdir(parents=True, exist_ok=True)
        self.accept()
        # 刷新父页面
        parent = self.parent()
        if hasattr(parent, "refresh"):
            parent.refresh()

    def _on_auth_change(self, idx):
        # 离线模式下可编辑用户名，微软账号使用已登录账号
        self.user_edit.setEnabled(idx == 0)


def _make_mem_spin():
    from PyQt6.QtWidgets import QSpinBox
    s = QSpinBox()
    s.setRange(512, 16384)
    s.setSingleStep(512)
    s.setValue(2048)
    s.setSuffix(" MB")
    return s

# === gui/pages/versions.py ===
"""版本下载页面：浏览版本、下载版本、查看进度。"""

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QGridLayout, QLineEdit, QMessageBox,
)

from core import DownloadError


class DownloadWorker(QThread):
    """后台下载线程。"""
    progress = pyqtSignal(int, int, str)
    done = pyqtSignal(bool, str)

    def __init__(self, app, version_id):
        super().__init__()
        self.app = app
        self.version_id = version_id

    def run(self):
        try:
            self.app.versions.download_version(
                self.version_id, progress=self.progress.emit)
            self.done.emit(True, "下载完成")
        except DownloadError as e:
            self.done.emit(False, str(e))
        except Exception as e:
            self.done.emit(False, f"未知错误: {e}")


class VersionsPage(QWidget):
    def __init__(self, app, window):
        super().__init__()
        self.app = app
        self.window = window
        self.versions_cache = []
        self.workers = {}
        self._progress_bars = {}
        self._list_worker = None
        self._build()
        self.refresh_async()

    def refresh_async(self):
        """后台加载版本列表，避免阻塞 UI。"""
        if self._list_worker and self._list_worker.isRunning():
            return
        from ..widgets import VersionListWorker
        self._list_worker = VersionListWorker(self.app)
        self._list_worker.finished.connect(self._on_list_loaded)
        self._list_worker.start()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(16)

        top = QHBoxLayout()
        left = QVBoxLayout()
        left.setSpacing(2)
        t = QLabel("版本下载")
        t.setObjectName("page_title")
        left.addWidget(t)
        sub = QLabel(f"当前源：{self.app.config.source_config['label']}")
        sub.setObjectName("page_subtitle")
        left.addWidget(sub)
        top.addLayout(left)
        top.addStretch()
        refresh_btn = QPushButton("刷新列表")
        refresh_btn.setObjectName("ghost")
        refresh_btn.clicked.connect(self.refresh)
        top.addWidget(refresh_btn)
        lay.addLayout(top)

        # 搜索框
        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索版本...")
        self.search.textChanged.connect(self._render)
        lay.addWidget(self.search)

        # 列表
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.host = QWidget()
        self.grid = QGridLayout(self.host)
        self.grid.setContentsMargins(0, 0, 8, 8)
        self.grid.setSpacing(10)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self.host)
        lay.addWidget(scroll, 1)

    def refresh(self):
        """手动刷新入口。"""
        self.refresh_async()

    def _on_list_loaded(self, versions, error):
        if error:
            QMessageBox.warning(self, "加载失败", error)
        self.versions_cache = versions or []
        self._render()

    def _render(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        query = self.search.text().strip().lower()
        versions = [v for v in self.versions_cache if query in v["id"].lower()]
        if not versions:
            self.grid.addWidget(EmptyState(icon="⬇", title="没有找到版本", desc="换个关键词试试"), 0, 0)
            return

        for i, v in enumerate(versions):
            r, c = divmod(i, 2)
            self.grid.addWidget(self._version_card(v), r, c)

    def _version_card(self, v):
        v_id = v["id"]
        card = Card()
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(8)

        top = QHBoxLayout()
        name = QLabel(v_id)
        name.setObjectName("card_title")
        top.addWidget(name)
        top.addStretch()
        badge = QLabel(v["type"])
        badge.setObjectName("badge")
        top.addWidget(badge)
        lay.addLayout(top)

        # 下载状态
        downloaded = self.app.versions.version_files_present(v_id)
        status = QLabel("已下载" if downloaded else f"发布于 {v.get('time', '')[:10]}")
        status.setObjectName("dim")
        lay.addWidget(status)

        # 进度条（若有）
        if v_id in self.workers:
            from PyQt6.QtWidgets import QProgressBar
            bar = QProgressBar()
            bar.setObjectName("dlbar")
            bar.setRange(0, 100)
            bar.setValue(0)
            lay.addWidget(bar)
            self._progress_bars[v_id] = bar

        btn_row = QHBoxLayout()
        if downloaded:
            btn = QPushButton("重新下载")
            btn.setObjectName("ghost")
        else:
            btn = QPushButton("下载")
        btn.clicked.connect(lambda _=False, vid=v_id: self._start_download(vid))
        btn_row.addWidget(btn)
        btn_row.addStretch()
        lay.addLayout(btn_row)
        return card

    def _start_download(self, v_id):
        if v_id in self.workers:
            return
        worker = DownloadWorker(self.app, v_id)
        worker.progress.connect(lambda d, t, name: self._on_progress(v_id, d, t, name))
        worker.done.connect(lambda ok, msg: self._on_done(v_id, ok, msg))
        self.workers[v_id] = worker
        worker.start()
        self.window.notify(f"开始下载 {v_id} ...")
        self._render()

    def _on_progress(self, v_id, done, total, name):
        bar = getattr(self, "_progress_bars", {}).get(v_id)
        if bar:
            pct = int(done * 100 / total) if total else 0
            bar.setValue(pct)
            bar.setFormat(f"{pct}% · {name}")
        self.window.notify(f"下载中：{name}")

    def _on_done(self, v_id, ok, msg):
        self.workers.pop(v_id, None)
        if ok:
            self.window.notify(f"{v_id} {msg}")
        else:
            QMessageBox.warning(self, "下载失败", f"{v_id}: {msg}")
        self._render()

# === gui/pages/settings.py ===
"""设置页面：下载源切换、Java 选择、外观等。"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QFileDialog, QMessageBox, QGroupBox,
)

from core import SOURCES
from core import java_major_version


class SettingsPage(QWidget):
    def __init__(self, app, window):
        super().__init__()
        self.app = app
        self.window = window
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(16)

        t = QLabel("设置")
        t.setObjectName("page_title")
        lay.addWidget(t)
        sub = QLabel("启动器全局配置")
        sub.setObjectName("page_subtitle")
        lay.addWidget(sub)

        # 下载源
        src_box = QGroupBox("下载源")
        src_lay = QVBoxLayout(src_box)
        src_h = QHBoxLayout()
        self.src_combo = QComboBox()
        for key, info in SOURCES.items():
            self.src_combo.addItem(info["label"], key)
        cur = self.app.config.source
        idx = self.src_combo.findData(cur)
        if idx >= 0:
            self.src_combo.setCurrentIndex(idx)
        self.src_combo.currentIndexChanged.connect(self._on_source_change)
        src_h.addWidget(self.src_combo, 1)
        src_h.addStretch()
        src_lay.addLayout(src_h)
        src_note = QLabel("国内网络建议使用 BMCLAPI 镜像，速度更快。")
        src_note.setObjectName("dim")
        src_lay.addWidget(src_note)
        lay.addWidget(src_box)

        # Java
        java_box = QGroupBox("Java 运行时")
        java_lay = QVBoxLayout(java_box)
        java_row = QHBoxLayout()
        self.java_label = QLabel("未检测到 Java")
        self.java_label.setWordWrap(True)
        java_row.addWidget(self.java_label, 1)
        detect_btn = QPushButton("重新检测")
        detect_btn.setObjectName("ghost")
        detect_btn.clicked.connect(self._detect_java)
        java_row.addWidget(detect_btn)
        manual_btn = QPushButton("手动选择")
        manual_btn.setObjectName("ghost")
        manual_btn.clicked.connect(self._pick_java)
        java_row.addWidget(manual_btn)
        java_lay.addLayout(java_row)
        java_note = QLabel("启动器会根据游戏版本自动选择对应 Java 版本。")
        java_note.setObjectName("dim")
        java_lay.addWidget(java_note)
        lay.addWidget(java_box)

        # CurseForge API Key
        cf_box = QGroupBox("CurseForge API Key")
        cf_lay = QVBoxLayout(cf_box)
        from PyQt6.QtWidgets import QLineEdit
        self.cf_key_edit = QLineEdit()
        self.cf_key_edit.setPlaceholderText("填入 CurseForge API Key 以启用下载中心（可选）")
        self.cf_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.cf_key_edit.setText(self.app.config.get_setting("curseforge_key", ""))
        self.cf_key_edit.editingFinished.connect(self._save_cf_key)
        cf_lay.addWidget(self.cf_key_edit)
        cf_note = QLabel("没有 Key 也能用 Modrinth 下载。获取方式见 docs/curseforge-api.md。")
        cf_note.setObjectName("dim")
        cf_note.setWordWrap(True)
        cf_lay.addWidget(cf_note)
        lay.addWidget(cf_box)

        # 关于
        about_box = QGroupBox("关于")
        about_lay = QVBoxLayout(about_box)
        about = QLabel(
            "SFT 启动器 v0.1.0（测试版）\n"
            "功能：多实例 · 版本下载 · 离线/微软登录 · 模组加载器 · Mod 下载\n"
            "本软件为开源工具，与 Mojang 无关。")
        about.setWordWrap(True)
        about_lay.addWidget(about)
        lay.addWidget(about_box)

        lay.addStretch()
        self._detect_java()

    def _save_cf_key(self):
        self.app.config.set_setting("curseforge_key", self.cf_key_edit.text().strip())
        self.window.notify("CurseForge API Key 已保存")

    def _on_source_change(self, idx):
        key = self.src_combo.itemData(idx)
        if key:
            self.app.config.set_setting("source", key)
            self.window.notify(f"下载源已切换为 {SOURCES[key]['label']}")

    def _detect_java(self):
        java = self.app.java.find_java()
        if java:
            ver = java_major_version(java)
            self.java_label.setText(f"已找到 Java {ver}：{java}")
            self.window.notify("Java 检测完成")
        else:
            self.java_label.setText("未检测到 Java，可在设置中手动指定路径。")
            self.java_label.setStyleSheet("color:#e0a34e;")

    def _pick_java(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择 java 可执行文件",
            "", "Java 可执行文件 (java.exe java)")
        if path:
            ver = java_major_version(path)
            if ver is None:
                QMessageBox.warning(self, "无效", "所选文件不是有效的 Java 可执行文件")
                return
            self.app.config.set_setting("java_path", path)
            self.java_label.setText(f"已指定 Java {ver}：{path}")
            self.window.notify("Java 路径已保存")

# === gui/pages/mods.py ===
"""下载中心：搜索并下载 Mod / 资源包（Modrinth + CurseForge）。"""

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QLineEdit, QComboBox, QProgressBar, QMessageBox,
)



class SearchWorker(QThread):
    """后台搜索线程。搜索结果附带来源平台。"""
    finished = pyqtSignal(list, str, str)  # results, error, platform_used

    def __init__(self, client, query, project_type, mc_ver, loader, platform):
        super().__init__()
        self.client = client
        self.query = query
        self.project_type = project_type
        self.mc_ver = mc_ver
        self.loader = loader
        self.platform = platform  # 目标平台

    def run(self):
        platform_used = self.platform
        try:
            if isinstance(self.client, ModrinthClient):
                results = self.client.search(self.query, project_type=self.project_type,
                                             mc_version=self.mc_ver or None,
                                             loader=self.loader or None)
                self.finished.emit(results, "", platform_used)
            else:
                # CurseForge
                pt = 6 if self.project_type == "mod" else 12
                try:
                    results = self.client.search(self.query, project_type=pt,
                                                 game_version=self.mc_ver or None)
                    self.finished.emit(results, "", "curseforge")
                except Exception as cf_err:
                    # CurseForge 失败/限流 → 自动降级到 Modrinth
                    self.finished.emit([], str(cf_err), "curseforge_failed")
        except Exception as e:
            self.finished.emit([], str(e), platform_used)


class DownloadFileWorker(QThread):
    """后台下载线程。"""
    progress = pyqtSignal(int, int)
    done = pyqtSignal(bool, str)

    def __init__(self, client, file, dest_dir):
        super().__init__()
        self.client = client
        self.file = file
        self.dest_dir = dest_dir

    def run(self):
        try:
            path = self.client.download_to(self.file, self.dest_dir,
                                           progress=self.progress.emit)
            self.done.emit(True, path)
        except Exception as e:
            self.done.emit(False, str(e))


from api import ModrinthClient


class ModsPage(QWidget):
    def __init__(self, app, window):
        super().__init__()
        self.app = app
        self.window = window
        self._workers = []
        self._current_source = "Modrinth"
        self._build()
        self._load_instances()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(16)

        top = QHBoxLayout()
        left = QVBoxLayout()
        left.setSpacing(2)
        t = QLabel("下载中心")
        t.setObjectName("page_title")
        left.addWidget(t)
        sub = QLabel("从 Modrinth / CurseForge 下载 Mod 和资源包")
        sub.setObjectName("page_subtitle")
        left.addWidget(sub)
        top.addLayout(left)
        top.addStretch()
        lay.addLayout(top)

        # 筛选栏
        filter_row = QHBoxLayout()
        self.instance_combo = QComboBox()
        self.instance_combo.setMinimumWidth(160)
        self.instance_combo.setPlaceholderText("选择实例")
        filter_row.addWidget(self.instance_combo)
        self.type_combo = QComboBox()
        self.type_combo.addItem("Mod", "mod")
        self.type_combo.addItem("资源包", "resourcepack")
        filter_row.addWidget(self.type_combo)
        self.platform_combo = QComboBox()
        self.platform_combo.addItem("Modrinth", "modrinth")
        self.platform_combo.addItem("CurseForge", "curseforge")
        filter_row.addWidget(self.platform_combo)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索 Mod / 资源包...")
        self.search_edit.returnPressed.connect(self._search)
        filter_row.addWidget(self.search_edit, 1)
        search_btn = QPushButton("搜索")
        search_btn.clicked.connect(self._search)
        filter_row.addWidget(search_btn)
        lay.addLayout(filter_row)

        # 提示
        hint = QLabel("提示：下载的 Mod 会保存到所选实例的 mods / resourcepacks 目录（版本分离）")
        hint.setObjectName("dim")
        lay.addWidget(hint)

        # 结果
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.results_host = QWidget()
        self.results_lay = QVBoxLayout(self.results_host)
        self.results_lay.setContentsMargins(0, 0, 8, 8)
        self.results_lay.setSpacing(10)
        self.results_lay.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self.results_host)
        lay.addWidget(scroll, 1)

    def _load_instances(self):
        self.instance_combo.clear()
        self.instance_combo.addItem("（仅浏览，不安装）", None)
        for inst in self.app.config.all_instances():
            self.instance_combo.addItem(inst["name"], inst)

    def _current_instance(self):
        return self.instance_combo.currentData()

    def _client(self):
        platform = self.platform_combo.currentData()
        if platform == "modrinth":
            return ModrinthClient()
        else:
            from api import CurseForgeClient
            key = self.app.config.get_setting("curseforge_key", "")
            return CurseForgeClient(key)

    def _search(self):
        query = self.search_edit.text().strip()
        if not query:
            return
        client = self._client()
        inst = self._current_instance()
        mc_ver = inst["version"] if inst else None
        loader = inst.get("loader") if inst else None
        project_type = self.type_combo.currentData()
        platform = self.platform_combo.currentData()
        from api import CurseForgeClient
        if isinstance(client, CurseForgeClient) and not client.available:
            QMessageBox.information(
                self, "未配置 API Key",
                "CurseForge 需要 API Key。\n请在「设置」页填写 CurseForge API Key，\n或改用 Modrinth（无需配置）。")
            return
        worker = SearchWorker(client, query, project_type, mc_ver, loader, platform)
        worker.finished.connect(self._on_search_done)
        worker.start()
        self._workers.append(worker)
        self.window.notify(f"搜索：{query} ...")

    def _on_search_done(self, results, error, platform_used):
        # 清空结果
        while self.results_lay.count():
            item = self.results_lay.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        # CurseForge 失败/限流 → 自动降级到 Modrinth
        if platform_used == "curseforge_failed":
            self.window.notify("CurseForge 暂不可用，已自动切换到 Modrinth")
            # 自动用 Modrinth 重新搜索
            client = ModrinthClient()
            inst = self._current_instance()
            mc_ver = inst["version"] if inst else None
            loader = inst.get("loader") if inst else None
            project_type = self.type_combo.currentData()
            query = self.search_edit.text().strip()
            worker = SearchWorker(client, query, project_type, mc_ver, loader, "modrinth")
            worker.finished.connect(self._on_search_done)
            worker.start()
            self._workers.append(worker)
            return

        if error:
            QMessageBox.warning(self, "搜索失败", error)
            return
        if not results:
            self.results_lay.addWidget(EmptyState(icon="🔍", title="没有找到结果",
                                                  desc="换个关键词或筛选条件试试"))
            return

        # 显示来源平台标识
        src_label = "Modrinth" if platform_used == "modrinth" else "CurseForge"
        if platform_used != "modrinth":
            pass
        self._current_source = src_label
        for r in results:
            self.results_lay.addWidget(self._result_card(r, src_label))

    def _result_card(self, result, source="Modrinth"):
        card = Card()
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(6)

        top = QHBoxLayout()
        title = QLabel(result.get("title") or result.get("name") or "未知")
        title.setObjectName("card_title")
        top.addWidget(title)
        top.addStretch()
        src = QLabel(source)
        src.setObjectName("badge")
        if source == "CurseForge":
            src.setStyleSheet("background-color:rgba(224,163,78,0.18);color:#e0a34e;border-radius:4px;padding:2px 8px;font-size:11px;")
        top.addWidget(src)
        dl = QLabel(f"下载 {result.get('downloads', 0):,}")
        dl.setObjectName("badge")
        top.addWidget(dl)
        lay.addLayout(top)

        desc = (result.get("description") or result.get("summary") or "").strip()
        if desc:
            d = QLabel(desc[:120] + ("..." if len(desc) > 120 else ""))
            d.setObjectName("card_desc")
            d.setWordWrap(True)
            lay.addWidget(d)

        author = result.get("author") or result.get("slug") or ""
        if author:
            a = QLabel(f"作者：{author}")
            a.setObjectName("dim")
            lay.addWidget(a)

        # 下载按钮 + 进度
        btn_row = QHBoxLayout()
        install_btn = QPushButton("下载到实例")
        install_btn.clicked.connect(lambda _=False, r=result: self._download(r))
        btn_row.addWidget(install_btn)
        bar = QProgressBar()
        bar.setVisible(False)
        bar.setRange(0, 100)
        btn_row.addWidget(bar, 1)
        lay.addLayout(btn_row)
        # 存储进度条引用
        card._dl_bar = bar
        card._dl_btn = install_btn
        return card

    def _download(self, result):
        inst = self._current_instance()
        if not inst:
            QMessageBox.information(self, "提示", "请先在上方选择目标实例")
            return
        # 根据结果来源平台选择客户端（兼容降级场景）
        source = getattr(self, "_current_source", "Modrinth")
        if source == "CurseForge":
            from api import CurseForgeClient
            client = CurseForgeClient(self.app.config.get_setting("curseforge_key", ""))
        else:
            client = ModrinthClient()
        project_type = self.type_combo.currentData()
        mc_ver = inst["version"]
        loader = inst.get("loader")
        # 解析版本并选文件
        try:
            if isinstance(client, ModrinthClient):
                file = client.pick_best_file(result["slug"], mc_ver, loader)
            else:
                file = client.pick_best_file(result["id"], mc_ver)
        except Exception as e:
            QMessageBox.warning(self, "获取版本失败", str(e))
            return
        if not file:
            QMessageBox.information(self, "无可用版本",
                                    f"该内容没有适配 MC {mc_ver} 的版本。")
            return
        # 目标目录（版本分离）
        game_dir = self.app.config.instance_game_dir(inst["id"])
        dest_dir = game_dir / ("mods" if project_type == "mod" else "resourcepacks")
        dest_dir.mkdir(parents=True, exist_ok=True)
        # 下载
        worker = DownloadFileWorker(client, file, dest_dir)
        worker.progress.connect(self._on_dl_progress)
        worker.done.connect(self._on_dl_done)
        worker.start()
        self._workers.append(worker)
        self.window.notify(f"正在下载 {file['filename']} ...")

    def _on_dl_progress(self, done, total):
        # 简化：状态栏显示
        pass

    def _on_dl_done(self, ok, msg):
        if ok:
            self.window.notify("下载完成：" + msg)
            QMessageBox.information(self, "下载完成", f"已保存到：\n{msg}")
        else:
            QMessageBox.warning(self, "下载失败", msg)

# === gui/main_window.py ===
"""主窗口：侧边栏导航 + 页面切换。"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QStackedWidget, QButtonGroup,
)

from core import App

NAV_ITEMS = [
    ("首页", "home"),
    ("版本下载", "versions"),
    ("下载中心", "mods"),
    ("设置", "settings"),
]


class MainWindow(QMainWindow):
    def __init__(self, app: App):
        super().__init__()
        self.app = app
        self.setWindowTitle("SFT 启动器")
        self.resize(1080, 720)
        self.setMinimumSize(900, 600)
        self.setStyleSheet(QSS)

        central = QWidget()
        central.setObjectName("root")
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 侧边栏
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(200)
        sb_lay = QVBoxLayout(sidebar)
        sb_lay.setContentsMargins(0, 0, 0, 0)
        sb_lay.setSpacing(4)
        title = QLabel("SFT 启动器")
        title.setObjectName("sidebar_title")
        sb_lay.addWidget(title)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.pages = QStackedWidget()
        self.nav_map = {}  # key -> button

        # 注册页面（模块内自建导航按钮）
        self._build_pages()

        for key in ("home", "versions", "mods", "settings"):
            btn = self.nav_map.get(key)
            if btn:
                sb_lay.addWidget(btn)
        sb_lay.addStretch()
        ver = QLabel("v0.1.0 · 测试版")
        ver.setObjectName("dim")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sb_lay.addWidget(ver)

        root.addWidget(sidebar)
        root.addWidget(self.pages, 1)

        # 默认选中首页
        if self.nav_map:
            self.nav_map["home"].setChecked(True)

        self.statusBar().showMessage("就绪")

    def _build_pages(self):
        pages_defs = [
            (HomePage, "home", "首页"),
            (VersionsPage, "versions", "版本下载"),
            (ModsPageProxy, "mods", "下载中心"),
            (SettingsPage, "settings", "设置"),
        ]
        for cls, key, label in pages_defs:
            page = cls(self.app, self)
            self.pages.addWidget(page)
            btn = QPushButton(label)
            btn.setObjectName("nav_btn")
            btn.setCheckable(True)
            self.nav_group.addButton(btn)
            self.nav_map[key] = btn
            btn.clicked.connect(lambda _=False, k=key: self.switch_page(k))

    def switch_page(self, key):
        order = {"home": 0, "versions": 1, "mods": 2, "settings": 3}
        idx = order.get(key, 0)
        self.pages.setCurrentIndex(idx)
        # 高亮对应导航
        if key in self.nav_map:
            self.nav_map[key].setChecked(True)

    def notify(self, msg):
        self.statusBar().showMessage(msg, 5000)


# 下载中心页面（阶段 5 实现，先占位）
class ModsPageProxy(QWidget):
    def __init__(self, app: App, window):
        super().__init__()
        from .pages.mods import ModsPage
        # 直接复用真正的下载中心页面
        self._impl = ModsPage(app, window)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._impl)
