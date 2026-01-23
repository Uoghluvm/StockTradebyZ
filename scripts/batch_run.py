#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量运行选股和回测脚本

用法:
    python batch_run.py [月份]
    
示例:
    python batch_run.py 2026-01
"""

import argparse
import subprocess
import sys
from pathlib import Path
import pandas as pd

def get_trading_days(month: str, data_dir: str = './data') -> list[str]:
    """
    获取指定月份的交易日列表
    通过读取 000001.csv 来确定实际交易日
    """
    ref_file = Path(data_dir) / '000001.csv'
    if not ref_file.exists():
        print(f"错误: 无法找到参考数据文件 {ref_file}")
        sys.exit(1)
        
    df = pd.read_csv(ref_file, parse_dates=['date'])
    
    # 筛选指定月份
    mask = df['date'].astype(str).str.startswith(month)
    days = df[mask]['date'].dt.strftime('%Y-%m-%d').tolist()
    
    return sorted(days)

def run_command(cmd: list[str]):
    """运行命令并实时输出"""
    print(f"执行: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"错误:\n{result.stderr}")
    else:
        # 打印部分关键输出，避免刷屏，但保留策略统计
        lines = result.stdout.split('\n')
        for line in lines:
            # 放宽过滤条件，保留所有关键统计行
            if any(keyword in line for keyword in ["符合条件", "回测统计", "总体表现", "分策略表現", "策略:", "平均收益率", "胜率"]):
                print(f"  > {line.strip()}")

def main():
    parser = argparse.ArgumentParser(description='批量运行选股和回测')
    parser.add_argument('month', help='指定月份 (YYYY-MM)')
    args = parser.parse_args()
    
    month = args.month
    print(f"开始处理 {month} 月份的任务...")
    
    # 1. 获取交易日
    days = get_trading_days(month, data_dir='./data')
    print(f"找到 {len(days)} 个交易日: {', '.join(days)}")
    print("-" * 50)
    
    for date in days:
        print(f"\n>>> 处理日期: {date}")
        
        # 2. 运行选股
        # python scripts/select_stock.py --date YYYY-MM-DD
        run_command([sys.executable, 'scripts/select_stock.py', '--date', date])
        
        # 3. 运行回测
        # python scripts/backtest.py logs/YYYY-MM-DD选股.log
        log_file = Path('logs') / f"{date}选股.log"
        if log_file.exists():
            run_command([sys.executable, 'scripts/backtest.py', str(log_file)])
        else:
            print(f"警告: 未找到日志文件 {log_file}，可能选股失败或无结果")
            
    print("\n所有日期执行完毕，开始汇总分析...")
    # python scripts/analyze_results.py
    run_command([sys.executable, 'scripts/analyze_results.py'])

if __name__ == '__main__':
    main()
