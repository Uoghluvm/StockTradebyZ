from __future__ import annotations

import argparse
import importlib
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List

import pandas as pd

# 适配新目录结构: 添加根目录到 sys.path
current_dir = Path(__file__).resolve().parent
root_dir = current_dir.parent
sys.path.append(str(root_dir))

from src.strategy import SelectorFactory, precompute_indicators

# ---------- 日志 ----------
def setup_logging():
    """初始化日志，仅输出到控制台"""
    # 清除之前的 handlers 以免重复打印
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
        
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger("select")

# ---------- 工具 ----------

def load_stock_names(csv_path: Path) -> Dict[str, str]:
    """从 stocklist.csv 加载代码到名称的映射"""
    if not csv_path.exists():
        return {}
    try:
        df = pd.read_csv(csv_path)
        # 支持 ts_code (000001.SZ) 或 symbol (000001) 作为匹配键
        # 优先使用 symbol 匹配六位代码
        mapping = {}
        for _, row in df.iterrows():
            mapping[str(row['symbol']).zfill(6)] = row['name']
        return mapping
    except Exception:
        return {}

def load_data(data_dir: Path, codes: Iterable[str]) -> Dict[str, pd.DataFrame]:
    frames: Dict[str, pd.DataFrame] = {}
    total = len(codes)
    for i, code in enumerate(codes):
        if i % 100 == 0:
            print(f"[LOAD] {i}/{total}", flush=True)
            
        fp = data_dir / f"{code}.csv"
        if not fp.exists():
            continue
        df = pd.read_csv(fp, parse_dates=["date"]).sort_values("date")
        frames[code] = df
    print(f"[LOAD] {total}/{total}", flush=True)
    return frames


def load_config(cfg_path: Path) -> List[Dict[str, Any]]:
    if not cfg_path.exists():
        print(f"配置文件 {cfg_path} 不存在")
        sys.exit(1)
    with cfg_path.open(encoding="utf-8") as f:
        cfg_raw = json.load(f)

    # 兼容三种结构：单对象、对象数组、或带 selectors 键
    if isinstance(cfg_raw, list):
        cfgs = cfg_raw
    elif isinstance(cfg_raw, dict) and "selectors" in cfg_raw:
        cfgs = cfg_raw["selectors"]
    else:
        cfgs = [cfg_raw]

    if not cfgs:
        print("configs.json 未定义任何 Selector")
        sys.exit(1)

    return cfgs


def instantiate_selector(cfg: Dict[str, Any]):
    """动态加载 Selector 类并实例化"""
    cls_name: str = cfg.get("class")
    if not cls_name:
        raise ValueError("缺少 class 字段")

    try:
        module = importlib.import_module("Selector")
        cls = getattr(module, cls_name)
    except (ModuleNotFoundError, AttributeError) as e:
        raise ImportError(f"无法加载 Selector.{cls_name}: {e}") from e

    params = cfg.get("params", {})
    return cfg.get("alias", cls_name), cls(**params)


# ---------- 主函数 ----------

def main():
    p = argparse.ArgumentParser(description="Run selectors defined in configs.json")
    # 默认路径调整
    default_data = root_dir / "data"
    default_config = root_dir / "config" / "strategies.json"
    
    p.add_argument("--data-dir", default=str(default_data), help="CSV 行情目录")
    p.add_argument("--config", default=str(default_config), help="Selector 配置文件")
    p.add_argument("--date", help="交易日 YYYY-MM-DD；缺省=数据最新日期")
    p.add_argument("--tickers", default="all", help="'all' 或逗号分隔股票代码列表")
    args = p.parse_args()

    # --- 加载行情 ---
    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        print(f"数据目录 {data_dir} 不存在")
        sys.exit(1)

    codes = (
        [f.stem for f in data_dir.glob("*.csv")]
        if args.tickers.lower() == "all"
        else [c.strip() for c in args.tickers.split(",") if c.strip()]
    )
    if not codes:
        print("股票池为空！")
        sys.exit(1)

    data = load_data(data_dir, codes)
    if not data:
        print("未能加载任何行情数据")
        sys.exit(1)

    # --- 确定交易日 ---
    if args.date:
        trade_date = pd.to_datetime(args.date)
    else:
        # 尝试获取所有数据中的最大日期，过滤掉空值
        max_dates = [df["date"].max() for df in data.values() if not df.empty and pd.notnull(df["date"].max())]
        if max_dates:
            trade_date = max(max_dates)
        else:
            # 如果都没有数据，缺省为今天
            trade_date = pd.Timestamp.now().normalize()
    
    # --- 初始化日志 ---
    logger = setup_logging()

    if not args.date:
        logger.info("未指定 --date，使用最近日期 %s", date_str)

    # --- 加载股票名称映射 ---
    name_map = load_stock_names(root_dir / "config" / "stock_list.csv")

    # --- 加载 Selector 配置 ---
    selector_cfgs = load_config(Path(args.config))
    
    # 提前实例化所有启用的策略
    active_selectors = []
    for cfg in selector_cfgs:
        if cfg.get("activate", True) is False:
            continue
        try:
            # 使用 src.strategy.SelectorFactory
            selector = SelectorFactory.create_selector(cfg.get("class"), cfg.get("params", {}))
            alias = cfg.get("alias", cfg.get("class"))
            if selector:
                active_selectors.append((alias, selector))
            else:
                logger.error("无法创建策略: %s", cfg.get("class"))
        except Exception as e:
            logger.error("初始化策略 %s 失败: %s", cfg.get("class"), e)
            continue

    if not active_selectors:
        print("无有效策略，退出")
        sys.exit(0)

    # 准备结果容器 { alias: [code, code...] }
    results = {alias: [] for alias, _ in active_selectors}

    # --- 逐只股票 Precompute + Check ---
    total = len(data)
    logger.info(f"开始处理 {total} 只股票 (Precompute Mode)...")

    for i, (code, df) in enumerate(data.items()):
        if i % 100 == 0:
            print(f"[PROCESS] {i}/{total}", flush=True)

        if df.empty:
            continue
            
        try:
            # 1. 预计算指标 (在完整历史数据上)
            df = precompute_indicators(df)
            
            # 2. 截取到交易日 (含)
            # 必须包含足够的历史供策略回溯 (e.g. 400 天)
            hist = df[df["date"] <= trade_date]
            if hist.empty:
                continue
            
            if len(hist) > 400:
                hist = hist.tail(400)
            
            # 3. 遍历策略检查
            for alias, selector in active_selectors:
                if selector.check_single(hist):
                    results[alias].append(code)
                    
        except Exception as e:
            # 仅记录 debug，以免刷屏
            # logger.debug(f"Error checking {code}: {e}")
            continue

    print(f"[PROCESS] {total}/{total}", flush=True)

    # --- 构建结果 DataFrame ---
    # 格式: 代码, 名称, 策略 (多策略用+连接)
    stock_strategies = {}  # {code: [strategy1, strategy2, ...]}
    
    for alias, picks in results.items():
        for code in picks:
            if code not in stock_strategies:
                stock_strategies[code] = []
            stock_strategies[code].append(alias)
    
    # 转换为 DataFrame
    rows = []
    for code, strategies in stock_strategies.items():
        rows.append({
            '代码': code,
            '名称': name_map.get(code, '未知'),
            '策略': '+'.join(strategies)
        })
    
    result_df = pd.DataFrame(rows)
    
    # --- 保存 CSV ---
    logs_dir = root_dir / "logs"
    logs_dir.mkdir(exist_ok=True)
    csv_path = logs_dir / f"{date_str}选股.csv"
    result_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    
    # --- 日志输出 (终端可见) ---
    logger.info("")
    logger.info("============== 选股汇总 ==============")
    logger.info("交易日: %s", date_str)
    logger.info("符合条件股票总数: %d", len(result_df))
    logger.info("结果已保存至: %s", csv_path)
    
    # 按策略统计
    for alias, picks in results.items():
        if picks:
            logger.info("[%s] %d 只", alias, len(picks))


if __name__ == "__main__":
    main()

