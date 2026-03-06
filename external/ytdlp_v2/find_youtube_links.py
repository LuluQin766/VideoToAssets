#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通过视频标题在YouTube中搜索并获取真实链接
使用yt-dlp进行搜索
"""

import re
import json
import sys
from pathlib import Path
import yt_dlp
from config import OUTPUT_PATH, DOWNLOAD_LIST_PATH, DEFAULT_CHANNEL_NAME

# 配置
OUTPUT_DIR = OUTPUT_PATH  # 输出目录
CHANNEL_NAME = DEFAULT_CHANNEL_NAME  # 可选：限制搜索范围到特定频道

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
    # 确保转换为整数
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
    """格式化日期字符串 YYYYMMDD -> YYYY"""
    if not date_str or len(date_str) < 4:
        return ""
    return date_str[:4]

def verify_video_link(video_id):
    """
    验证视频链接是否可访问和可下载
    
    Args:
        video_id: 视频ID
    
    Returns:
        (is_valid, details): (是否有效, 视频详细信息或None)
    """
    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        
        # 使用 yt-dlp 库的 API
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'noplaylist': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            data = ydl.extract_info(url, download=False)
        
        if not data:
            return False, None
        
        # 检查视频是否可用（不是私有、删除等）
        availability = data.get('availability', '')
        if availability in ['private', 'premium_only', 'subscriber_only', 'unlisted']:
            # 这些状态可能无法下载
            return False, None
        
        # 提取详细信息
        details = {
            'view_count': data.get('view_count', 0) or 0,
            'like_count': data.get('like_count', 0) or 0,
            'duration': data.get('duration', 0) or 0,
            'upload_date': data.get('upload_date', '') or '',
            'duration_str': format_duration(data.get('duration', 0)),
            'date_str': format_date(data.get('upload_date', '')),
            'title': data.get('title', ''),
            'availability': availability
        }
        
        return True, details
    
    except Exception as e:
        return False, None

def get_video_details(video_id):
    """获取视频的详细信息（兼容旧代码）"""
    is_valid, details = verify_video_link(video_id)
    if is_valid:
        return details
    return None

def search_youtube_video(title, channel=None, max_results=5):
    """
    在YouTube中搜索视频
    
    Args:
        title: 视频标题
        channel: 频道名称（可选）
        max_results: 最大返回结果数
    
    Returns:
        视频ID列表，按相关性排序
    """
    # 构建搜索查询
    if channel:
        query = f"ytsearch{max_results}:{title} {channel}"
    else:
        query = f"ytsearch{max_results}:{title}"
    
    try:
        # 使用 yt-dlp 库的 API 进行搜索
        # 先使用 extract_flat 快速获取搜索结果
        ydl_opts_flat = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
        }
        
        videos = []
        with yt_dlp.YoutubeDL(ydl_opts_flat) as ydl:
            search_results = ydl.extract_info(query, download=False)
            
            if not search_results or 'entries' not in search_results:
                return []
            
            # 对每个搜索结果提取详细信息
            ydl_opts_detail = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }
            
            for entry in search_results['entries']:
                if not entry:
                    continue
                
                video_id = entry.get('id', '')
                if not video_id:
                    continue
                
                try:
                    # 获取详细信息
                    video_url = f"https://www.youtube.com/watch?v={video_id}"
                    with yt_dlp.YoutubeDL(ydl_opts_detail) as ydl_detail:
                        try:
                            detail_data = ydl_detail.extract_info(video_url, download=False)
                        except:
                            # 如果获取详细信息失败，使用基本信息
                            detail_data = entry
                    
                    video_title = detail_data.get('title', entry.get('title', ''))
                    
                    if video_title:
                        # 提取更多信息，确保类型正确
                        view_count = detail_data.get('view_count', 0) or 0
                        like_count = detail_data.get('like_count', 0) or 0
                        duration = detail_data.get('duration', 0) or 0
                        upload_date = detail_data.get('upload_date', '') or ''
                        
                        # 转换为整数（如果可能）
                        try:
                            view_count = int(view_count) if view_count else 0
                        except (ValueError, TypeError):
                            view_count = 0
                        
                        try:
                            like_count = int(like_count) if like_count else 0
                        except (ValueError, TypeError):
                            like_count = 0
                        
                        # 格式化时长
                        duration_str = format_duration(duration)
                        
                        # 格式化日期
                        date_str = format_date(upload_date)
                        
                        videos.append({
                            'id': video_id,
                            'title': video_title,
                            'url': video_url,
                            'view_count': view_count,
                            'like_count': like_count,
                            'duration': duration,
                            'duration_str': duration_str,
                            'upload_date': upload_date,
                            'date_str': date_str
                        })
                except Exception as e:
                    # 如果格式化失败，仍然添加基本信息
                    video_title = entry.get('title', '')
                    if video_title:
                        videos.append({
                            'id': video_id,
                            'title': video_title,
                            'url': f"https://www.youtube.com/watch?v={video_id}",
                            'view_count': 0,
                            'like_count': 0,
                            'duration': 0,
                            'duration_str': '',
                            'upload_date': '',
                            'date_str': ''
                        })
        
        return videos
    
    except Exception as e:
        print_colored(f"搜索出错: {str(e)}", Colors.RED)
        return []

def extract_video_id_from_url(url):
    """从URL中提取视频ID"""
    patterns = [
        r'youtu\.be/([a-zA-Z0-9_-]+)',
        r'youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
        r'youtube\.com/embed/([a-zA-Z0-9_-]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def is_placeholder_id(video_id):
    """检查是否是占位符ID"""
    placeholder_patterns = [
        r'^[a-z]{3}\d{3}$',  # abc123格式
        r'^[A-Z_]+$',  # 全大写或下划线
    ]
    
    for pattern in placeholder_patterns:
        if re.match(pattern, video_id):
            return True
    return False

def read_download_list(download_file):
    """读取下载列表文件，返回已有的视频ID集合"""
    existing_ids = set()
    
    if not Path(download_file).exists():
        return existing_ids
    
    try:
        with open(download_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                # 提取embed链接中的视频ID
                video_id = extract_video_id_from_url(line)
                if video_id:
                    existing_ids.add(video_id)
    except Exception as e:
        print_colored(f"读取下载列表文件出错: {str(e)}", Colors.YELLOW)
    
    return existing_ids

def add_to_download_list(download_file, video_ids):
    """添加视频ID到下载列表文件"""
    if not video_ids:
        return 0
    
    # 读取现有内容
    existing_lines = []
    if Path(download_file).exists():
        with open(download_file, 'r', encoding='utf-8') as f:
            existing_lines = [line.rstrip() for line in f]
    
    # 提取已有的视频ID
    existing_ids = set()
    for line in existing_lines:
        video_id = extract_video_id_from_url(line)
        if video_id:
            existing_ids.add(video_id)
    
    # 添加新的视频ID（使用watch格式，不带引号）
    new_count = 0
    with open(download_file, 'a', encoding='utf-8') as f:
        for video_id in video_ids:
            if video_id not in existing_ids:
                # 使用watch格式，不带引号，这样yt-dlp可以直接使用
                watch_url = f"https://www.youtube.com/watch?v={video_id}"
                f.write(watch_url + '\n')
                existing_ids.add(video_id)
                new_count += 1
    
    return new_count

def remove_duplicates_from_download_list(download_file):
    """从下载列表文件中移除重复的链接"""
    if not Path(download_file).exists():
        return 0
    
    try:
        # 读取所有行
        lines = []
        seen_ids = set()
        duplicate_count = 0
        
        with open(download_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.rstrip()
                if not line or line.startswith('#'):
                    # 保留空行和注释
                    lines.append(line)
                    continue
                
                # 提取视频ID
                video_id = extract_video_id_from_url(line)
                if video_id:
                    if video_id not in seen_ids:
                        seen_ids.add(video_id)
                        lines.append(line)
                    else:
                        duplicate_count += 1
                else:
                    # 无法解析的行也保留
                    lines.append(line)
        
        # 如果有重复，重新写入文件
        if duplicate_count > 0:
            with open(download_file, 'w', encoding='utf-8') as f:
                for line in lines:
                    f.write(line + '\n')
            
            print_colored(f"✅ 已移除 {duplicate_count} 个重复链接", Colors.GREEN)
            return duplicate_count
        else:
            print_colored("✅ 未发现重复链接", Colors.GREEN)
            return 0
    
    except Exception as e:
        print_colored(f"去重时出错: {str(e)}", Colors.RED)
        return 0

def read_video_list(file_path):
    """从文件中读取视频列表"""
    videos = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 匹配表格行，包含所有列
    pattern = r'\|\s*(\d+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*\[[^\]]+\]\(([^\)]+)\)'
    matches = re.findall(pattern, content)
    
    for match in matches:
        rank = int(match[0])
        title = match[1].strip()
        views = match[2].strip()
        likes = match[3].strip()
        year = match[4].strip()
        duration = match[5].strip()
        url = match[6].strip()
        video_id = extract_video_id_from_url(url)
        
        videos.append({
            'rank': rank,
            'title': title,
            'original_title': title,
            'url': url,
            'video_id': video_id,
            'is_placeholder': is_placeholder_id(video_id) if video_id else True,
            'original_views': views,
            'original_likes': likes,
            'original_year': year,
            'original_duration': duration
        })
    
    return videos

def generate_csv_summary(videos, csv_file):
    """生成CSV格式的汇总表"""
    import csv
    
    try:
        with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            
            # 写入表头
            writer.writerow([
                '排名',
                '视频标题',
                '播放量',
                '点赞量',
                '发布年份',
                '视频长度',
                '视频ID',
                'YouTube链接'
            ])
            
            # 写入数据
            for video in videos:
                # 获取原始数据（如果存在）
                original_title = video.get('original_title', video.get('title', ''))
                original_views = video.get('original_views', '')
                original_likes = video.get('original_likes', '')
                original_year = video.get('original_year', video.get('date_str', ''))
                original_duration = video.get('original_duration', video.get('duration_str', ''))
                
                # 使用更新后的数据（如果存在）
                final_title = video.get('new_title', original_title)
                final_views = video.get('view_count', original_views)
                final_likes = video.get('like_count', original_likes)
                final_year = video.get('date_str', original_year)
                final_duration = video.get('duration_str', original_duration)
                
                # 格式化播放量和点赞量
                views_str = f"{final_views:,}" if isinstance(final_views, int) else str(final_views)
                likes_str = f"{final_likes:,}" if isinstance(final_likes, int) else str(final_likes)
                
                # 视频ID和链接
                video_id = video.get('new_video_id', video.get('video_id', ''))
                video_url = video.get('new_url', video.get('url', ''))
                
                writer.writerow([
                    video.get('rank', ''),
                    final_title,
                    views_str,
                    likes_str,
                    final_year,
                    final_duration,
                    video_id,
                    video_url
                ])
        
        print_colored(f"✅ CSV汇总表已生成: {csv_file}", Colors.GREEN)
        return True
    except Exception as e:
        print_colored(f"生成CSV时出错: {str(e)}", Colors.RED)
        return False

def update_video_links(input_file, output_file, channel=None, interactive=True, add_to_download_list_file=None, csv_output=None):
    """
    更新视频链接
    
    Args:
        input_file: 输入文件路径
        output_file: 输出文件路径（可选，如果为None则更新原文件）
        channel: 频道名称（可选）
        interactive: 是否交互式确认
        add_to_download_list_file: 下载列表文件路径（可选）
    """
    print_colored("=" * 60, Colors.CYAN)
    print_colored("YouTube 视频链接搜索工具", Colors.GREEN)
    print_colored("=" * 60, Colors.CYAN)
    print()
    
    # 读取下载列表（如果指定）
    existing_video_ids = set()
    if add_to_download_list_file:
        existing_video_ids = read_download_list(add_to_download_list_file)
        print_colored(f"已读取下载列表，现有 {len(existing_video_ids)} 个视频ID", Colors.BLUE)
        print()
    
    # 读取视频列表
    videos = read_video_list(input_file)
    print_colored(f"读取到 {len(videos)} 个视频", Colors.BLUE)
    print()
    
    # 找出需要更新的视频
    need_update = [v for v in videos if v['is_placeholder']]
    print_colored(f"需要更新的视频: {len(need_update)} 个", Colors.YELLOW)
    print()
    
    updated_count = 0
    failed_count = 0
    skipped_count = 0
    added_to_download_count = 0
    removed_count = 0
    
    # 处理每个需要更新的视频
    for video in need_update:
        print_colored("-" * 60, Colors.CYAN)
        print_colored(f"排名 {video['rank']}: {video['title']}", Colors.BLUE)
        print_colored(f"当前链接: {video['url']}", Colors.YELLOW)
        print()
        
        # 检查是否已经在下载列表中（通过标题匹配）
        # 这里我们搜索后检查，因为需要通过搜索来找到正确的视频ID
        
        # 搜索视频
        print_colored("正在搜索...", Colors.CYAN)
        results = search_youtube_video(video['title'], channel=channel, max_results=5)
        
        if not results:
            print_colored("❌ 未找到匹配的视频", Colors.RED)
            failed_count += 1
            print()
            continue
        
        # 检查前3个结果是否已经在下载列表中
        top3_results = results[:3]
        already_in_list = []
        new_results = []
        
        for result in top3_results:
            if result['id'] in existing_video_ids:
                already_in_list.append(result)
            else:
                new_results.append(result)
        
        if already_in_list:
            print_colored(f"⚠️  前3个结果中有 {len(already_in_list)} 个已在下载列表中，跳过", Colors.YELLOW)
            for result in already_in_list:
                print_colored(f"   - {result['title']} (ID: {result['id']})", Colors.CYAN)
            print()
        
        if not new_results:
            print_colored("✅ 前3个结果都已存在于下载列表中，跳过", Colors.GREEN)
            skipped_count += 1
            print()
            continue
        
        # 显示搜索结果
        print_colored(f"找到 {len(results)} 个结果，其中 {len(new_results)} 个新结果:", Colors.GREEN)
        for i, result in enumerate(new_results, 1):
            print_colored(f"  {i}. {result['title']}", Colors.CYAN)
            print_colored(f"     ID: {result['id']}", Colors.MAGENTA)
            print_colored(f"     链接: {result['url']}", Colors.BLUE)
            print()
        
        # 如果指定了下载列表文件，自动添加前3个新结果（需要验证）
        if add_to_download_list_file:
            # 验证并添加前3个新结果到下载列表
            print_colored("正在验证视频链接是否可访问...", Colors.CYAN)
            valid_video_ids = []
            invalid_count = 0
            
            for result in new_results[:3]:
                video_id = result['id']
                print_colored(f"  验证: {result['title'][:50]}...", Colors.CYAN, end='\r')
                
                is_valid, details = verify_video_link(video_id)
                if is_valid:
                    valid_video_ids.append(video_id)
                    print_colored(f"  ✅ 有效: {result['title'][:50]}", Colors.GREEN)
                else:
                    invalid_count += 1
                    print_colored(f"  ❌ 无效: {result['title'][:50]} (无法访问或下载)", Colors.RED)
            
            print()  # 换行
            
            # 只添加有效的视频ID
            if valid_video_ids:
                added = add_to_download_list(add_to_download_list_file, valid_video_ids)
                added_to_download_count += added
                
                # 更新existing_video_ids集合
                existing_video_ids.update(valid_video_ids)
                
                print_colored(f"✅ 已添加 {added} 个有效视频到下载列表", Colors.GREEN)
                if invalid_count > 0:
                    print_colored(f"⚠️  跳过了 {invalid_count} 个无效链接", Colors.YELLOW)
            else:
                print_colored(f"⚠️  前3个结果中没有可访问的视频，跳过", Colors.YELLOW)
            print()
        
        # 选择视频（用于更新源文件）- 自动选择第一个有效的
        selected = None
        for result in results:
            video_id = result['id']
            print_colored(f"验证链接: {result['title'][:50]}...", Colors.CYAN, end='\r')
            is_valid, details = verify_video_link(video_id)
            if is_valid:
                selected = result
                # 更新详细信息
                if details:
                    selected.update(details)
                print_colored(f"✅ 链接有效", Colors.GREEN)
                break
            else:
                print_colored(f"❌ 链接无效，尝试下一个...", Colors.YELLOW)
        
        if not selected:
            print_colored("❌ 所有搜索结果都无法访问，跳过此视频", Colors.RED)
            failed_count += 1
            print()
            continue
        
        # 更新视频信息，保存详细信息
        video['new_video_id'] = selected['id']
        video['new_url'] = selected['url']
        video['new_title'] = selected.get('title', video['title'])
        video['view_count'] = selected.get('view_count', 0)
        video['like_count'] = selected.get('like_count', 0)
        video['duration'] = selected.get('duration', 0)
        video['duration_str'] = selected.get('duration_str', '')
        video['upload_date'] = selected.get('upload_date', '')
        video['date_str'] = selected.get('date_str', '')
        updated_count += 1
        
        print_colored(f"✅ 已自动选择并更新源文件: {selected['title']}", Colors.GREEN)
        print_colored(f"   新链接: {selected['url']}", Colors.GREEN)
        if selected.get('view_count'):
            print_colored(f"   播放量: {selected['view_count']:,}", Colors.CYAN)
        if selected.get('like_count'):
            print_colored(f"   点赞量: {selected['like_count']:,}", Colors.CYAN)
        print()
    
    # 更新文件
    if updated_count > 0:
        print_colored("=" * 60, Colors.CYAN)
        print_colored("正在更新源文件...", Colors.BLUE)
        
        # 读取原文件
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 更新链接
        for video in need_update:
            if 'new_video_id' in video:
                old_url = video['url']
                # 构建新链接
                new_url = f"https://youtu.be/{video['new_video_id']}"
                
                # 替换链接
                # 匹配格式: [点击观看](旧链接)
                pattern = rf'(\[{re.escape("点击观看")}\]\()({re.escape(old_url)})(\))'
                replacement = rf'\1{new_url}\3'
                content = re.sub(pattern, replacement, content)
        
        # 写入文件
        output_path = output_file if output_file else input_file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print_colored(f"✅ 源文件已更新: {output_path}", Colors.GREEN)
    
    # 去重处理
    if add_to_download_list_file:
        print_colored("=" * 60, Colors.CYAN)
        print_colored("正在检查并移除重复链接...", Colors.BLUE)
        removed_count = remove_duplicates_from_download_list(add_to_download_list_file)
        print()
    
    # 生成CSV汇总表
    if csv_output:
        print_colored("=" * 60, Colors.CYAN)
        print_colored("正在生成CSV汇总表...", Colors.BLUE)
        # 使用更新后的文件路径
        source_file = output_file if output_file else input_file
        all_videos = read_video_list(source_file)
        # 更新已处理的视频信息（从need_update中获取详细信息）
        updated_dict = {v['rank']: v for v in need_update if 'new_video_id' in v}
        for v in all_videos:
            if v['rank'] in updated_dict:
                updated_v = updated_dict[v['rank']]
                v.update({
                    'new_video_id': updated_v.get('new_video_id'),
                    'new_url': updated_v.get('new_url'),
                    'new_title': updated_v.get('new_title'),
                    'view_count': updated_v.get('view_count', 0),
                    'like_count': updated_v.get('like_count', 0),
                    'duration': updated_v.get('duration', 0),
                    'duration_str': updated_v.get('duration_str', ''),
                    'date_str': updated_v.get('date_str', '')
                })
        generate_csv_summary(all_videos, csv_output)
        print()
    
    # 统计
    print_colored("=" * 60, Colors.CYAN)
    print_colored("更新完成！", Colors.GREEN)
    print_colored(f"成功更新源文件: {updated_count} 个", Colors.GREEN)
    if add_to_download_list_file:
        print_colored(f"添加到下载列表: {added_to_download_count} 个", Colors.GREEN)
        if removed_count > 0:
            print_colored(f"移除重复链接: {removed_count} 个", Colors.YELLOW)
    print_colored(f"已存在于下载列表: {skipped_count} 个", Colors.YELLOW)
    print_colored(f"失败/跳过: {failed_count} 个", Colors.YELLOW)
    if csv_output:
        print_colored(f"CSV汇总表: {csv_output}", Colors.CYAN)
    print_colored("=" * 60, Colors.CYAN)

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='通过视频标题在YouTube中搜索并获取真实链接')
    parser.add_argument('input_file', help='输入文件路径')
    parser.add_argument('-o', '--output', help='输出文件路径（默认覆盖原文件）')
    parser.add_argument('-c', '--channel', help='限制搜索范围到特定频道')
    parser.add_argument('-y', '--yes', action='store_true', help='自动选择第一个搜索结果，不交互')
    parser.add_argument('--add-to-download-list', nargs='?', const=True, default=None,
                        help='下载列表文件路径，自动添加前3个搜索结果（不提供路径时使用默认路径）')
    parser.add_argument('--csv-output', nargs='?', const=True, default=None,
                        help='生成CSV汇总表（不提供路径时使用默认路径）')
    
    args = parser.parse_args()
    
    # 检查文件是否存在
    if not Path(args.input_file).exists():
        print_colored(f"错误: 文件不存在 {args.input_file}", Colors.RED)
        sys.exit(1)
    
    # 确保输出目录存在
    output_dir = Path(OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 如果指定了下载列表但没有提供路径，使用默认路径
    download_list_file = args.add_to_download_list
    if args.add_to_download_list is True:  # 如果只是设置了flag但没有值
        # 使用默认路径：输出目录下的 todownload_links_DanKoe.txt
        download_list_file = str(output_dir / "todownload_links_DanKoe.txt")
        print_colored(f"使用默认下载列表路径: {download_list_file}", Colors.BLUE)
    
    # 如果指定了CSV输出但没有提供路径，使用默认路径
    csv_output_file = args.csv_output
    if args.csv_output is True:  # 如果只是设置了flag但没有值
        # 使用默认路径：输出目录下的 DanKoe_top30_summary.csv
        csv_output_file = str(output_dir / "DanKoe_top30_summary.csv")
        print_colored(f"使用默认CSV输出路径: {csv_output_file}", Colors.BLUE)
    
    # 执行更新
    update_video_links(
        args.input_file,
        args.output,
        channel=args.channel or CHANNEL_NAME,
        interactive=not args.yes,
        add_to_download_list_file=download_list_file,
        csv_output=csv_output_file
    )

if __name__ == '__main__':
    main()

