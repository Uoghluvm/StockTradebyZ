#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量运行选股和回测脚本 (多日期并行版)

用法:
    python scripts/batch_run.py --start 2025-01-01 --end 2025-01-31 --skip --parallel 4
    
后台运行:
    nohup python scripts/batch_run.py --start 2025-01-01 --end 2025-01-31 --skip --parallel 4 > batch.log 2>&1 &
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

import pandas as pd

# 路径适配
current_dir = Path(__file__).resolve().parent
root_dir = current_dir.parent


def get_trading_days(start_date: str, end_date: str, parquet_dir: str = './data_parquet') -> list[str]:
    """获取指定范围内的交易日列表 (优先使用 Parquet)"""
    parquet_dir_path = Path(parquet_dir)
    
    ref_parquet = parquet_dir_path / '000001.parquet'
    if ref_parquet.exists():
        df = pd.read_parquet(ref_parquet, columns=['date'])
    else:
        # 回退到 CSV
        data_dir = root_dir / 'data'
        ref_file = data_dir / '000001.csv'
        if not ref_file.exists():
            csv_files = list(data_dir.glob('*.csv'))
            if not csv_files:
                print(f"错误: 无法找到参考数据")
                sys.exit(1)
            ref_file = csv_files[0]
        df = pd.read_csv(ref_file, usecols=['date'])
    
    df['date'] = pd.to_datetime(df['date'])
    
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    
    mask = (df['date'] >= start_dt) & (df['date'] <= end_dt)
    days = df[mask]['date'].dt.strftime('%Y-%m-%d').tolist()
    
    return sorted(days)


def process_single_date(date_str: str, skip: bool = True) -> dict:
    """
    处理单个日期的选股和回测 (在子进程中运行)
    
    Returns:
        {'date': str, 'select_ok': bool, 'backtest_ok': bool, 'skipped': bool}
    """
    result = {'date': date_str, 'select_ok': False, 'backtest_ok': False, 'skipped': False}
    
    csv_p = Path('logs') / f"{date_str}选股.csv"
    res_p = Path('results') / f"回测结果_{date_str}.csv"
    
    need_select = True
    need_backtest = True
    
    if skip:
        if csv_p.exists() and csv_p.stat().st_size > 0:
            need_select = False
            result['select_ok'] = True
        if res_p.exists() and res_p.stat().st_size > 0:
            need_backtest = False
            result['backtest_ok'] = True
    
    if not need_select and not need_backtest:
        result['skipped'] = True
        return result
    
    # 运行选股 (静默模式)
    if need_select:
        proc = subprocess.run(
            [sys.executable, 'scripts/select_stock.py', '--date', date_str],
            capture_output=True, text=True
        )
        result['select_ok'] = (proc.returncode == 0)
    
    # 运行回测
    if need_backtest and (csv_p.exists() or result['select_ok']):
        proc = subprocess.run(
            [sys.executable, 'scripts/backtest.py', str(csv_p)],
            capture_output=True, text=True
        )
        result['backtest_ok'] = (proc.returncode == 0)
    
    return result


def main():
    parser = argparse.ArgumentParser(description='批量运行选股和回测 (多日期并行版)')
    parser.add_argument('--start', required=True, help='开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end', required=True, help='结束日期 (YYYY-MM-DD)')
    parser.add_argument('--skip', action='store_true', help='跳过已存在的选股结果')
    parser.add_argument('--parallel', type=int, default=2, help='并行处理的日期数 (默认=2，建议不超过4)')
    args = parser.parse_args()
    
    print(f"=== 批量处理任务开始 (并行模式) ===")
    print(f"日期范围: {args.start} -> {args.end}")
    print(f"并行日期数: {args.parallel}")
    print("-" * 50)
    
    # 1. 获取交易日
    days = get_trading_days(args.start, args.end)
    print(f"找到 {len(days)} 个交易日")
    
    # 2. 并行处理
    success = 0
    failed = 0
    skipped = 0
    
    from functools import partial
    process_func = partial(process_single_date, skip=args.skip)
    
    with ProcessPoolExecutor(max_workers=args.parallel) as executor:
        futures = {executor.submit(process_func, d): d for d in days}
        
        for i, future in enumerate(as_completed(futures)):
            date_str = futures[future]
            try:
                result = future.result()
                
                if result['skipped']:
                    skipped += 1
                    status = "⏭️ 跳过"
                elif result['select_ok'] and result['backtest_ok']:
                    success += 1
                    status = "✅ 完成"
                else:
                    failed += 1
                    status = "❌ 失败"
                
                # 每完成一个日期输出一行状态
                pct = int((i + 1) / len(days) * 100)
                print(f"[{pct:3d}%] {result['date']} {status}")
                sys.stdout.flush()
                
            except Exception as e:
                failed += 1
                print(f"[ERR] {date_str}: {e}")
    
    print("\n" + "="*50)
    print(f"批量任务完成: 成功 {success}, 跳过 {skipped}, 失败 {failed}")
    
    # 运行汇总分析
    print("运行最后汇总分析...")
    subprocess.run([sys.executable, 'scripts/analyze_results.py'], capture_output=True)
    print("=== 批量任务结束 ===")


if __name__ == '__main__':
    main()
