"""SFT 启动器 - 主入口。"""
from __future__ import annotations

import sys
import os


def main():
    # 确保可导入 src
    here = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(here, "src")
    if src not in sys.path:
        sys.path.insert(0, src)

    from PyQt6.QtWidgets import QApplication
    from core.app import App
    from gui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("SFTLauncher")
    app.setApplicationVersion("0.1.0")

    core_app = App()
    window = MainWindow(core_app)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
