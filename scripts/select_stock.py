from __future__ import annotations

import argparse
import json
import logging
import sys
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple
from concurrent.futures import ProcessPoolExecutor, as_completed
from functools import partial

import pandas as pd
from tqdm import tqdm

# 适配新目录结构: 添加根目录到 sys.path
current_dir = Path(__file__).resolve().parent
root_dir = current_dir.parent
sys.path.append(str(root_dir))

from src.strategy import SelectorFactory, precompute_indicators


# ---------- 日志 ----------
def setup_logging():
    """初始化日志，仅输出到控制台"""
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
        
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("select")


# ---------- 工具函数 ----------

def load_stock_names(csv_path: Path) -> Dict[str, str]:
    """从 stocklist.csv 加载代码到名称的映射"""
    if not csv_path.exists():
        return {}
    try:
        df = pd.read_csv(csv_path)
        mapping = {}
        for _, row in df.iterrows():
            mapping[str(row['symbol']).zfill(6)] = row['name']
        return mapping
    except Exception:
        return {}


def load_single_file(file_path: Path) -> Tuple[str, pd.DataFrame]:
    """加载单个 Parquet 数据文件"""
    code = file_path.stem
    try:
        df = pd.read_parquet(file_path)
        df = df.sort_values("date")
        return code, df
    except Exception:
        return code, pd.DataFrame()


def load_data_parallel(data_dir: Path) -> Dict[str, pd.DataFrame]:
    """并行加载 Parquet 数据文件"""
    
    parquet_files = list(data_dir.glob("*.parquet"))
    if not parquet_files:
        print(f"[ERROR] 未找到 Parquet 数据文件于 {data_dir}")
        print(f"[INFO] 请先运行: python scripts/fetch_kline.py")
        return {}
    
    print(f"[INFO] 加载 {len(parquet_files)} 个 Parquet 文件...")
    
    frames = {}
    total = len(parquet_files)
    
    # 使用多进程并行加载
    with ProcessPoolExecutor() as executor:
        futures = {executor.submit(load_single_file, f): f for f in parquet_files}
        
        for i, future in enumerate(tqdm(as_completed(futures), total=total, desc="Loading Data")):
            code, df = future.result()
            if not df.empty:
                frames[code] = df
            
            # 保持 Web App 解析需要的进度标签
            if (i + 1) % 100 == 0 or (i + 1) == total:
                print(f"[LOAD] {i+1}/{total}", flush=True)
    
    return frames


def load_config(cfg_path: Path) -> List[Dict[str, Any]]:
    if not cfg_path.exists():
        print(f"配置文件 {cfg_path} 不存在")
        sys.exit(1)
    with cfg_path.open(encoding="utf-8") as f:
        cfg_raw = json.load(f)

    if isinstance(cfg_raw, list):
        cfgs = cfg_raw
    elif isinstance(cfg_raw, dict) and "selectors" in cfg_raw:
        cfgs = cfg_raw["selectors"]
    else:
        cfgs = [cfg_raw]

    if not cfgs:
        print("策略配置为空")
        sys.exit(1)

    return cfgs


# ---------- 并行处理单只股票 ----------

def process_single_stock(
    args: Tuple[str, pd.DataFrame],
    trade_date: pd.Timestamp,
    selector_configs: List[Tuple[str, dict]]
) -> Dict[str, List[str]]:
    """
    处理单只股票，返回命中的策略列表
    
    注意: 这个函数在子进程中运行，不能直接传入 selector 对象
    需要在每个进程中重新创建 selector 实例
    """
    code, df = args
    
    if df.empty:
        return {}
    
    try:
        # 1. 预计算指标
        df = precompute_indicators(df)
        
        # 2. 截取到交易日
        hist = df[df["date"] <= trade_date]
        if hist.empty:
            return {}
        
        if len(hist) > 400:
            hist = hist.tail(400)
        
        # 3. 在子进程中创建 selector 实例并检查
        matched = {}
        for alias, cfg in selector_configs:
            try:
                selector = SelectorFactory.create_selector(cfg["class"], cfg.get("params", {}))
                if selector and selector.check_single(hist):
                    if alias not in matched:
                        matched[alias] = []
                    matched[alias].append(code)
            except Exception:
                continue
        
        return matched
    except Exception:
        return {}


# ---------- 主函数 ----------

def main():
    p = argparse.ArgumentParser(description="Run stock selection with parallel processing")
    default_data = root_dir / "data_parquet"  # Parquet-first
    default_config = root_dir / "config" / "strategies.json"
    
    p.add_argument("--data-dir", default=str(default_data), help="Parquet 数据目录")
    p.add_argument("--config", default=str(default_config), help="Selector 配置文件")
    p.add_argument("--date", help="交易日 YYYY-MM-DD；缺省=数据最新日期")
    p.add_argument("--workers", type=int, default=None, help="并行进程数 (默认=CPU核心数)")
    args = p.parse_args()

    logger = setup_logging()

    # --- 加载行情 (Parquet-first) ---
    data_dir = Path(args.data_dir)
    
    if not data_dir.exists():
        print(f"数据目录不存在: {data_dir}")
        print(f"请先运行: python scripts/fetch_kline.py")
        sys.exit(1)

    data = load_data_parallel(data_dir)
    if not data:
        print("未能加载任何行情数据")
        sys.exit(1)

    # --- 确定交易日 ---
    if args.date:
        trade_date = pd.to_datetime(args.date)
    else:
        max_dates = [df["date"].max() for df in data.values() if not df.empty and pd.notnull(df["date"].max())]
        trade_date = max(max_dates) if max_dates else pd.Timestamp.now().normalize()
    
    date_str = trade_date.strftime("%Y-%m-%d")
    logger.info("交易日: %s", date_str)

    # --- 加载股票名称映射 ---
    name_map = load_stock_names(root_dir / "config" / "stock_list.csv")

    # --- 加载 Selector 配置 ---
    selector_cfgs = load_config(Path(args.config))
    
    # 准备可序列化的配置 (用于多进程传递)
    active_configs = []
    for cfg in selector_cfgs:
        if cfg.get("activate", True) is False:
            continue
        alias = cfg.get("alias", cfg.get("class"))
        active_configs.append((alias, cfg))
    
    if not active_configs:
        print("无有效策略，退出")
        sys.exit(0)
    
    logger.info("加载了 %d 个策略", len(active_configs))

    # --- 并行处理股票 ---
    total = len(data)
    logger.info("开始并行处理 %d 只股票...", total)
    
    results = {alias: [] for alias, _ in active_configs}
    
    # 使用多进程并行处理
    process_func = partial(process_single_stock, trade_date=trade_date, selector_configs=active_configs)
    
    workers = args.workers or os.cpu_count()
    logger.info("使用 %d 个工作进程", workers)
    
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(process_func, item): item[0] for item in data.items()}
        
        # miniters: 每 5% 更新一次显示
        update_interval = max(1, total // 20)
        for i, future in enumerate(tqdm(as_completed(futures), total=total, desc="Processing Stocks", unit="stock", miniters=update_interval)):
            matched = future.result()
            for alias, codes in matched.items():
                results[alias].extend(codes)
            
            # 保持 Web App 解析需要的进度标签 (每 5% 输出一次)
            progress_pct = int((i + 1) / total * 100)
            if progress_pct % 5 == 0 and (i == 0 or int(i / total * 100) != progress_pct):
                print(f"[PROCESS] {i+1}/{total}", flush=True)

    # --- 构建结果 DataFrame ---
    stock_strategies = {}
    for alias, picks in results.items():
        for code in picks:
            if code not in stock_strategies:
                stock_strategies[code] = []
            stock_strategies[code].append(alias)
    
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
    
    # --- 日志输出 ---
    logger.info("")
    logger.info("============== 选股汇总 ==============")
    logger.info("交易日: %s", date_str)
    logger.info("符合条件股票总数: %d", len(result_df))
    logger.info("结果已保存至: %s", csv_path)
    
    for alias, picks in results.items():
        if picks:
            logger.info("[%s] %d 只", alias, len(picks))


if __name__ == "__main__":
    main()
