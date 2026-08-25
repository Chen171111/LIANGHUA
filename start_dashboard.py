"""AI 量化研投平台 Web Dashboard 一键启动入口（仓库内，进 git）。

双击 / 命令行运行即可在浏览器打开交互式仪表盘：
    python start_dashboard.py
"""
import os
import sys
import threading
import time
import webbrowser

# 确保无论从何目录运行都能 import 到 quantplatform 包
_SELF = os.path.dirname(os.path.abspath(__file__))      # quantplatform 目录
_PARENT = os.path.dirname(_SELF)                         # pytrader 目录
for _p in (_SELF, _PARENT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

PORT = int(os.environ.get("QP_PORT", "8000"))
URL = "http://127.0.0.1:{}".format(PORT)


def _open_browser():
    time.sleep(1.5)
    try:
        webbrowser.open(URL)
    except Exception:
        pass


def main():
    try:
        from quantplatform.api.server import create_app, _HAS_WEB
        import uvicorn
        if not _HAS_WEB:
            raise RuntimeError("缺少 fastapi / uvicorn")
        app = create_app()
    except Exception as e:
        print("\n[启动失败] 缺少依赖：", e)
        print("请先执行: pip install fastapi \"uvicorn[standard]\" akshare pandas numpy")
        print("或在标机上执行: pip install -r requirements.txt")
        input("按回车退出...")
        return 1

    print("=" * 56)
    print("  AI 量化研投平台  Web Dashboard")
    print("  地址: %s" % URL)
    print("  关闭窗口或在终端按 Ctrl+C 即可停止服务")
    print("=" * 56)

    threading.Thread(target=_open_browser, daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="info")
    return 0


if __name__ == "__main__":
    sys.exit(main())