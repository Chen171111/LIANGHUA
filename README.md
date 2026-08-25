# quantplatform — AI 智能量化研投平台

一个模块化、免费数据、可扩展的量化投研平台，覆盖 **数据获取 → 因子计算 → 多策略 → 专业回测 → 绩效分析 → Web Dashboard** 全链路。

> 位处 Qbot 生态内，独立成仓，不依赖 Qbot 上游代码运行。

## 特性

- **数据引擎** `dataprovider`：akshare 免费行情（指数 + 个股前复权），自动下载/缓存，跨标的横截面面板
- **因子引擎** `factors`：技术因子库（RSI/MACD/乖离率/波动率/动量/量比…），因子注册表可自定义，因子暴露计算
- **多策略引擎** `strategies`：策略抽象接口 + 热插拔注册表，内置 `momentum / mean_reversion / cross_moving / multifactor`
- **回测引擎** `backtest`：组合账户（佣金+滑点+印花税），逐 bar 权重轮动，多周期绩效（年化/夏普/索提诺/Calmar/最大回撤/胜率/盈亏比）
- **交易接口预留** `trader`：`Broker` 抽象 + `MockBroker`，可对接 easytrader 等实盘通道
- **Web Dashboard** `api` + `dashboard`：FastAPI + ECharts，在线改参数回测并渲染净值/回撤/月度收益/持仓热力图

## 快速开始

```bash
pip install -r requirements.txt

# 一、命令行一键回测并生成 HTML 报告
cd pytrader   # quantplatform 的上级目录，使 python 可 import 到 quantplatform
python -m quantplatform.cli --codes 000300.SH,399006.SZ,399324.SZ --strategy multifactor \
    --start 20150101 --end 20241231 --out results/report.html

# 二、启动交互式 Web Dashboard
python -m quantplatform.api.server --port 8000
# 打开 http://127.0.0.1:8000/
```

## 目录结构

```
quantplatform/
├── config.py           配置层（路径/默认回测成本）
├── dataprovider/       数据引擎（akshare 下载缓存、面板构建）
├── factors/            因子引擎（因子库/注册表/暴露）
├── strategies/         多策略引擎（接口/注册表/内置策略）
├── backtest/           回测引擎（账户/轮动/绩效）
├── trader/             交易接口抽象（Broker / MockBroker）
├── analysis/           HTML 报告渲染（自包含 ECharts Dashboard）
├── api/                FastAPI 后端
├── dashboard/          Web 交互仪表盘
├── pipeline.py         统一流水线
└── cli.py              CLI 入口
```

## API 概览

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/strategies` | GET | 列出可用策略 |
| `/api/backtest?codes=…&strategy=…` | POST | 运行回测，返回净值/月度收益/指标/持仓 |
| `/api/health` | GET | 健康检查 |

## License

MIT