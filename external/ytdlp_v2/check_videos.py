#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频质量检查工具
批量检查CSV文件中的视频是否仍可用（未被删除、设为私有等）
"""

import csv
import sys
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import yt_dlp
from config import (
    OUTPUT_PATH,
    DEFAULT_MAX_WORKERS, MAX_WORKERS_LIMIT, RECOMMENDED_WORKERS_MIN, RECOMMENDED_WORKERS_MAX,
    GET_INFO_TIMEOUT,
    YT_DLP_DEFAULT_OPTS
)
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

def check_video_status(video_url, video_id, video_title, logger=None):
    """检查单个视频的状态
    
    Returns:
        (status, message, details)
        status: 'available', 'unavailable', 'private', 'deleted', 'error'
    """
    try:
        ydl_opts = YT_DLP_DEFAULT_OPTS.copy()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
            if not info:
                return ('unavailable', '无法获取视频信息', {})
            
            # 检查可用性
            availability = info.get('availability', '')
            
            if availability in ['private', 'premium_only', 'subscriber_only']:
                return ('private', f'视频为{availability}状态', {
                    'availability': availability,
                    'title': info.get('title', ''),
                })
            
            if availability == 'unlisted':
                return ('unavailable', '视频为未列出状态', {
                    'availability': availability,
                    'title': info.get('title', ''),
                })
            
            # 视频可用
            return ('available', '视频可用', {
                'availability': availability,
                'title': info.get('title', ''),
                'view_count': info.get('view_count', 0),
                'like_count': info.get('like_count', 0),
            })
    
    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e).lower()
        if 'private' in error_msg or 'private video' in error_msg:
            return ('private', '视频为私有', {})
        elif 'unavailable' in error_msg or 'not available' in error_msg:
            return ('unavailable', '视频不可用', {})
        elif 'deleted' in error_msg or 'removed' in error_msg:
            return ('deleted', '视频已删除', {})
        else:
            return ('error', f'检查失败: {str(e)[:100]}', {})
    except Exception as e:
        return ('error', f'检查异常: {str(e)[:100]}', {})

def check_single_video(row, lock, stats, logger=None):
    """检查单个视频并更新统计"""
    video_id = row.get('视频ID', '').strip()
    video_url = row.get('视频链接', '').strip()
    video_title = row.get('视频标题', '').strip()
    
    if not video_id or not video_url:
        return row, 'error', '缺少视频ID或链接'
    
    status, message, details = check_video_status(video_url, video_id, video_title, logger=logger)
    
    # 更新行数据
    row['视频状态'] = status
    row['状态说明'] = message
    
    # 如果视频可用，更新统计数据
    if status == 'available' and details:
        if 'view_count' in details:
            row['播放量'] = details.get('view_count', row.get('播放量', 0))
        if 'like_count' in details:
            row['点赞量'] = details.get('like_count', row.get('点赞量', 0))
    
    # 更新统计
    with lock:
        stats[status] = stats.get(status, 0) + 1
    
    return row, status, message

def check_videos(csv_file, output_file=None, max_workers=None):
    """检查CSV文件中的视频可用性"""
    # 设置日志
    log_file = get_log_file_name('check_videos')
    logger = setup_logger('check_videos', log_file)
    logger.info("=" * 60)
    logger.info("视频质量检查工具")
    logger.info("=" * 60)
    
    csv_path = Path(csv_file)
    
    if not csv_path.exists():
        error_msg = f"文件不存在: {csv_file}"
        print_colored(f"❌ {error_msg}", Colors.RED)
        logger.error(error_msg)
        return False
    
    # 使用配置的默认并发数
    if max_workers is None:
        max_workers = DEFAULT_MAX_WORKERS
    
    # 如果没有指定输出文件，覆盖原文件
    if not output_file:
        output_file = str(csv_path)
        backup_file = str(csv_path.with_suffix('.csv.backup'))
        # 创建备份
        import shutil
        shutil.copy2(csv_path, backup_file)
        print_colored(f"📦 已创建备份文件: {backup_file}", Colors.CYAN)
        logger.info(f"已创建备份文件: {backup_file}")
    else:
        output_file = str(Path(output_file))
    
    print_colored("=" * 60, Colors.CYAN)
    print_colored("视频质量检查工具", Colors.GREEN)
    print_colored("=" * 60, Colors.CYAN)
    print()
    print_colored(f"输入文件: {csv_file}", Colors.BLUE)
    print_colored(f"输出文件: {output_file}", Colors.BLUE)
    print_colored(f"并发线程数: {max_workers}", Colors.CYAN)
    logger.info(f"输入文件: {csv_file}, 输出文件: {output_file}, 并发数: {max_workers}")
    print()
    
    # 读取CSV文件
    print_colored("正在读取CSV文件...", Colors.CYAN)
    rows = []
    headers = []
    
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            headers = list(reader.fieldnames)
            rows = list(reader)
        
        # 添加状态列（如果不存在）
        if '视频状态' not in headers:
            headers.append('视频状态')
        if '状态说明' not in headers:
            headers.append('状态说明')
        
        print_colored(f"✅ 读取到 {len(rows)} 条视频记录", Colors.GREEN)
        print()
    except Exception as e:
        print_colored(f"❌ 读取CSV文件失败: {str(e)}", Colors.RED)
        return False
    
    if not rows:
        print_colored("⚠️  CSV文件中没有数据", Colors.YELLOW)
        return False
    
    # 检查视频状态
    print_colored(f"正在检查 {len(rows)} 个视频的状态...", Colors.BLUE)
    print_colored("这可能需要一些时间，请耐心等待...", Colors.YELLOW)
    print()
    
    checked_rows = []
    stats = {
        'available': 0,
        'unavailable': 0,
        'private': 0,
        'deleted': 0,
        'error': 0
    }
    
    lock = Lock()
    completed_count = 0
    
    logger.info(f"开始检查 {len(rows)} 个视频的状态")
    
    # 使用线程池并发检查
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_row = {
            executor.submit(check_single_video, row, lock, stats, logger): (i, row)
            for i, row in enumerate(rows)
        }
        
        for future in as_completed(future_to_row):
            i, original_row = future_to_row[future]
            completed_count += 1
            
            try:
                updated_row, status, message = future.result()
                checked_rows.append(updated_row)
                
                video_title = updated_row.get('视频标题', 'Unknown')[:50]
                
                # 根据状态显示不同颜色
                if status == 'available':
                    print_colored(f"✅ [{completed_count}/{len(rows)}] {video_title}", Colors.GREEN)
                elif status == 'private':
                    print_colored(f"🔒 [{completed_count}/{len(rows)}] {video_title} - {message}", Colors.YELLOW)
                elif status == 'unavailable':
                    print_colored(f"⚠️  [{completed_count}/{len(rows)}] {video_title} - {message}", Colors.YELLOW)
                elif status == 'deleted':
                    print_colored(f"❌ [{completed_count}/{len(rows)}] {video_title} - {message}", Colors.RED)
                else:
                    print_colored(f"❓ [{completed_count}/{len(rows)}] {video_title} - {message}", Colors.RED)
                
                # 显示进度
                progress = completed_count / len(rows) * 100
                available_count = stats.get('available', 0)
                unavailable_count = stats.get('unavailable', 0) + stats.get('private', 0) + stats.get('deleted', 0)
                print_colored(f"进度: {completed_count}/{len(rows)} ({progress:.1f}%) | 可用: {available_count} | 不可用: {unavailable_count}", Colors.CYAN, end='\r')
            except Exception as e:
                checked_rows.append(original_row)
                with lock:
                    stats['error'] = stats.get('error', 0) + 1
                print_colored(f"❓ [{completed_count}/{len(rows)}] 异常: {str(e)}", Colors.RED)
    
    print()  # 换行
    
    # 保存检查结果
    print_colored(f"正在保存检查结果...", Colors.BLUE)
    
    try:
        with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(checked_rows)
        
        print_colored(f"✅ 检查结果已保存: {output_file}", Colors.GREEN)
        print()
        
        # 显示统计信息
        print_colored("检查统计:", Colors.YELLOW)
        print_colored(f"  总视频数: {len(rows)}", Colors.CYAN)
        print_colored(f"  ✅ 可用: {stats.get('available', 0)}", Colors.GREEN)
        print_colored(f"  ⚠️  不可用: {stats.get('unavailable', 0)}", Colors.YELLOW)
        print_colored(f"  🔒 私有: {stats.get('private', 0)}", Colors.YELLOW)
        print_colored(f"  ❌ 已删除: {stats.get('deleted', 0)}", Colors.RED)
        print_colored(f"  ❓ 检查失败: {stats.get('error', 0)}", Colors.RED)
        
        # 计算可用率
        total_checked = sum(stats.values())
        if total_checked > 0:
            available_rate = (stats.get('available', 0) / total_checked) * 100
            print_colored(f"  可用率: {available_rate:.1f}%", Colors.CYAN)
        print()
        
        return True
    except Exception as e:
        print_colored(f"❌ 保存文件失败: {str(e)}", Colors.RED)
        return False

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='检查CSV文件中的视频是否仍可用')
    parser.add_argument('csv_file', help='要检查的CSV文件路径')
    parser.add_argument('-o', '--output', help='输出CSV文件路径（默认覆盖原文件并创建备份）')
    parser.add_argument('-w', '--workers', type=int, default=None,
                        help=f'并发线程数（默认{DEFAULT_MAX_WORKERS}）')
    
    args = parser.parse_args()
    
    # 使用配置的默认值
    if args.workers is None:
        args.workers = DEFAULT_MAX_WORKERS
    
    # 验证并发数
    if args.workers < 1:
        print_colored("错误: 并发线程数必须大于0", Colors.RED)
        sys.exit(1)
    if args.workers > MAX_WORKERS_LIMIT:
        print_colored(f"警告: 并发线程数过大可能导致API限制，建议使用{RECOMMENDED_WORKERS_MIN}-{RECOMMENDED_WORKERS_MAX}", Colors.YELLOW)
    
    # 执行检查
    success = check_videos(args.csv_file, args.output, args.workers)
    
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

