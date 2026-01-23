import re
import csv

def parse_log(log_file):
    # 使用字典按代码分组：{code: {'名称': name, '策略': [strat1, strat2, ...]}}
    stock_map = {}
    current_strategy = None
    
    # Regex to find strategy names
    strategy_pattern = re.compile(r"============== 选股结果 \[(.*?)\] ==============")
    # Regex to find stock entries like 688002(睿创微纳)
    stock_pattern = re.compile(r"(\d{6})\((.*?)\)")

    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            strategy_match = strategy_pattern.search(line)
            if strategy_match:
                current_strategy = strategy_match.group(1)
                continue
            
            if current_strategy:
                # Find all stock entries in the line
                stocks = stock_pattern.findall(line)
                for code, name in stocks:
                    if code not in stock_map:
                        stock_map[code] = {
                            '名称': name,
                            '策略': [current_strategy]
                        }
                    else:
                        # 如果该股票已经存在，且该策略还未记录，则添加策略
                        if current_strategy not in stock_map[code]['策略']:
                            stock_map[code]['策略'].append(current_strategy)
    
    # 转换为最终格式并合并策略名称
    results = []
    for code, data in stock_map.items():
        results.append({
            '代码': code,
            '名称': data['名称'],
            '策略': "+".join(data['策略'])
        })
    
    # Sort results
    # Primary: 策略, Secondary: 代码
    results.sort(key=lambda x: (x['策略'], x['代码']))
    return results

def save_to_csv(results, output_file):
    keys = ['代码', '名称', '策略']
    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        dict_writer = csv.DictWriter(f, fieldnames=keys)
        dict_writer.writeheader()
        dict_writer.writerows(results)

if __name__ == "__main__":
    log_path = '2026-01-20选股.log'
    csv_path = '选股结果_2026-01-20.csv'
    data = parse_log(log_path)
    save_to_csv(data, csv_path)
    print(f"成功保存 {len(data)} 条结果到 {csv_path}")
