"""AI 量化研投平台 Web API + Dashboard。

启动：
    python -m quantplatform.api.server --port 8000
    # 打开 http://127.0.0.1:8000/
"""
import sys
from pathlib import Path

# 若系统未安装 fastapi/uvicorn，则尝试使用项目内隔离的 _vendor 目录
_VENDOR = Path(__file__).resolve().parent.parent / "_vendor"
if _VENDOR.exists() and str(_VENDOR) not in sys.path:
    sys.path.insert(0, str(_VENDOR))

try:
    from fastapi import FastAPI, Query
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import HTMLResponse, FileResponse, Response
    import uvicorn
    _HAS_WEB = True
except ImportError:
    _HAS_WEB = False

from ..pipeline import run_backtest
from ..strategies.registry import list_strategies
from ..config import DEFAULT_CONFIG


def create_app() -> "FastAPI":
    if not _HAS_WEB:
        raise RuntimeError("缺少 FastAPI/uvicorn，请执行: pip install fastapi uvicorn")
    app = FastAPI(title="AI 量化研投平台", version="0.1.0")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                       allow_headers=["*"])
    dash_path = Path(__file__).resolve().parent.parent / "dashboard" / "index.html"

    @app.get("/", response_class=HTMLResponse)
    def index():
        if dash_path.exists():
            return FileResponse(str(dash_path))
        return "<h1>AI 量化研投平台</h1><p>未找到 dashboard</p>"

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon():
        # 返回内联 SVG 图标，避免浏览器 404 噪音
        svg = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">' \
             b'<rect width="24" height="24" rx="4" fill="#2b3a67"/>' \
             b'<text x="12" y="16" font-size="11" fill="#fff" text-anchor="middle" ' \
             b'font-family="sans-serif">Q</text></svg>'
        return Response(content=svg, media_type="image/svg+xml")

    @app.get("/api/health")
    def health():
        return {"status": "ok", "strategies": list_strategies()}

    @app.get("/api/strategies")
    def strategies():
        return {"strategies": list_strategies()}

    @app.get("/api/pools")
    def pools():
        from ..dataprovider.store import RECOMMENDED_POOLS, fetch_index_cons_sample
        items = [{"name": k, "codes": v} for k, v in RECOMMENDED_POOLS.items()]
        items.append({"name": "个股动量", "codes": fetch_index_cons_sample(n=20)})
        # 仅注册这些；额外指标池可再加
        return {"pools": [i for i in items],
                "strategies": list_strategies()}

    @app.api_route("/api/backtest", methods=["GET", "POST"])
    def backtest(
        codes: str = Query(None, description="标的代码，逗号分隔(与 pool 二选一)"),
        strategy: str = Query("multifactor"),
        start: str = Query(None, description="YYYYMMDD"),
        end: str = Query(None, description="YYYYMMDD"),
        topk: int = Query(3),
        rebalance: int = Query(5),
        init_cash: float = Query(1_000_000.0),
        benchmark: str = Query(None),
        timing: str = Query(None, description="择时: ma20/abs_mom/rsrs"),
        pool: str = Query(None, description="推荐池名称(可替代 codes)"),
    ):
        try:
            code_list = [c.strip() for c in codes.split(",") if c.strip()] if codes else []
            ss = {"topk": topk, "rebalance_every": rebalance}
            # 连板龙头策略需要额外参数
            if strategy == "lianban_lead":
                ss["min_zt"] = 1
            pipe = run_backtest(
                codes=code_list, strategy=strategy, start=start, end=end,
                init_cash=init_cash, benchmark=benchmark,
                pool=pool or None, timing=timing or None,
                strategy_params=ss,
            )
            result = pipe["result"]
            payload = result.to_dict()
            payload["metrics"] = pipe["metrics"].drop(
                columns=[c for c in pipe["metrics"].columns if c != "策略"],
                errors="ignore")["策略"].to_dict()
            payload["monthly"] = _monthly(pipe["equity"])
            payload["meta"] = pipe["meta"]
            return {"error": 0, "data": payload}
        except Exception as e:
            return {"error": 1, "message": str(e)}

    return app


def _monthly(equity: "pd.DataFrame") -> dict:
    """按月汇总组合收益(%)，供 dashboard 展示。"""
    import pandas as pd
    m = equity["策略"].groupby(equity.index.str[:6]).apply(
        lambda s: s.iloc[-1] / s.iloc[0] - 1)
    return {"labels": [k + "" for k in m.index.tolist()],
            "values": [round(float(v) * 100, 2) for v in m.tolist()]}


def main(argv=None):
    if not _HAS_WEB:
        print("缺少依赖：pip install fastapi uvicorn")
        return 1
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args(argv)
    uvicorn.run(create_app(), host=args.host, port=args.port)


if __name__ == "__main__":
    import sys
    sys.exit(main())