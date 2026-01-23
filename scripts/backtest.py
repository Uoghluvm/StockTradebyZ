#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
股票选股回测工具

根据选股日志内容，计算每只股票以选股日收盘价或次日开盘价买入，
持有一周（5个交易日）后的收益率。

用法:
    python backtest.py [日志文件]
    
示例:
    python backtest.py 2026-01-20选股.log
    python backtest.py  # 自动寻找最新的选股日志
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Optional

import pandas as pd
from datetime import timedelta, datetime

# 适配新目录结构
current_dir = Path(__file__).resolve().parent
root_dir = current_dir.parent
sys.path.append(str(root_dir))


def load_selection_csv(csv_file: str) -> tuple[str, list[dict]]:
    """
    加载选股 CSV 文件
    
    Args:
        csv_file: CSV 文件路径
        
    Returns:
        (选股日期, [{代码, 名称, 策略}, ...])
    """
    # 从文件名提取日期 (YYYY-MM-DD选股.csv)
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', Path(csv_file).name)
    trade_date = date_match.group(1) if date_match else None
    
    # 直接读取 CSV
    try:
        df = pd.read_csv(csv_file, dtype={'代码': str})
        # 确保代码是6位
        df['代码'] = df['代码'].str.zfill(6)
        stocks = df.to_dict('records')
    except Exception as e:
        print(f"读取 CSV 失败: {e}")
        stocks = []
    
    return trade_date, stocks


def load_stock_data(code: str, data_dir: Path) -> Optional[pd.DataFrame]:
    """
    加载单只股票的历史数据 (Parquet 格式)
    
    Args:
        code: 股票代码（6位数字）
        data_dir: Parquet 数据目录路径
        
    Returns:
        DataFrame 或 None（如果文件不存在）
    """
    parquet_path = data_dir / f"{code}.parquet"
    if not parquet_path.exists():
        return None
    
    df = pd.read_parquet(parquet_path)
    df = df.sort_values('date').reset_index(drop=True)
    return df


def calculate_returns(df: pd.DataFrame, buy_date: str, hold_periods: list[int] = [1, 2, 3, 5, 10]) -> dict:
    """
    计算多周期收益率
    
    Args:
        df: 股票历史数据
        buy_date: 选股日期
        hold_periods: 持有天数列表
    
    Returns:
        包含基础买入信息和各周期收益率的字典
    """
    res = {
        'buy_close': None,
        'next_open': None,
        'status': '数据不足',
        'periods': {}  # {days: {'sell_date':..., 'sell_close':..., 'ret_close':..., 'ret_open':...}}
    }
    
    buy_date_ts = pd.to_datetime(buy_date)
    
    # 查找选股日
    buy_idx_list = df[df['date'] == buy_date_ts].index
    if len(buy_idx_list) == 0:
        res['status'] = '停牌或无数据'
        return res
    
    buy_idx = buy_idx_list[0]
    res['buy_close'] = df.loc[buy_idx, 'close']
    
    # 次日（买入日）
    next_day_idx = buy_idx + 1
    if next_day_idx >= len(df):
        res['status'] = '等待次日开盘'
        return res
        
    res['next_open'] = df.loc[next_day_idx, 'open']
    res['status'] = '正常' # 初始状态
    
    # 遍历计算各持有期
    max_idx = len(df) - 1
    
    for days in hold_periods:
        sell_idx = next_day_idx + days
        period_res = {
            'actual_days': days,
            'sell_close': None,
            'return_close': None,
            'return_open': None,
            'note': ''
        }
        
        if sell_idx > max_idx:
            # 数据不足，使用最新数据
            sell_idx = max_idx
            period_res['actual_days'] = sell_idx - next_day_idx
            if period_res['actual_days'] < 0: period_res['actual_days'] = 0
            period_res['note'] = '(持仓未满)'
            if days == max(hold_periods): # 仅最长周期更新主状态
                res['status'] = f"持有中 (持有{period_res['actual_days']}天)"
        
        period_res['sell_close'] = df.loc[sell_idx, 'close']
        
        # 计算
        if res['buy_close'] and res['buy_close'] > 0:
            period_res['return_close'] = round(
                (period_res['sell_close'] - res['buy_close']) / res['buy_close'] * 100, 2
            )
            
        if res['next_open'] and res['next_open'] > 0:
            period_res['return_open'] = round(
                (period_res['sell_close'] - res['next_open']) / res['next_open'] * 100, 2
            )
            
        res['periods'][days] = period_res
        
    return res


def run_backtest(input_path: str, data_dir: str = './data_parquet') -> pd.DataFrame:
    """
    执行回测 (Parquet-first)
    
    Args:
        input_path: 选股 CSV 文件路径
        data_dir: Parquet 数据目录
        
    Returns:
        回测结果 DataFrame
    """
    data_dir = Path(data_dir)
    
    # 加载选股 CSV
    trade_date, stocks = load_selection_csv(input_path)
    
    if not trade_date:
        raise ValueError(f"无法确定选股日期：{input_path}")
    
    print(f"选股日期: {trade_date}")
    print(f"股票数量: {len(stocks)}")
    
    # 回测每只股票
    results = []
    for stock in stocks:
        code = stock['代码']
        df = load_stock_data(code, data_dir)
        
        row = {
            '代码': stock['代码'],
            '名称': stock['名称'],
            '策略': stock['策略'],
        }
        
        if df is None:
            # 无数据填充空
            row.update({
                '选股日收盘价': None,
                '次日开盘价': None,
                '状态': '无数据文件'
            })
            # 填充各周期空值
            for d in [1, 2, 3, 5, 10]:
                row[f'收盘收益_{d}日(%)'] = None
                row[f'开盘收益_{d}日(%)'] = None
            
            # 兼容旧字段
            row['收盘买入收益率(%)'] = None
            row['开盘买入收益率(%)'] = None
            
        else:
            ret = calculate_returns(df, trade_date, hold_periods=[1, 2, 3, 5, 10])
            
            row['选股日收盘价'] = ret['buy_close']
            row['次日开盘价'] = ret['next_open']
            row['状态'] = ret['status']
            
            # 展平周期数据
            for d, p_res in ret['periods'].items():
                row[f'收盘收益_{d}日(%)'] = p_res['return_close']
                row[f'开盘收益_{d}日(%)'] = p_res['return_open']
            
            # 为了兼容 main 函数的打印逻辑，设置默认的 5日收益率
            # 如果没有 5日数据，则为空
            p5 = ret['periods'].get(5)
            if p5:
                row['收盘买入收益率(%)'] = p5['return_close']
                row['开盘买入收益率(%)'] = p5['return_open']
                row['5日后收盘价'] = p5['sell_close']
            else:
                row['收盘买入收益率(%)'] = None
                row['开盘买入收益率(%)'] = None
                row['5日后收盘价'] = None

        results.append(row)
    
    return pd.DataFrame(results)


def find_latest_log(directory: str = 'logs') -> Optional[str]:
    """查找目录下最新的选股日志"""
    pattern = re.compile(r'\d{4}-\d{2}-\d{2}选股\.log')
    logs = [f for f in Path(directory).glob('*选股.log') if pattern.match(f.name)]
    
    if not logs:
        return None
    
    # 按日期排序
    logs.sort(key=lambda x: x.name, reverse=True)
    return str(logs[0])


def main():
    parser = argparse.ArgumentParser(description='股票选股回测工具')
    parser.add_argument('log_file', nargs='?', help='选股日志文件路径（缺省自动查找最新日志）')
    # 默认路径调整
    default_data = root_dir / 'data'
    parser.add_argument('--data-dir', default=str(default_data), help='数据目录（默认 ./data）')
    parser.add_argument('--output', '-o', help='输出文件路径（缺省自动生成）')
    args = parser.parse_args()
    
    # 确定日志文件
    log_path = args.log_file
    if not log_path:
        # 自动查找最新，logs 目录位于根目录
        log_dir = root_dir / 'logs'
        if not log_dir.exists():
            print(f"错误：日志目录 {log_dir} 不存在")
            sys.exit(1)
            
        logs = [f for f in log_dir.glob('*选股.log') if re.match(r'\d{4}-\d{2}-\d{2}选股\.log', f.name)]
        if not logs:
            print(f"错误：未找到选股日志文件，请检查 logs/ 目录")
            sys.exit(1)
            
        # 按日期排序
        logs.sort(key=lambda x: x.name, reverse=True)
        log_path = str(logs[0])
        print(f"自动选择最新日志: {log_path}")
    
    if not Path(log_path).exists():
        print(f"错误：日志文件不存在: {log_path}")
        sys.exit(1)
    
    # 执行回测
    results = run_backtest(log_path, args.data_dir)
    
    # 输出结果
    if args.output:
        output_path = args.output
    else:
        # 结果保存
        results_dir = root_dir / 'results'
        results_dir.mkdir(exist_ok=True)
        
        # 从日志文件名提取日期
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', Path(log_path).name)
        if date_match:
            date_str = date_match.group(1)
            output_path = results_dir / f'回测结果_{date_str}.csv'
        else:
            output_path = results_dir / '回测结果.csv'
    
    results.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"\n回测结果已保存至: {output_path}")
    
    # 打印汇总统计
    valid_results = results[results['状态'].str.contains('正常|已完成|持有中')]
    if len(valid_results) > 0:
        print(f"\n{'='*20} 回测统计（共 {len(valid_results)} 只有效股票） {'='*20}")
        
        # 总体统计
        print("【总体表现】")
        print(f"  收盘买入 - 平均收益率: {valid_results['收盘买入收益率(%)'].mean():.2f}%")
        print(f"  收盘买入 - 盈利比例: {(valid_results['收盘买入收益率(%)'] > 0).sum() / len(valid_results) * 100:.1f}%")
        print(f"  开盘买入 - 平均收益率: {valid_results['开盘买入收益率(%)'].mean():.2f}%")
        print(f"  开盘买入 - 盈利比例: {(valid_results['开盘买入收益率(%)'] > 0).sum() / len(valid_results) * 100:.1f}%")
        
        # 分策略统计
        print(f"\n{'='*20} 分策略表现 {'='*20}")
        strategies = valid_results['策略'].unique()
        for strategy in strategies:
            strat_data = valid_results[valid_results['策略'] == strategy]
            count = len(strat_data)
            avg_close = strat_data['收盘买入收益率(%)'].mean()
            win_close = (strat_data['收盘买入收益率(%)'] > 0).sum() / count * 100
            avg_open = strat_data['开盘买入收益率(%)'].mean()
            win_open = (strat_data['开盘买入收益率(%)'] > 0).sum() / count * 100
            
            print(f"\n策略: [{strategy}] (共 {count} 只)")
            print(f"  收盘买入: 平均 {avg_close:6.2f}% | 胜率 {win_close:5.1f}%")
            print(f"  开盘买入: 平均 {avg_open:6.2f}% | 胜率 {win_open:5.1f}%")
            
    else:
        print("\n警告：没有有效的回测数据")


if __name__ == '__main__':
    main()
