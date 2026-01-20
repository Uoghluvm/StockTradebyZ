from __future__ import annotations

import argparse
import importlib
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List

import pandas as pd

# ---------- 日志 ----------
def setup_logging(date_str: str):
    log_filename = f"{date_str}选股.log"
    # 清除之前的 handlers 以免重复打印
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
        
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_filename, encoding="utf-8"),
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
    for code in codes:
        fp = data_dir / f"{code}.csv"
        if not fp.exists():
            # 这里先临时用 print，因为 logger 还没初始化
            continue
        df = pd.read_csv(fp, parse_dates=["date"]).sort_values("date")
        frames[code] = df
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
    p.add_argument("--data-dir", default="./data", help="CSV 行情目录")
    p.add_argument("--config", default="./configs.json", help="Selector 配置文件")
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
    
    # --- 初始化日志 (包含日期) ---
    date_str = trade_date.strftime("%Y-%m-%d")
    logger = setup_logging(date_str)

    if not args.date:
        logger.info("未指定 --date，使用最近日期 %s", date_str)

    # --- 加载股票名称映射 ---
    name_map = load_stock_names(Path("stocklist.csv"))

    # --- 加载 Selector 配置 ---
    selector_cfgs = load_config(Path(args.config))

    # --- 逐个 Selector 运行 ---
    for cfg in selector_cfgs:
        if cfg.get("activate", True) is False:
            continue
        try:
            alias, selector = instantiate_selector(cfg)
        except Exception as e:
            logger.error("跳过配置 %s：%s", cfg, e)
            continue

        picks = selector.select(trade_date, data)

        # 整理输出格式：代码(名称)
        formatted_picks = []
        for code in (picks or []):
            name = name_map.get(code, "未知")
            formatted_picks.append(f"{code}({name})")

        # 将结果写入日志，同时输出到控制台
        logger.info("")
        logger.info("============== 选股结果 [%s] ==============", alias)
        logger.info("交易日: %s", date_str)
        logger.info("符合条件股票数: %d", len(picks) if picks else 0)
        logger.info("%s", ", ".join(formatted_picks) if formatted_picks else "无符合条件股票")


if __name__ == "__main__":
    main()
