#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
选股策略全量分析工具

读取当前目录下所有的 `回测结果_YYYY-MM-DD.csv` 文件，
按【策略】进行汇总统计，计算平均收益、胜率、最大回撤等指标。

输出:
    - 终端打印排行
    - 保存为 strategy_report.csv
"""

import pandas as pd
from pathlib import Path
import sys

# 适配新目录结构
current_dir = Path(__file__).resolve().parent
root_dir = current_dir.parent
sys.path.append(str(root_dir))


def load_all_results(data_dir: str = 'results') -> pd.DataFrame:
    """加载目录下所有回测结果CSV"""
    # 路径调整
    path = root_dir / data_dir
    csv_files = list(path.glob('回测结果_*.csv'))
    
    if not csv_files:
        return pd.DataFrame()
    
    df_list = []
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file)
            # 提取日期（假设文件名格式固定）
            # 回测结果_2026-01-20.csv -> 2026-01-20
            date_str = csv_file.stem.replace('回测结果_', '')
            df['选股日期'] = date_str
            df_list.append(df)
        except Exception as e:
            print(f"读取 {csv_file} 失败: {e}")
            
    if not df_list:
        return pd.DataFrame()
        
    return pd.concat(df_list, ignore_index=True)

def analyze_strategies(df: pd.DataFrame):
    """按策略分析业绩"""
    if df.empty:
        print("无数据可分析")
        return

    # 过滤有效数据（排除 '无数据文件' 等状态，保留 '持有中' 进行统计但需谨慎）
    # 这里我们只统计已有明确结果的，或者包含持有中的当前浮盈
    valid_df = df[df['状态'].str.contains('正常|已完成|持有中', na=False)].copy()
    
    if valid_df.empty:
        print("无有效回测数据")
        return

    print(f"共加载 {len(valid_df)} 条有效选股记录，涵盖 {valid_df['选股日期'].nunique()} 个交易日。")

    # 按策略分组
    # 有些股票可能属于多个策略（策略字段如果是 '策略A+策略B'，这里暂按组合策略名为准，
    # 若需拆分统计需先对 dataframe 进行 explode 处理。这里先按组合名统计）
    
    # 统计指标
    # 动态识别所有收益率列
    return_cols = [c for c in valid_df.columns if '收盘收益_' in c and '(%)' in c]
    if not return_cols:
        # 兼容旧版本
        return_cols = ['收盘买入收益率(%)']
        
    agg_dict = {
        '代码': 'count',
        '收盘买入收益率(%)': ['mean'], # 基础5日
        '开盘买入收益率(%)': ['mean'],
    }
    
    #哪怕有新列，也加入聚合
    for col in return_cols:
        agg_dict[col] = 'mean'
        
    stats = valid_df.groupby('策略').agg(agg_dict)
    
    # 重命名列 (由于是多级索引，需要扁平化)
    stats.columns = ['_'.join(col).strip() for col in stats.columns.values]
    
    # 重命名基础列
    stats = stats.rename(columns={
        '代码_count': '总荐股数',
        '收盘买入收益率(%)_mean': '收盘_5日均%',
        '开盘买入收益率(%)_mean': '开盘_5日均%'
    })
    
    # 计算各周期胜率和均值，找出最佳周期
    best_periods = []
    
    for strategy in stats.index:
        strat_df = valid_df[valid_df['策略'] == strategy]
        
        # 寻找最佳周期
        best_day = '5日'
        best_ret = -100
        period_stats = []
        
        for col in return_cols:
            day_str = col.split('_')[1].replace('日(%)', '') # '1'
            avg_ret = strat_df[col].mean()
            win_rate = (strat_df[col] > 0).sum() / len(strat_df) * 100
            
            period_stats.append(f"{day_str}日:{avg_ret:.1f}%")
            
            if avg_ret > best_ret:
                best_ret = avg_ret
                best_day = day_str + '日'
        
        best_periods.append({
            '策略': strategy,
            '最佳周期': best_day,
            '最佳均收': best_ret,
            '周期详情': ' | '.join(period_stats)
        })
    
    best_df = pd.DataFrame(best_periods).set_index('策略')
    stats = stats.join(best_df)

    # 综合评分 (示例: 胜率*0.5 + 收益*0.5)
    # 使用基础5日胜率作为参考
    win_rates = valid_df.groupby('策略')['收盘买入收益率(%)'].apply(lambda x: (x > 0).sum() / len(x) * 100)
    stats['收盘_胜率%'] = win_rates
    
    stats['综合得分'] = stats['收盘_胜率%'] * 0.6 + stats['收盘_5日均%'] * 0.4
    
    # 排序
    stats = stats.sort_values('综合得分', ascending=False)
    
    # 格式化输出
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    pd.set_option('display.float_format', '{:.2f}'.format)
    
    print("\n" + "="*20 + " 策略全量回测排行 " + "="*20)
    # 选取关键列打印
    print_cols = ['总荐股数', '最佳周期', '最佳均收', '收盘_胜率%', '周期详情', '综合得分']
    # 确保列存在
    print_cols = [c for c in print_cols if c in stats.columns]
    print(stats[print_cols])
    
    # 保存报告
    report_path = root_dir / 'results' / '策略评测报告_汇总.csv'
    stats.to_csv(report_path, encoding='utf-8-sig')
    print(f"\n详细报告已保存至: {report_path}")

def main():
    print("正在扫描回测结果...")
    df = load_all_results()
    analyze_strategies(df)

if __name__ == '__main__':
    main()
