#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从YouTube账号获取前100个播放量最高的视频并保存到CSV
"""

import re
import json
import sys
import csv
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import yt_dlp
from config import OUTPUT_PATH, YT_DLP_DEFAULT_OPTS
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

def extract_channel_url(user_input):
    """从用户输入中提取频道URL或ID，并转换为视频列表URL"""
    base_url = ""
    
    # 如果是完整的URL
    if 'youtube.com' in user_input or 'youtu.be' in user_input:
        # 提取频道ID或用户名
        if '/channel/' in user_input:
            channel_id = re.search(r'/channel/([^/?]+)', user_input)
            if channel_id:
                base_url = f"https://www.youtube.com/channel/{channel_id.group(1)}"
        elif '/c/' in user_input:
            channel_name = re.search(r'/c/([^/?]+)', user_input)
            if channel_name:
                base_url = f"https://www.youtube.com/c/{channel_name.group(1)}"
        elif '/user/' in user_input:
            username = re.search(r'/user/([^/?]+)', user_input)
            if username:
                base_url = f"https://www.youtube.com/user/{username.group(1)}"
        elif '/@' in user_input:
            handle = re.search(r'/@([^/?]+)', user_input)
            if handle:
                base_url = f"https://www.youtube.com/@{handle.group(1)}"
        else:
            base_url = user_input
    # 如果是@handle格式
    elif user_input.startswith('@'):
        base_url = f"https://www.youtube.com/{user_input}"
    # 如果只是用户名或ID
    else:
        # 尝试作为频道ID
        if len(user_input) > 10:
            base_url = f"https://www.youtube.com/channel/{user_input}"
        else:
            base_url = f"https://www.youtube.com/@{user_input}"
    
    # 转换为视频列表URL（添加/videos）
    if base_url and not base_url.endswith('/videos'):
        if base_url.endswith('/'):
            return f"{base_url}videos"
        else:
            return f"{base_url}/videos"
    
    return base_url

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

def format_date(date_str):
    """格式化日期字符串 YYYYMMDD -> YYYY-MM-DD"""
    if not date_str or len(date_str) < 8:
        return ""
    try:
        year = date_str[:4]
        month = date_str[4:6]
        day = date_str[6:8]
        return f"{year}-{month}-{day}"
    except:
        return date_str[:4] if len(date_str) >= 4 else ""

def get_channel_videos(channel_url, max_videos=100, logger=None):
    """获取频道的所有视频信息"""
    print_colored(f"正在获取频道视频列表...", Colors.CYAN)
    print_colored(f"频道URL: {channel_url}", Colors.BLUE)
    if logger:
        logger.info(f"开始获取频道视频列表: {channel_url}, 最大数量: {max_videos}")
    print()
    
    try:
        # 使用yt-dlp获取频道视频列表
        ydl_opts = YT_DLP_DEFAULT_OPTS.copy()
        ydl_opts['extract_flat'] = True
        ydl_opts['playlistend'] = max_videos * 2  # 获取更多以便排序
        
        videos = []
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(channel_url, download=False)
            
            if not result or 'entries' not in result:
                print_colored(f"获取视频列表失败", Colors.RED)
                return []
            
            # 处理视频列表
            for entry in result['entries']:
                if not entry:
                    continue
                
                video_id = entry.get('id', '')
                if not video_id:
                    continue
                
                videos.append({
                    'id': video_id,
                    'url': f"https://www.youtube.com/watch?v={video_id}",
                    'title': entry.get('title', ''),
                    'duration': entry.get('duration', 0) or 0
                })
        
        print_colored(f"获取到 {len(videos)} 个视频，正在获取详细信息...", Colors.GREEN)
        if logger:
            logger.info(f"成功获取 {len(videos)} 个视频")
        print()
        
        return videos
    
    except Exception as e:
        error_msg = f"获取视频列表出错: {str(e)}"
        print_colored(error_msg, Colors.RED)
        if logger:
            logger.error(error_msg, exc_info=True)
        return []

def get_video_details(video_id, logger=None):
    """获取单个视频的详细信息"""
    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        ydl_opts = YT_DLP_DEFAULT_OPTS.copy()
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            data = ydl.extract_info(url, download=False)
        
        if not data:
            return None
        
        # 提取信息
        view_count = data.get('view_count', 0) or 0
        like_count = data.get('like_count', 0) or 0
        duration = data.get('duration', 0) or 0
        upload_date = data.get('upload_date', '') or ''
        
        # 转换为整数
        try:
            view_count = int(view_count) if view_count else 0
        except (ValueError, TypeError):
            view_count = 0
        
        try:
            like_count = int(like_count) if like_count else 0
        except (ValueError, TypeError):
            like_count = 0
        
        result = {
            'view_count': view_count,
            'like_count': like_count,
            'duration': duration,
            'duration_str': format_duration(duration),
            'upload_date': upload_date,
            'date_str': format_date(upload_date),
            'title': data.get('title', ''),
            'description': data.get('description', '')[:200]  # 限制描述长度
        }
        if logger:
            logger.debug(f"成功获取视频详情: {video_id}")
        return result
    
    except Exception as e:
        if logger:
            logger.warning(f"获取视频详情失败: {video_id} - {str(e)}")
        return None

def get_top_videos(channel_url, top_n=100, output_csv=None):
    """获取频道前N个播放量最高的视频"""
    # 设置日志
    log_file = get_log_file_name('get_top_videos')
    logger = setup_logger('get_top_videos', log_file)
    logger.info("=" * 60)
    logger.info("YouTube 频道视频获取工具")
    logger.info("=" * 60)
    
    print_colored("=" * 60, Colors.CYAN)
    print_colored("YouTube 频道视频获取工具", Colors.GREEN)
    print_colored("=" * 60, Colors.CYAN)
    print()
    
    # 获取视频列表
    videos = get_channel_videos(channel_url, max_videos=top_n * 2, logger=logger)
    
    if not videos:
        print_colored("❌ 未能获取到任何视频", Colors.RED)
        return False
    
    # 获取每个视频的详细信息
    print_colored(f"正在获取 {len(videos)} 个视频的详细信息...", Colors.BLUE)
    print_colored("这可能需要一些时间，请耐心等待...", Colors.YELLOW)
    print()
    
    detailed_videos = []
    for i, video in enumerate(videos, 1):
        print_colored(f"[{i}/{len(videos)}] 正在获取: {video['title'][:50]}...", Colors.CYAN, end='\r')
        
        details = get_video_details(video['id'], logger=logger)
        if details:
            video.update(details)
            detailed_videos.append(video)
        else:
            # 即使获取详细信息失败，也保留基本信息
            video.update({
                'view_count': 0,
                'like_count': 0,
                'duration': 0,
                'duration_str': '',
                'upload_date': '',
                'date_str': '',
                'description': ''
            })
            detailed_videos.append(video)
    
    print()  # 换行
    print_colored(f"✅ 成功获取 {len(detailed_videos)} 个视频的详细信息", Colors.GREEN)
    print()
    
    # 按播放量排序
    print_colored("正在按播放量排序...", Colors.BLUE)
    detailed_videos.sort(key=lambda x: x.get('view_count', 0), reverse=True)
    
    # 取前N个
    top_videos = detailed_videos[:top_n]
    
    # 生成CSV
    if not output_csv:
        # 使用默认文件名（保存在输出目录）
        channel_name = channel_url.split('/')[-1].replace('@', '')
        output_csv = str(OUTPUT_PATH / f"{channel_name}_top{top_n}_videos.csv")
    
    print_colored(f"正在生成CSV文件: {output_csv}", Colors.BLUE)
    
    try:
        with open(output_csv, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            
            # 写入表头
            writer.writerow([
                '排名',
                '视频标题',
                '播放量',
                '点赞量',
                '发布日期',
                '视频长度',
                '视频ID',
                'YouTube链接',
                '描述（前200字符）'
            ])
            
            # 写入数据
            for i, video in enumerate(top_videos, 1):
                writer.writerow([
                    i,
                    video.get('title', ''),
                    f"{video.get('view_count', 0):,}",
                    f"{video.get('like_count', 0):,}",
                    video.get('date_str', ''),
                    video.get('duration_str', ''),
                    video.get('id', ''),
                    video.get('url', ''),
                    video.get('description', '')
                ])
        
        print_colored(f"✅ CSV文件已生成: {output_csv}", Colors.GREEN)
        print_colored(f"共 {len(top_videos)} 个视频", Colors.CYAN)
        print()
        
        # 显示前5个视频的统计
        print_colored("前5个视频:", Colors.YELLOW)
        for i, video in enumerate(top_videos[:5], 1):
            print_colored(f"  {i}. {video.get('title', '')[:60]}", Colors.CYAN)
            print_colored(f"     播放量: {video.get('view_count', 0):,}", Colors.BLUE)
            print_colored(f"     点赞量: {video.get('like_count', 0):,}", Colors.MAGENTA)
            print()
        
        return True
    
    except Exception as e:
        print_colored(f"生成CSV时出错: {str(e)}", Colors.RED)
        return False

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='从YouTube账号获取前N个播放量最高的视频')
    parser.add_argument('channel_url', help='YouTube频道URL或@用户名')
    parser.add_argument('-n', '--top-n', type=int, default=100, help='获取前N个视频（默认100）')
    parser.add_argument('-o', '--output', help='输出CSV文件路径（默认自动生成）')
    
    args = parser.parse_args()
    
    # 提取并规范化频道URL
    channel_url = extract_channel_url(args.channel_url)
    
    # 执行获取
    success = get_top_videos(channel_url, args.top_n, args.output)
    
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

