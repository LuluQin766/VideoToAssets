#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新视频统计数据工具
更新已有CSV文件中的播放量、点赞数等会变化的字段
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

def format_duration(seconds):
    """将秒数格式化为 MM:SS 或 HH:MM:SS"""
    if not seconds or seconds == 0:
        return ""
    try:
        seconds = int(float(seconds))
    except (ValueError, TypeError):
        return ""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"

def get_video_stats(video_url, logger=None):
    """获取视频的统计数据（播放量、点赞数等）"""
    try:
        ydl_opts = YT_DLP_DEFAULT_OPTS.copy()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            if not info:
                return None
            
            # 提取会变化的统计数据
            view_count = info.get('view_count', 0) or 0
            like_count = info.get('like_count', 0) or 0
            comment_count = info.get('comment_count', 0) or 0
            
            # 转换为整数
            try:
                view_count = int(view_count) if view_count else 0
            except (ValueError, TypeError):
                view_count = 0
            
            try:
                like_count = int(like_count) if like_count else 0
            except (ValueError, TypeError):
                like_count = 0
            
            try:
                comment_count = int(comment_count) if comment_count else 0
            except (ValueError, TypeError):
                comment_count = 0
            
            # 计算点赞率
            like_rate = (like_count / view_count * 100) if view_count > 0 else 0
            
            stats = {
                'view_count': view_count,
                'like_count': like_count,
                'comment_count': comment_count,
                'like_rate': like_rate,
            }
            if logger:
                logger.debug(f"成功获取视频统计: {video_url}")
            return stats
    except Exception as e:
        if logger:
            logger.warning(f"获取视频统计失败: {video_url} - {str(e)}")
        return None

def update_single_video(row, lock, updated_count, failed_count, logger=None):
    """更新单个视频的统计数据"""
    video_id = row.get('视频ID', '').strip()
    video_url = row.get('视频链接', '').strip()
    video_title = row.get('视频标题', '').strip()
    
    if not video_id or not video_url:
        return row, False
    
    try:
        stats = get_video_stats(video_url, logger=logger)
        if not stats:
            with lock:
                failed_count[0] += 1
            return row, False
        
        # 更新统计数据
        row['播放量'] = stats['view_count']
        row['点赞量'] = stats['like_count']
        row['评论数'] = stats['comment_count']
        row['点赞率(%)'] = f"{stats['like_rate']:.2f}"
        
        with lock:
            updated_count[0] += 1
        
        return row, True
    except Exception as e:
        with lock:
            failed_count[0] += 1
        return row, False

def update_video_stats(csv_file, output_file=None, max_workers=None):
    """更新CSV文件中的视频统计数据"""
    # 设置日志
    log_file = get_log_file_name('update_video_stats')
    logger = setup_logger('update_video_stats', log_file)
    logger.info("=" * 60)
    logger.info("视频统计数据更新工具")
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
    print_colored("视频统计数据更新工具", Colors.GREEN)
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
            headers = reader.fieldnames
            rows = list(reader)
        
        print_colored(f"✅ 读取到 {len(rows)} 条视频记录", Colors.GREEN)
        print()
    except Exception as e:
        print_colored(f"❌ 读取CSV文件失败: {str(e)}", Colors.RED)
        return False
    
    if not rows:
        print_colored("⚠️  CSV文件中没有数据", Colors.YELLOW)
        return False
    
    # 更新统计数据
    print_colored(f"正在更新 {len(rows)} 个视频的统计数据...", Colors.BLUE)
    print_colored("这可能需要一些时间，请耐心等待...", Colors.YELLOW)
    print()
    
    updated_count = [0]  # 使用列表以便在函数中修改
    failed_count = [0]
    updated_rows = []
    
    lock = Lock()
    
    logger.info(f"开始更新 {len(rows)} 个视频的统计数据")
    
    # 使用线程池并发更新
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_row = {
            executor.submit(update_single_video, row, lock, updated_count, failed_count, logger): (i, row)
            for i, row in enumerate(rows)
        }
        
        for future in as_completed(future_to_row):
            i, original_row = future_to_row[future]
            try:
                updated_row, success = future.result()
                updated_rows.append(updated_row)
                
                video_title = updated_row.get('视频标题', 'Unknown')[:50]
                if success:
                    view_count = updated_row.get('播放量', 0)
                    like_count = updated_row.get('点赞量', 0)
                    print_colored(f"✅ [{i+1}/{len(rows)}] {video_title} - 播放量: {view_count:,}, 点赞: {like_count:,}", Colors.GREEN)
                else:
                    print_colored(f"❌ [{i+1}/{len(rows)}] {video_title} - 更新失败", Colors.RED)
                
                # 显示进度
                progress = len(updated_rows) / len(rows) * 100
                print_colored(f"进度: {len(updated_rows)}/{len(rows)} ({progress:.1f}%) | 成功: {updated_count[0]} | 失败: {failed_count[0]}", Colors.CYAN, end='\r')
            except Exception as e:
                updated_rows.append(original_row)
                with lock:
                    failed_count[0] += 1
                print_colored(f"❌ [{i+1}/{len(rows)}] 异常: {str(e)}", Colors.RED)
    
    print()  # 换行
    
    # 保存更新后的CSV
    print_colored(f"正在保存更新后的CSV文件...", Colors.BLUE)
    
    try:
        with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(updated_rows)
        
        print_colored(f"✅ CSV文件已更新: {output_file}", Colors.GREEN)
        print()
        
        # 显示统计信息
        print_colored("更新统计:", Colors.YELLOW)
        print_colored(f"  总视频数: {len(rows)}", Colors.CYAN)
        print_colored(f"  成功更新: {updated_count[0]}", Colors.GREEN)
        print_colored(f"  更新失败: {failed_count[0]}", Colors.RED if failed_count[0] > 0 else Colors.GREEN)
        print()
        
        return True
    except Exception as e:
        print_colored(f"❌ 保存CSV文件失败: {str(e)}", Colors.RED)
        return False

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='更新CSV文件中的视频统计数据（播放量、点赞数等）')
    parser.add_argument('csv_file', help='要更新的CSV文件路径')
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
    
    # 执行更新
    success = update_video_stats(args.csv_file, args.output, args.workers)
    
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

