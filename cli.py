"""quantplatform CLI：一键回测并生成 HTML 报告。

用法示例：
    python -m quantplatform.cli --codes 000300.SH,600519.SH,000001.SZ --strategy multifactor \
        --start 20150101 --end 20241231 --out results/report.html
"""
import argparse
import sys
from pathlib import Path

from .pipeline import run_backtest
from .strategies.registry import list_strategies


def main(argv=None):
    ap = argparse.ArgumentParser(description="AI 量化研投平台回测 CLI")
    ap.add_argument("--codes", required=True, help="标的代码，逗号分隔")
    ap.add_argument("--strategy", default="multifactor", choices=list_strategies())
    ap.add_argument("--start", default=None, help="YYYYMMDD")
    ap.add_argument("--end", default=None, help="YYYYMMDD")
    ap.add_argument("--init-cash", type=float, default=1_000_000.0)
    ap.add_argument("--topk", type=int, default=3)
    ap.add_argument("--rebalance", type=int, default=5)
    ap.add_argument("--benchmark", default=None, help="基准代码")
    ap.add_argument("--out", default="results/report.html", help="HTML 报告输出路径")
    args = ap.parse_args(argv)

    codes = [c.strip() for c in args.codes.split(",") if c.strip()]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    print("==> 开始回测 策略=%(s)s 标的=%(c)s" % {"s": args.strategy, "c": codes})
    pipe = run_backtest(
        codes=codes,
        strategy=args.strategy,
        start=args.start,
        end=args.end,
        init_cash=args.init_cash,
        benchmark=args.benchmark,
        strategy_params={"topk": args.topk, "rebalance_every": args.rebalance},
    )
    out.write_text(pipe["html"], encoding="utf-8")
    print("\n=== 绩效指标 ===")
    print(pipe["metrics"].round(4).to_string())
    print("\n报告已生成: {}".format(out.resolve()))
    return 0


if __name__ == "__main__":
    sys.exit(main())