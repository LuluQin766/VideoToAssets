#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频统计分析工具
生成详细的视频分析报告，包括趋势分析、分类统计、时间分布等
"""

import csv
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter
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

def parse_number(value):
    """解析数字（支持千位分隔符）"""
    if not value or value == '':
        return 0
    try:
        value = str(value).replace(',', '').replace(' ', '').strip()
        return int(value)
    except:
        return 0

def parse_date(date_str):
    """解析日期字符串 YYYY-MM-DD 或 YYYY"""
    if not date_str or date_str.strip() == '':
        return None
    try:
        if len(date_str) >= 10:
            return datetime.strptime(date_str[:10], '%Y-%m-%d')
        elif len(date_str) >= 4:
            return datetime.strptime(date_str[:4], '%Y')
    except:
        pass
    return None

def parse_duration(duration_str):
    """解析时长字符串，返回秒数"""
    if not duration_str or duration_str.strip() == '':
        return 0
    try:
        parts = duration_str.split(':')
        if len(parts) == 2:  # MM:SS
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:  # HH:MM:SS
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        else:
            return int(duration_str)
    except:
        return 0

def analyze_videos(csv_file, output_report=None):
    """分析视频数据并生成报告"""
    # 设置日志
    log_file = get_log_file_name('analyze_videos')
    logger = setup_logger('analyze_videos', log_file)
    logger.info("=" * 60)
    logger.info("视频统计分析工具")
    logger.info("=" * 60)
    
    csv_path = Path(csv_file)
    
    if not csv_path.exists():
        error_msg = f"文件不存在: {csv_file}"
        print_colored(f"❌ {error_msg}", Colors.RED)
        logger.error(error_msg)
        return False
    
    print_colored("=" * 60, Colors.CYAN)
    print_colored("视频统计分析工具", Colors.GREEN)
    print_colored("=" * 60, Colors.CYAN)
    print()
    print_colored(f"输入文件: {csv_file}", Colors.BLUE)
    logger.info(f"输入文件: {csv_file}")
    print()
    
    # 读取CSV文件
    print_colored("正在读取CSV文件...", Colors.CYAN)
    rows = []
    
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
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
    
    # 数据预处理
    print_colored("正在分析数据...", Colors.CYAN)
    logger.info("开始分析数据")
    
    videos_data = []
    for row in rows:
        view_count = parse_number(row.get('播放量', 0))
        like_count = parse_number(row.get('点赞量', 0))
        comment_count = parse_number(row.get('评论数', 0))
        duration = parse_number(row.get('视频时长（秒）', 0))
        if duration == 0:
            duration = parse_duration(row.get('视频时长', ''))
        
        upload_date = parse_date(row.get('上传日期', ''))
        year = upload_date.year if upload_date else None
        month = upload_date.month if upload_date else None
        
        videos_data.append({
            'title': row.get('视频标题', ''),
            'view_count': view_count,
            'like_count': like_count,
            'comment_count': comment_count,
            'duration': duration,
            'upload_date': upload_date,
            'year': year,
            'month': month,
            'category': row.get('分类', ''),
            'tags': row.get('标签', ''),
            'language': row.get('语言', ''),
            'availability': row.get('可用性', ''),
            'status': row.get('视频状态', 'available'),
        })
    
    # 生成分析报告
    report_lines = []
    report_lines.append("# 视频统计分析报告\n")
    report_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    report_lines.append(f"数据来源: {csv_file}\n")
    report_lines.append(f"总视频数: {len(videos_data)}\n\n")
    report_lines.append("=" * 60 + "\n\n")
    
    # 1. 基础统计
    print_colored("📊 生成基础统计...", Colors.CYAN)
    total_views = sum(v['view_count'] for v in videos_data)
    total_likes = sum(v['like_count'] for v in videos_data)
    total_comments = sum(v['comment_count'] for v in videos_data)
    total_duration = sum(v['duration'] for v in videos_data)
    avg_views = total_views / len(videos_data) if videos_data else 0
    avg_likes = total_likes / len(videos_data) if videos_data else 0
    avg_comments = total_comments / len(videos_data) if videos_data else 0
    avg_duration = total_duration / len(videos_data) if videos_data else 0
    
    report_lines.append("## 1. 基础统计\n\n")
    report_lines.append(f"- **总播放量**: {total_views:,}\n")
    report_lines.append(f"- **总点赞量**: {total_likes:,}\n")
    report_lines.append(f"- **总评论数**: {total_comments:,}\n")
    report_lines.append(f"- **总时长**: {total_duration // 3600}小时 {(total_duration % 3600) // 60}分钟\n")
    report_lines.append(f"- **平均播放量**: {avg_views:,.0f}\n")
    report_lines.append(f"- **平均点赞量**: {avg_likes:,.0f}\n")
    report_lines.append(f"- **平均评论数**: {avg_comments:,.0f}\n")
    report_lines.append(f"- **平均时长**: {avg_duration // 60}分钟 {avg_duration % 60}秒\n")
    report_lines.append(f"- **平均点赞率**: {(total_likes / total_views * 100) if total_views > 0 else 0:.2f}%\n\n")
    
    # 2. 时间分布分析
    print_colored("📅 分析时间分布...", Colors.CYAN)
    year_stats = defaultdict(lambda: {'count': 0, 'views': 0, 'likes': 0})
    month_stats = defaultdict(lambda: {'count': 0, 'views': 0, 'likes': 0})
    
    for v in videos_data:
        if v['year']:
            year_stats[v['year']]['count'] += 1
            year_stats[v['year']]['views'] += v['view_count']
            year_stats[v['year']]['likes'] += v['like_count']
        
        if v['year'] and v['month']:
            month_key = f"{v['year']}-{v['month']:02d}"
            month_stats[month_key]['count'] += 1
            month_stats[month_key]['views'] += v['view_count']
            month_stats[month_key]['likes'] += v['like_count']
    
    report_lines.append("## 2. 时间分布分析\n\n")
    report_lines.append("### 2.1 按年份统计\n\n")
    report_lines.append("| 年份 | 视频数 | 总播放量 | 总点赞量 | 平均播放量 |\n")
    report_lines.append("|------|--------|----------|----------|------------|\n")
    
    for year in sorted(year_stats.keys()):
        stats = year_stats[year]
        avg_views = stats['views'] / stats['count'] if stats['count'] > 0 else 0
        report_lines.append(f"| {year} | {stats['count']} | {stats['views']:,} | {stats['likes']:,} | {avg_views:,.0f} |\n")
    
    report_lines.append("\n### 2.2 按月份统计（前10个月）\n\n")
    report_lines.append("| 月份 | 视频数 | 总播放量 | 总点赞量 | 平均播放量 |\n")
    report_lines.append("|------|--------|----------|----------|------------|\n")
    
    sorted_months = sorted(month_stats.items(), key=lambda x: x[1]['views'], reverse=True)[:10]
    for month_key, stats in sorted_months:
        avg_views = stats['views'] / stats['count'] if stats['count'] > 0 else 0
        report_lines.append(f"| {month_key} | {stats['count']} | {stats['views']:,} | {stats['likes']:,} | {avg_views:,.0f} |\n")
    
    report_lines.append("\n")
    
    # 3. 播放量分析
    print_colored("📈 分析播放量分布...", Colors.CYAN)
    sorted_by_views = sorted(videos_data, key=lambda x: x['view_count'], reverse=True)
    
    report_lines.append("## 3. 播放量分析\n\n")
    report_lines.append("### 3.1 播放量最高的10个视频\n\n")
    report_lines.append("| 排名 | 视频标题 | 播放量 | 点赞量 | 点赞率 |\n")
    report_lines.append("|------|----------|--------|--------|--------|\n")
    
    for i, v in enumerate(sorted_by_views[:10], 1):
        title = v['title'][:50] + '...' if len(v['title']) > 50 else v['title']
        like_rate = (v['like_count'] / v['view_count'] * 100) if v['view_count'] > 0 else 0
        report_lines.append(f"| {i} | {title} | {v['view_count']:,} | {v['like_count']:,} | {like_rate:.2f}% |\n")
    
    # 播放量区间统计
    view_ranges = {
        '0-1万': 0,
        '1-10万': 0,
        '10-50万': 0,
        '50-100万': 0,
        '100-500万': 0,
        '500万以上': 0
    }
    
    for v in videos_data:
        views = v['view_count']
        if views < 10000:
            view_ranges['0-1万'] += 1
        elif views < 100000:
            view_ranges['1-10万'] += 1
        elif views < 500000:
            view_ranges['10-50万'] += 1
        elif views < 1000000:
            view_ranges['50-100万'] += 1
        elif views < 5000000:
            view_ranges['100-500万'] += 1
        else:
            view_ranges['500万以上'] += 1
    
    report_lines.append("\n### 3.2 播放量区间分布\n\n")
    report_lines.append("| 播放量区间 | 视频数量 | 占比 |\n")
    report_lines.append("|------------|----------|------|\n")
    
    for range_name, count in view_ranges.items():
        percentage = (count / len(videos_data) * 100) if videos_data else 0
        report_lines.append(f"| {range_name} | {count} | {percentage:.1f}% |\n")
    
    report_lines.append("\n")
    
    # 4. 时长分析
    print_colored("⏱️  分析时长分布...", Colors.CYAN)
    duration_ranges = {
        '0-5分钟': 0,
        '5-10分钟': 0,
        '10-15分钟': 0,
        '15-30分钟': 0,
        '30-60分钟': 0,
        '60分钟以上': 0
    }
    
    for v in videos_data:
        duration = v['duration']
        if duration < 300:
            duration_ranges['0-5分钟'] += 1
        elif duration < 600:
            duration_ranges['5-10分钟'] += 1
        elif duration < 900:
            duration_ranges['10-15分钟'] += 1
        elif duration < 1800:
            duration_ranges['15-30分钟'] += 1
        elif duration < 3600:
            duration_ranges['30-60分钟'] += 1
        else:
            duration_ranges['60分钟以上'] += 1
    
    report_lines.append("## 4. 时长分布分析\n\n")
    report_lines.append("| 时长区间 | 视频数量 | 占比 |\n")
    report_lines.append("|----------|----------|------|\n")
    
    for range_name, count in duration_ranges.items():
        percentage = (count / len(videos_data) * 100) if videos_data else 0
        report_lines.append(f"| {range_name} | {count} | {percentage:.1f}% |\n")
    
    report_lines.append("\n")
    
    # 5. 分类统计
    print_colored("📂 分析分类分布...", Colors.CYAN)
    category_stats = defaultdict(lambda: {'count': 0, 'views': 0, 'likes': 0})
    
    for v in videos_data:
        categories = v['category'].split(';') if v['category'] else []
        for cat in categories:
            cat = cat.strip()
            if cat:
                category_stats[cat]['count'] += 1
                category_stats[cat]['views'] += v['view_count']
                category_stats[cat]['likes'] += v['like_count']
    
    if category_stats:
        report_lines.append("## 5. 分类统计\n\n")
        report_lines.append("| 分类 | 视频数 | 总播放量 | 总点赞量 | 平均播放量 |\n")
        report_lines.append("|------|--------|----------|----------|------------|\n")
        
        sorted_categories = sorted(category_stats.items(), key=lambda x: x[1]['count'], reverse=True)
        for cat, stats in sorted_categories:
            avg_views = stats['views'] / stats['count'] if stats['count'] > 0 else 0
            report_lines.append(f"| {cat} | {stats['count']} | {stats['views']:,} | {stats['likes']:,} | {avg_views:,.0f} |\n")
        
        report_lines.append("\n")
    
    # 6. 标签分析
    print_colored("🏷️  分析标签分布...", Colors.CYAN)
    tag_counter = Counter()
    
    for v in videos_data:
        tags = v['tags'].split(';') if v['tags'] else []
        for tag in tags:
            tag = tag.strip()
            if tag:
                tag_counter[tag] += 1
    
    if tag_counter:
        report_lines.append("## 6. 热门标签（前20）\n\n")
        report_lines.append("| 标签 | 出现次数 |\n")
        report_lines.append("|------|----------|\n")
        
        for tag, count in tag_counter.most_common(20):
            report_lines.append(f"| {tag} | {count} |\n")
        
        report_lines.append("\n")
    
    # 7. 语言统计
    print_colored("🌐 分析语言分布...", Colors.CYAN)
    language_stats = Counter()
    
    for v in videos_data:
        lang = v['language'].strip()
        if lang:
            language_stats[lang] += 1
    
    if language_stats:
        report_lines.append("## 7. 语言分布\n\n")
        report_lines.append("| 语言 | 视频数量 | 占比 |\n")
        report_lines.append("|------|----------|------|\n")
        
        for lang, count in language_stats.most_common():
            percentage = (count / len(videos_data) * 100) if videos_data else 0
            report_lines.append(f"| {lang} | {count} | {percentage:.1f}% |\n")
        
        report_lines.append("\n")
    
    # 8. 趋势分析
    print_colored("📊 生成趋势分析...", Colors.CYAN)
    if len(year_stats) > 1:
        report_lines.append("## 8. 年度趋势分析\n\n")
        report_lines.append("### 8.1 视频数量趋势\n\n")
        report_lines.append("| 年份 | 视频数 | 变化 |\n")
        report_lines.append("|------|--------|------|\n")
        
        sorted_years = sorted(year_stats.keys())
        prev_count = None
        for year in sorted_years:
            count = year_stats[year]['count']
            if prev_count is not None:
                change = count - prev_count
                change_str = f"+{change}" if change > 0 else str(change)
                report_lines.append(f"| {year} | {count} | {change_str} |\n")
            else:
                report_lines.append(f"| {year} | {count} | - |\n")
            prev_count = count
        
        report_lines.append("\n### 8.2 播放量趋势\n\n")
        report_lines.append("| 年份 | 总播放量 | 平均播放量 | 变化 |\n")
        report_lines.append("|------|----------|------------|------|\n")
        
        prev_avg = None
        for year in sorted_years:
            stats = year_stats[year]
            avg_views = stats['views'] / stats['count'] if stats['count'] > 0 else 0
            if prev_avg is not None:
                change = avg_views - prev_avg
                change_str = f"+{change:,.0f}" if change > 0 else f"{change:,.0f}"
                report_lines.append(f"| {year} | {stats['views']:,} | {avg_views:,.0f} | {change_str} |\n")
            else:
                report_lines.append(f"| {year} | {stats['views']:,} | {avg_views:,.0f} | - |\n")
            prev_avg = avg_views
        
        report_lines.append("\n")
    
    # 9. 视频状态统计
    print_colored("✅ 分析视频状态...", Colors.CYAN)
    status_stats = Counter()
    for v in videos_data:
        status = v.get('status', 'available')
        status_stats[status] += 1
    
    if status_stats:
        report_lines.append("## 9. 视频状态统计\n\n")
        report_lines.append("| 状态 | 数量 | 占比 |\n")
        report_lines.append("|------|------|------|\n")
        
        status_names = {
            'available': '可用',
            'unavailable': '不可用',
            'private': '私有',
            'deleted': '已删除',
            'error': '检查失败'
        }
        
        for status, count in status_stats.items():
            percentage = (count / len(videos_data) * 100) if videos_data else 0
            status_name = status_names.get(status, status)
            report_lines.append(f"| {status_name} | {count} | {percentage:.1f}% |\n")
        
        report_lines.append("\n")
    
    # 保存报告
    if not output_report:
        output_report = str(csv_path.with_suffix('.analysis.md'))
    
    print_colored(f"正在保存分析报告...", Colors.BLUE)
    
    try:
        with open(output_report, 'w', encoding='utf-8') as f:
            f.writelines(report_lines)
        
        print_colored(f"✅ 分析报告已保存: {output_report}", Colors.GREEN)
        logger.info(f"分析报告已保存: {output_report}")
        print()
        
        # 显示报告摘要
        print_colored("报告摘要:", Colors.YELLOW)
        print_colored(f"  总视频数: {len(videos_data)}", Colors.CYAN)
        print_colored(f"  总播放量: {total_views:,}", Colors.BLUE)
        print_colored(f"  总点赞量: {total_likes:,}", Colors.MAGENTA)
        print_colored(f"  平均播放量: {avg_views:,.0f}", Colors.CYAN)
        print_colored(f"  报告文件: {output_report}", Colors.CYAN)
        logger.info(f"分析完成 - 总视频数: {len(videos_data)}, 总播放量: {total_views:,}")
        print()
        
        return True
    except Exception as e:
        error_msg = f"保存报告失败: {str(e)}"
        print_colored(f"❌ {error_msg}", Colors.RED)
        logger.error(error_msg, exc_info=True)
        return False

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='分析CSV文件中的视频数据并生成详细报告')
    parser.add_argument('csv_file', help='要分析的CSV文件路径')
    parser.add_argument('-o', '--output', help='输出报告文件路径（默认: 输入文件名.analysis.md）')
    
    args = parser.parse_args()
    
    # 执行分析
    success = analyze_videos(args.csv_file, args.output)
    
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

