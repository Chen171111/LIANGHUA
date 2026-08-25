"""
quantplatform —— AI 智能量化研投平台（Qbot 生态内置）

模块化分层：
    config        平台统一配置
    dataprovider   数据引擎：统一接入(akshare/tushare/CSV)、缓存、面板构建
    factors        因子引擎：技术/量价因子库、因子注册表、因子暴露
    backtest       回测引擎：组合账户(手续费/滑点/复权)、逐bar轮动、多周期绩效
    strategies     多策略引擎：策略接口 + 注册表(可插拔) + 内置策略
    analysis       结果与报告
    trader         交易接口抽象(模拟/实盘适配层)
    api / dashboard Web 层(可选)

设计目标：
    - 数据获取免费可用(akshare)，无需付费 token 即可跑通全流程
    - 策略可插拔注册，引擎与策略解耦
    - 与 Qbot 现有 pytrader 生态对齐(可对接 easytrader / easyquant)
"""
from .config import PlatformConfig, backtest_config

__version__ = "0.1.0"
__all__ = ["PlatformConfig", "backtest_config"]