#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频筛选和导出工具
按日期、播放量、时长等条件筛选CSV中的视频并导出
"""

import csv
import sys
from pathlib import Path
from datetime import datetime
from config import OUTPUT_PATH
from logger_utils import setup_logger, get_log_file_name

# 颜色输出
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    MAGENTA = '\033[0;35m'
    NC = '\033[0m'  # No Color

def print_colored(text, color=Colors.NC, end='\n'):
    """打印彩色文本"""
    print(f"{color}{text}{Colors.NC}", end=end)

def parse_date(date_str):
    """解析日期字符串 YYYY-MM-DD 或 YYYY"""
    if not date_str or date_str.strip() == '':
        return None
    try:
        # 尝试解析 YYYY-MM-DD
        if len(date_str) >= 10:
            return datetime.strptime(date_str[:10], '%Y-%m-%d')
        # 尝试解析 YYYY
        elif len(date_str) >= 4:
            return datetime.strptime(date_str[:4], '%Y')
    except:
        pass
    return None

def parse_number(value):
    """解析数字（支持千位分隔符）"""
    if not value or value == '':
        return 0
    try:
        # 移除千位分隔符和空格
        value = str(value).replace(',', '').replace(' ', '').strip()
        return int(value)
    except:
        return 0

def parse_duration(duration_str):
    """解析时长字符串 MM:SS 或 HH:MM:SS，返回秒数"""
    if not duration_str or duration_str.strip() == '':
        return 0
    try:
        parts = duration_str.split(':')
        if len(parts) == 2:  # MM:SS
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:  # HH:MM:SS
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        else:
            # 尝试直接解析为秒数
            return int(duration_str)
    except:
        return 0

def filter_videos(csv_file, output_file, filters=None):
    """筛选视频并导出到新CSV文件
    
    Args:
        csv_file: 输入CSV文件路径
        output_file: 输出CSV文件路径
        filters: 筛选条件字典，包含：
            - min_views: 最小播放量
            - max_views: 最大播放量
            - min_likes: 最小点赞量
            - max_likes: 最大点赞量
            - min_duration: 最小时长（秒）
            - max_duration: 最大时长（秒）
            - date_from: 起始日期 (YYYY-MM-DD)
            - date_to: 结束日期 (YYYY-MM-DD)
            - year: 年份 (YYYY)
            - keywords: 关键词列表（在标题或描述中搜索）
            - has_subtitles: 是否有字幕 (True/False)
    """
    # 设置日志
    log_file = get_log_file_name('filter_videos')
    logger = setup_logger('filter_videos', log_file)
    logger.info("=" * 60)
    logger.info("视频筛选和导出工具")
    logger.info("=" * 60)
    
    csv_path = Path(csv_file)
    
    if not csv_path.exists():
        error_msg = f"文件不存在: {csv_file}"
        print_colored(f"❌ {error_msg}", Colors.RED)
        logger.error(error_msg)
        return False
    
    filters = filters or {}
    
    print_colored("=" * 60, Colors.CYAN)
    print_colored("视频筛选和导出工具", Colors.GREEN)
    print_colored("=" * 60, Colors.CYAN)
    print()
    print_colored(f"输入文件: {csv_file}", Colors.BLUE)
    print_colored(f"输出文件: {output_file}", Colors.BLUE)
    logger.info(f"输入文件: {csv_file}, 输出文件: {output_file}")
    print()
    
    # 显示筛选条件
    if filters:
        print_colored("筛选条件:", Colors.YELLOW)
        for key, value in filters.items():
            if value is not None and value != '':
                print_colored(f"  {key}: {value}", Colors.CYAN)
        print()
    
    # 读取CSV文件
    print_colored("正在读取CSV文件...", Colors.CYAN)
    rows = []
    headers = []
    
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            rows = list(reader)
        
        print_colored(f"✅ 读取到 {len(rows)} 条视频记录", Colors.GREEN)
        logger.info(f"成功读取 {len(rows)} 条视频记录")
        print()
    except Exception as e:
        error_msg = f"读取CSV文件失败: {str(e)}"
        print_colored(f"❌ {error_msg}", Colors.RED)
        logger.error(error_msg, exc_info=True)
        return False
    
    if not rows:
        print_colored("⚠️  CSV文件中没有数据", Colors.YELLOW)
        logger.warning("CSV文件中没有数据")
        return False
    
    # 应用筛选条件
    print_colored("正在应用筛选条件...", Colors.BLUE)
    logger.info(f"开始应用筛选条件: {filters}")
    filtered_rows = []
    
    for row in rows:
        # 播放量筛选
        if 'min_views' in filters and filters['min_views'] is not None:
            views = parse_number(row.get('播放量', 0))
            if views < filters['min_views']:
                continue
        
        if 'max_views' in filters and filters['max_views'] is not None:
            views = parse_number(row.get('播放量', 0))
            if views > filters['max_views']:
                continue
        
        # 点赞量筛选
        if 'min_likes' in filters and filters['min_likes'] is not None:
            likes = parse_number(row.get('点赞量', 0))
            if likes < filters['min_likes']:
                continue
        
        if 'max_likes' in filters and filters['max_likes'] is not None:
            likes = parse_number(row.get('点赞量', 0))
            if likes > filters['max_likes']:
                continue
        
        # 时长筛选
        duration_seconds = parse_number(row.get('视频时长（秒）', 0))
        if duration_seconds == 0:
            duration_seconds = parse_duration(row.get('视频时长', ''))
        
        if 'min_duration' in filters and filters['min_duration'] is not None:
            if duration_seconds < filters['min_duration']:
                continue
        
        if 'max_duration' in filters and filters['max_duration'] is not None:
            if duration_seconds > filters['max_duration']:
                continue
        
        # 日期筛选
        upload_date_str = row.get('上传日期', '')
        upload_date = parse_date(upload_date_str)
        
        if 'date_from' in filters and filters['date_from'] is not None:
            date_from = parse_date(filters['date_from'])
            if upload_date and date_from and upload_date < date_from:
                continue
        
        if 'date_to' in filters and filters['date_to'] is not None:
            date_to = parse_date(filters['date_to'])
            if upload_date and date_to and upload_date > date_to:
                continue
        
        if 'year' in filters and filters['year'] is not None:
            if upload_date and upload_date.year != filters['year']:
                continue
        
        # 关键词筛选
        if 'keywords' in filters and filters['keywords']:
            title = row.get('视频标题', '').lower()
            description = row.get('视频描述', '').lower()
            text = title + ' ' + description
            
            keywords = [k.lower() for k in filters['keywords']]
            if not any(keyword in text for keyword in keywords):
                continue
        
        # 字幕筛选
        if 'has_subtitles' in filters and filters['has_subtitles'] is not None:
            subtitle_langs = row.get('字幕语言', '').strip()
            auto_caption_langs = row.get('自动字幕语言', '').strip()
            has_subs = bool(subtitle_langs or auto_caption_langs)
            
            if filters['has_subtitles'] and not has_subs:
                continue
            if not filters['has_subtitles'] and has_subs:
                continue
        
        filtered_rows.append(row)
    
    print_colored(f"✅ 筛选后剩余 {len(filtered_rows)} 条记录", Colors.GREEN)
    print()
    
    # 保存筛选结果
    if not filtered_rows:
        print_colored("⚠️  没有符合条件的视频", Colors.YELLOW)
        return False
    
    print_colored(f"正在保存筛选结果到: {output_file}", Colors.BLUE)
    
    try:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(filtered_rows)
        
        print_colored(f"✅ 筛选结果已保存: {output_file}", Colors.GREEN)
        logger.info(f"筛选结果已保存: {output_file}")
        print()
        
        # 显示统计信息
        total_views = sum(parse_number(r.get('播放量', 0)) for r in filtered_rows)
        total_likes = sum(parse_number(r.get('点赞量', 0)) for r in filtered_rows)
        avg_views = total_views / len(filtered_rows) if filtered_rows else 0
        
        print_colored("筛选结果统计:", Colors.YELLOW)
        print_colored(f"  视频数量: {len(filtered_rows)}", Colors.CYAN)
        print_colored(f"  总播放量: {total_views:,}", Colors.BLUE)
        print_colored(f"  总点赞量: {total_likes:,}", Colors.MAGENTA)
        print_colored(f"  平均播放量: {avg_views:,.0f}", Colors.CYAN)
        logger.info(f"筛选完成 - 结果数量: {len(filtered_rows)}, 总播放量: {total_views:,}")
        print()
        
        return True
    except Exception as e:
        error_msg = f"保存文件失败: {str(e)}"
        print_colored(f"❌ {error_msg}", Colors.RED)
        logger.error(error_msg, exc_info=True)
        return False

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='筛选CSV文件中的视频并导出')
    parser.add_argument('csv_file', help='输入CSV文件路径')
    parser.add_argument('-o', '--output', required=True, help='输出CSV文件路径')
    
    # 播放量筛选
    parser.add_argument('--min-views', type=int, help='最小播放量')
    parser.add_argument('--max-views', type=int, help='最大播放量')
    
    # 点赞量筛选
    parser.add_argument('--min-likes', type=int, help='最小点赞量')
    parser.add_argument('--max-likes', type=int, help='最大点赞量')
    
    # 时长筛选（秒）
    parser.add_argument('--min-duration', type=int, help='最小时长（秒）')
    parser.add_argument('--max-duration', type=int, help='最大时长（秒）')
    
    # 日期筛选
    parser.add_argument('--date-from', help='起始日期 (YYYY-MM-DD)')
    parser.add_argument('--date-to', help='结束日期 (YYYY-MM-DD)')
    parser.add_argument('--year', type=int, help='年份 (YYYY)')
    
    # 关键词筛选
    parser.add_argument('--keywords', nargs='+', help='关键词列表（在标题或描述中搜索）')
    
    # 字幕筛选
    parser.add_argument('--has-subtitles', action='store_true', help='只筛选有字幕的视频')
    parser.add_argument('--no-subtitles', action='store_true', help='只筛选无字幕的视频')
    
    args = parser.parse_args()
    
    # 构建筛选条件
    filters = {}
    
    if args.min_views is not None:
        filters['min_views'] = args.min_views
    if args.max_views is not None:
        filters['max_views'] = args.max_views
    if args.min_likes is not None:
        filters['min_likes'] = args.min_likes
    if args.max_likes is not None:
        filters['max_likes'] = args.max_likes
    if args.min_duration is not None:
        filters['min_duration'] = args.min_duration
    if args.max_duration is not None:
        filters['max_duration'] = args.max_duration
    if args.date_from:
        filters['date_from'] = args.date_from
    if args.date_to:
        filters['date_to'] = args.date_to
    if args.year is not None:
        filters['year'] = args.year
    if args.keywords:
        filters['keywords'] = args.keywords
    if args.has_subtitles:
        filters['has_subtitles'] = True
    if args.no_subtitles:
        filters['has_subtitles'] = False
    
    # 检查是否有筛选条件
    if not filters:
        print_colored("⚠️  警告: 没有指定任何筛选条件，将导出所有视频", Colors.YELLOW)
        response = input("是否继续？(y/n): ")
        if response.lower() != 'y':
            return
    
    # 执行筛选
    success = filter_videos(args.csv_file, args.output, filters)
    
    if success:
        print_colored("=" * 60, Colors.CYAN)
        print_colored("✅ 完成！", Colors.GREEN)
        print_colored("=" * 60, Colors.CYAN)
    else:
        print_colored("=" * 60, Colors.CYAN)
        print_colored("❌ 失败", Colors.RED)
        print_colored("=" * 60, Colors.CYAN)
        sys.exit(1)

if __name__ == '__main__':
    main()

