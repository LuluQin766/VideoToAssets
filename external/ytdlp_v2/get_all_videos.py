#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取YouTube频道的所有视频并保存完整信息到CSV
包含 generate_video_info.py 中的所有信息字段
"""

import re
import json
import sys
import csv
import time
import subprocess
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from functools import wraps
import yt_dlp
from config import (
    OUTPUT_PATH,
    get_output_path_for_channel, extract_channel_name_from_url,
    GET_INFO_MAX_RETRIES, GET_INFO_INITIAL_DELAY, GET_INFO_BACKOFF_FACTOR,
    DOWNLOAD_SUBTITLE_MAX_RETRIES, DOWNLOAD_SUBTITLE_INITIAL_DELAY, DOWNLOAD_SUBTITLE_BACKOFF_FACTOR,
    DEFAULT_MAX_WORKERS, MAX_WORKERS_LIMIT, RECOMMENDED_WORKERS_MIN, RECOMMENDED_WORKERS_MAX,
    GET_INFO_TIMEOUT, DOWNLOAD_SUBTITLE_TIMEOUT, GET_PLAYLIST_TIMEOUT,
    PROGRESS_SAVE_INTERVAL,
    REQUEST_DELAY, BATCH_PAUSE_INTERVAL, BATCH_PAUSE_DURATION,
    RATE_LIMIT_EXTRA_DELAY, RATE_LIMIT_MAX_RETRIES,
    USER_AGENT, CUSTOM_HEADERS,
    YT_DLP_DEFAULT_OPTS, YT_DLP_SUBTITLE_OPTS, YT_DLP_VIDEO_OPTS
)
from logger_utils import setup_logger, get_log_file_name
from safety_utils import is_rate_limit_error, get_ydl_opts
from convert_subtitles_to_text import convert_single_srt_to_text, copy_srt_to_txt_source

GENERATE_INFO_SCRIPT = Path(__file__).parent / "generate_video_info.py"

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

def retry_with_backoff(max_retries=None, initial_delay=None, backoff_factor=None, exceptions=(Exception,)):
    """重试装饰器，使用指数退避策略，特别处理速率限制错误
    
    Args:
        max_retries: 最大重试次数（默认使用配置值）
        initial_delay: 初始延迟时间（秒，默认使用配置值）
        backoff_factor: 退避因子（默认使用配置值）
        exceptions: 需要重试的异常类型
    """
    # 使用配置的默认值
    max_retries = max_retries or GET_INFO_MAX_RETRIES
    initial_delay = initial_delay or GET_INFO_INITIAL_DELAY
    backoff_factor = backoff_factor or GET_INFO_BACKOFF_FACTOR
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            # 尝试从 kwargs 获取 logger
            logger = kwargs.get('logger', None)
            
            for attempt in range(max_retries + 1):
                try:
                    # 在请求前添加延迟（除了第一次）
                    if attempt > 0 and REQUEST_DELAY > 0:
                        time.sleep(REQUEST_DELAY)
                    
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    # 检测速率限制错误
                    is_rate_limit = is_rate_limit_error(e)
                    
                    if attempt < max_retries:
                        # 如果是速率限制错误，使用更长的等待时间
                        if is_rate_limit:
                            wait_time = RATE_LIMIT_EXTRA_DELAY + (delay * (backoff_factor ** attempt))
                            if logger:
                                logger.warning(f"⚠️  检测到速率限制，等待 {wait_time:.1f} 秒后重试 ({attempt + 1}/{max_retries})")
                        else:
                            wait_time = delay * (backoff_factor ** attempt)
                            if logger:
                                logger.warning(f"{func.__name__} 失败，{wait_time:.1f}秒后重试 ({attempt + 1}/{max_retries}): {str(e)[:100]}")
                        
                        time.sleep(wait_time)
                    else:
                        # 最后一次失败，记录错误并抛出异常
                        if logger:
                            if is_rate_limit:
                                logger.error(f"⚠️  {func.__name__} 遇到速率限制，重试{max_retries}次后仍失败。建议：降低并发数或增加延迟")
                            else:
                                logger.error(f"{func.__name__} 重试{max_retries}次后仍失败: {str(e)}")
                        raise last_exception
            
            return None
        return wrapper
    return decorator

def extract_channel_base_url(user_input):
    """从用户输入中提取频道基础URL（不包含/videos等后缀）"""
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
            # 提取 @handle，可能后面有 /videos, /shorts 等
            handle = re.search(r'/@([^/?]+)', user_input)
            if handle:
                # 提取的handle可能包含路径，需要清理
                handle_name = handle.group(1).split('/')[0]
                base_url = f"https://www.youtube.com/@{handle_name}"
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
    
    # 移除可能存在的后缀（/videos, /shorts, /playlists, /posts等）
    for suffix in ['/videos', '/shorts', '/playlists', '/posts', '/streams', '/community']:
        if base_url.endswith(suffix):
            base_url = base_url[:-len(suffix)]
    
    return base_url

def extract_channel_url(user_input, content_type='videos'):
    """从用户输入中提取频道URL，并转换为指定类型的内容URL
    
    Args:
        user_input: 用户输入的频道URL或ID
        content_type: 内容类型 ('videos', 'shorts', 'playlists', 'posts')
    
    Returns:
        完整的频道内容URL
    """
    base_url = extract_channel_base_url(user_input)
    
    if not base_url:
        return None
    
    # 添加内容类型后缀
    if base_url.endswith('/'):
        return f"{base_url}{content_type}"
    else:
        return f"{base_url}/{content_type}"

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

def format_size(size_bytes):
    """格式化文件大小"""
    if size_bytes == 0:
        return ""
    try:
        size_bytes = float(size_bytes)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"
    except:
        return ""

def detect_url_type(url):
    """检测URL类型：频道或播放列表，以及频道内容类型
    
    Returns:
        ('channel' | 'playlist', normalized_url, content_type)
        content_type: 'videos', 'shorts', 'playlists', 'posts', None
    """
    url_lower = url.lower()
    
    # 检测播放列表
    if '/playlist' in url_lower or 'list=' in url_lower:
        # 提取播放列表ID
        if 'list=' in url_lower:
            match = re.search(r'list=([a-zA-Z0-9_-]+)', url)
            if match:
                playlist_id = match.group(1)
                normalized_url = f"https://www.youtube.com/playlist?list={playlist_id}"
                return ('playlist', normalized_url, None)
        return ('playlist', url, None)
    
    # 检测频道内容类型
    content_type = None
    if '/shorts' in url_lower:
        content_type = 'shorts'
    elif '/playlists' in url_lower:
        content_type = 'playlists'
    elif '/posts' in url_lower or '/community' in url_lower:
        content_type = 'posts'
    elif '/videos' in url_lower:
        content_type = 'videos'
    elif '/streams' in url_lower:
        content_type = 'streams'
    
    # 检测频道
    return ('channel', url, content_type)

def get_channel_videos(channel_url, content_type='videos', logger=None):
    """获取频道的所有视频ID和标题（使用extract_flat快速获取）
    
    Args:
        channel_url: 频道URL（可以是/videos, /shorts, /playlists, /posts等）
        content_type: 内容类型 ('videos', 'shorts', 'playlists', 'posts')
        logger: 日志记录器
    """
    content_type_names = {
        'videos': '视频',
        'shorts': '短视频',
        'playlists': '播放列表',
        'posts': '社区帖子',
        'streams': '直播'
    }
    type_name = content_type_names.get(content_type, '内容')
    
    print_colored(f"正在获取频道{type_name}列表...", Colors.CYAN)
    print_colored(f"频道URL: {channel_url}", Colors.BLUE)
    if logger:
        logger.info(f"开始获取频道{type_name}列表: {channel_url}")
    print()
    
    try:
        # 使用yt-dlp获取频道视频列表（不限制数量）
        ydl_opts = get_ydl_opts(extract_flat=True)
        
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
                })
        
        content_type_names = {
            'videos': '视频',
            'shorts': '短视频',
            'playlists': '播放列表',
            'posts': '社区帖子',
            'streams': '直播'
        }
        type_name = content_type_names.get(content_type, '内容')
        
        print_colored(f"✅ 获取到 {len(videos)} 个{type_name}", Colors.GREEN)
        if logger:
            logger.info(f"成功获取频道{type_name}列表: {len(videos)} 个")
        print()
        
        return videos
    
    except Exception as e:
        error_msg = f"获取视频列表出错: {str(e)}"
        print_colored(error_msg, Colors.RED)
        if logger:
            logger.error(error_msg, exc_info=True)
        return []

def get_playlist_videos(playlist_url, logger=None):
    """获取播放列表的所有视频ID和标题（使用extract_flat快速获取）"""
    print_colored(f"正在获取播放列表视频...", Colors.CYAN)
    print_colored(f"播放列表URL: {playlist_url}", Colors.BLUE)
    if logger:
        logger.info(f"开始获取播放列表视频: {playlist_url}")
    print()
    
    try:
        # 使用yt-dlp获取播放列表视频（不限制数量）
        ydl_opts = get_ydl_opts(extract_flat=True)
        
        videos = []
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(playlist_url, download=False)
            
            if not result or 'entries' not in result:
                print_colored(f"获取播放列表失败", Colors.RED)
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
                })
        
        print_colored(f"✅ 获取到 {len(videos)} 个视频", Colors.GREEN)
        if logger:
            logger.info(f"成功获取播放列表视频: {len(videos)} 个视频")
        print()
        
        return videos
    
    except Exception as e:
        error_msg = f"获取播放列表出错: {str(e)}"
        print_colored(error_msg, Colors.RED)
        if logger:
            logger.error(error_msg, exc_info=True)
        return []

@retry_with_backoff(
    max_retries=GET_INFO_MAX_RETRIES,
    initial_delay=GET_INFO_INITIAL_DELAY,
    backoff_factor=GET_INFO_BACKOFF_FACTOR,
    exceptions=(Exception,)
)
def get_full_video_info(video_url, logger=None):
    """获取视频的完整详细信息（包含 generate_video_info.py 中的所有字段）"""
    ydl_opts = get_ydl_opts()
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)
        if logger and info:
            logger.debug(f"成功获取视频信息: {video_url}")
        return info

@retry_with_backoff(
    max_retries=DOWNLOAD_SUBTITLE_MAX_RETRIES,
    initial_delay=DOWNLOAD_SUBTITLE_INITIAL_DELAY,
    backoff_factor=DOWNLOAD_SUBTITLE_BACKOFF_FACTOR,
    exceptions=(Exception,)
)
def download_subtitles(video_url, subtitle_path, video_id, video_title=None, logger=None):
    """下载视频的字幕文件"""
    subtitle_path = Path(subtitle_path)
    subtitle_path.mkdir(parents=True, exist_ok=True)
    
    # 清理标题用于文件名
    if video_title:
        clean_title = re.sub(r'[^\w\s-]', '', video_title)[:50]  # 限制长度并清理特殊字符
        clean_title = re.sub(r'[-\s]+', '-', clean_title)  # 替换空格为连字符
        filename_template = f'{clean_title}_{video_id}.%(ext)s'
    else:
        filename_template = f'%(id)s.%(ext)s'
    
    ydl_opts = get_ydl_opts(YT_DLP_SUBTITLE_OPTS)
    ydl_opts['outtmpl'] = str(subtitle_path / filename_template)
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])
        if logger:
            logger.debug(f"成功下载字幕: {video_id}")
        return True

def load_progress(progress_file):
    """加载进度文件，返回已处理的视频ID集合"""
    processed_ids = set()
    if not Path(progress_file).exists():
        return processed_ids
    
    try:
        with open(progress_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            processed_ids = set(data.get('processed_video_ids', []))
            print_colored(f"📂 加载进度文件: 已处理 {len(processed_ids)} 个视频", Colors.CYAN)
    except Exception as e:
        print_colored(f"⚠️  加载进度文件失败: {str(e)}", Colors.YELLOW)
    
    return processed_ids

def save_progress(progress_file, processed_ids, last_update=None):
    """保存进度文件"""
    try:
        progress_data = {
            'processed_video_ids': list(processed_ids),
            'last_update': last_update or datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_processed': len(processed_ids)
        }
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print_colored(f"⚠️  保存进度文件失败: {str(e)}", Colors.YELLOW)

def load_existing_csv(csv_file):
    """加载现有CSV文件，返回已存在的视频ID集合"""
    existing_ids = set()
    if not Path(csv_file).exists():
        return existing_ids
    
    try:
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                video_id = row.get('视频ID', '').strip()
                if video_id:
                    existing_ids.add(video_id)
        if existing_ids:
            print_colored(f"📊 检测到现有CSV文件: 已包含 {len(existing_ids)} 个视频", Colors.CYAN)
    except Exception as e:
        print_colored(f"⚠️  读取现有CSV文件失败: {str(e)}", Colors.YELLOW)
    
    return existing_ids

def get_video_title(url, logger=None):
    """获取视频标题"""
    try:
        ydl_opts = get_ydl_opts()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', '') if info else None
            if logger and title:
                logger.debug(f"获取视频标题: {title[:50]}")
            return title
    except Exception as e:
        if logger:
            logger.warning(f"获取视频标题失败: {url} - {str(e)}")
        return None

def clean_title_for_filename(title):
    """清理标题，用于文件名（只保留字母、数字、中文、下划线和连字符）"""
    if not title:
        return ""
    # 使用正则表达式清理特殊字符
    clean = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fa5_-]', '', title)
    return clean

def get_folder_name(video_title):
    """获取文件夹名（视频标题前10个字符）"""
    if not video_title:
        return f"video_{int(datetime.now().timestamp())}"
    
    clean_title = clean_title_for_filename(video_title)
    if not clean_title:
        return f"video_{int(datetime.now().timestamp())}"
    
    # 截取前10个字符
    return clean_title[:10] if len(clean_title) > 10 else clean_title

def get_info_filename(video_title):
    """获取信息文件名（视频标题前20个字符 + 时间戳）"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    if not video_title:
        return f"video_info_{timestamp}.md"
    
    clean_title = clean_title_for_filename(video_title)
    if not clean_title:
        return f"video_info_{timestamp}.md"
    
    # 截取前20个字符，添加时间戳
    filename = clean_title[:20] if len(clean_title) > 20 else clean_title
    return f"{filename}_{timestamp}.md"

def download_video(url, save_path, folder_name, logger=None):
    """下载视频、音频、字幕、封面图片"""
    try:
        output_path = Path(save_path) / folder_name
        output_path.mkdir(parents=True, exist_ok=True)
        
        ydl_opts = get_ydl_opts(YT_DLP_VIDEO_OPTS)
        ydl_opts['outtmpl'] = str(output_path / '%(title)s.%(ext)s')
        
        if logger:
            logger.info(f"开始下载视频: {url} -> {output_path}")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        if logger:
            logger.info(f"视频下载完成: {url}")
        return True
    except Exception as e:
        error_msg = str(e)
        if logger:
            logger.error(f"视频下载失败: {url} - {error_msg}", exc_info=True)
        return False

def generate_video_info(url, info_file_path, logger=None):
    """生成视频信息文件"""
    try:
        cmd = [
            sys.executable,
            str(GENERATE_INFO_SCRIPT),
            url,
            str(info_file_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if logger:
            if result.returncode == 0:
                logger.debug(f"成功生成视频信息: {info_file_path}")
            else:
                logger.warning(f"生成视频信息失败: {info_file_path}")
        return result.returncode == 0
    except Exception as e:
        if logger:
            logger.error(f"生成视频信息异常: {info_file_path} - {str(e)}")
        return False

def check_files_exist(folder_path):
    """检查文件夹中的视频、音频、字幕、封面图片文件是否存在"""
    folder = Path(folder_path)
    if not folder.exists():
        return False, False, False, False
    
    # 检查视频文件（常见格式，通常包含音频）
    video_exts = ['.mp4', '.mkv', '.webm', '.flv', '.avi', '.mov']
    has_video = any(list(folder.glob(f'*{ext}')) for ext in video_exts)
    
    # 检查音频文件（如果单独存在，通常视频文件已包含音频）
    audio_exts = ['.mp3', '.m4a', '.opus', '.ogg', '.wav']
    has_audio = any(list(folder.glob(f'*{ext}')) for ext in audio_exts)
    # 如果视频文件存在，通常也包含音频
    if has_video and not has_audio:
        has_audio = True  # 视频文件通常包含音频轨道
    
    # 检查字幕文件
    subtitle_exts = ['.srt', '.vtt', '.ass', '.ssa']
    has_subtitle = any(list(folder.glob(f'*{ext}')) for ext in subtitle_exts)
    
    # 检查封面图片文件（常见格式）
    thumbnail_exts = ['.jpg', '.jpeg', '.png', '.webp']
    has_thumbnail = any(list(folder.glob(f'*{ext}')) for ext in thumbnail_exts)
    
    return has_video, has_audio, has_subtitle, has_thumbnail

def extract_video_data(info):
    """从info中提取所有字段数据"""
    if not info:
        return None
    
    # 基本信息
    title = info.get('title', '')
    video_id = info.get('id', '')
    webpage_url = info.get('webpage_url', '')
    channel = info.get('channel', '')
    channel_id = info.get('channel_id', '')
    channel_url = info.get('channel_url', '')
    channel_follower_count = info.get('channel_follower_count', 0) or 0
    uploader = info.get('uploader', '')
    uploader_id = info.get('uploader_id', '')
    uploader_url = info.get('uploader_url', '')
    
    # 日期信息
    upload_date = info.get('upload_date', '') or ''
    release_date = info.get('release_date', '') or ''
    upload_date_str = format_date(upload_date)
    release_date_str = format_date(release_date) if release_date else ''
    
    # 时长和格式
    duration = info.get('duration', 0) or 0
    duration_str = format_duration(duration)
    
    # 统计数据
    view_count = info.get('view_count', 0) or 0
    like_count = info.get('like_count', 0) or 0
    comment_count = info.get('comment_count', 0) or 0
    average_rating = info.get('average_rating', 0) or 0
    
    # 计算点赞率
    like_rate = (like_count / view_count * 100) if view_count > 0 else 0
    
    # 描述
    description = info.get('description', '')
    
    # 标签和分类
    tags = info.get('tags', [])
    tags_str = '; '.join(tags) if tags else ''
    categories = info.get('categories', [])
    categories_str = '; '.join(categories) if categories else ''
    
    # 缩略图
    thumbnail = info.get('thumbnail', '')
    
    # 语言和限制
    language = info.get('language', '')
    age_limit = info.get('age_limit', 0)
    availability = info.get('availability', '')
    
    # 视频技术信息
    format_note = info.get('format_note', '')
    width = info.get('width', 0) or 0
    height = info.get('height', 0) or 0
    resolution = f"{width}x{height}" if width and height else ''
    fps = info.get('fps', 0) or 0
    vcodec = info.get('vcodec', '')
    acodec = info.get('acodec', '')
    filesize = info.get('filesize', 0) or 0
    filesize_approx = info.get('filesize_approx', 0) or 0
    file_size = filesize if filesize > 0 else filesize_approx
    file_size_str = format_size(file_size)
    
    # 字幕信息
    subtitles = info.get('subtitles', {})
    automatic_captions = info.get('automatic_captions', {})
    subtitle_langs = list(subtitles.keys()) if subtitles else []
    auto_caption_langs = list(automatic_captions.keys()) if automatic_captions else []
    subtitle_langs_str = '; '.join(subtitle_langs) if subtitle_langs else ''
    auto_caption_langs_str = '; '.join(auto_caption_langs) if auto_caption_langs else ''
    
    # 章节信息
    chapters = info.get('chapters', [])
    chapter_count = len(chapters) if chapters else 0
    
    # 其他信息
    ext = info.get('ext', '')
    format_id = info.get('format', '')
    
    return {
        'video_id': video_id,
        'title': title,
        'url': webpage_url,
        'channel': channel,
        'channel_id': channel_id,
        'channel_url': channel_url,
        'channel_follower_count': channel_follower_count,
        'uploader': uploader,
        'uploader_id': uploader_id,
        'uploader_url': uploader_url,
        'upload_date': upload_date_str,
        'release_date': release_date_str,
        'duration': duration,
        'duration_str': duration_str,
        'view_count': view_count,
        'like_count': like_count,
        'comment_count': comment_count,
        'like_rate': like_rate,
        'average_rating': average_rating,
        'description': description,
        'tags': tags_str,
        'categories': categories_str,
        'thumbnail': thumbnail,
        'language': language,
        'age_limit': age_limit,
        'availability': availability,
        'resolution': resolution,
        'width': width,
        'height': height,
        'format_note': format_note,
        'fps': fps,
        'vcodec': vcodec,
        'acodec': acodec,
        'file_size': file_size,
        'file_size_str': file_size_str,
        'subtitle_langs': subtitle_langs_str,
        'auto_caption_langs': auto_caption_langs_str,
        'chapter_count': chapter_count,
        'ext': ext,
        'format_id': format_id,
    }

def process_single_video(video, subtitles_path, videos_path, subtitles_txt_source_path, subtitles_txt_essay_path, subtitles_md_essay_path, download_video_file=False, logger=None):
    """处理单个视频（获取信息、下载视频、字幕、封面，生成信息文档）
    
    Args:
        video: 视频信息字典，包含 id, title, url
        subtitles_path: 字幕保存路径（原始 .srt 文件）
        videos_path: 视频保存路径（用于下载视频文件）
        subtitles_txt_source_path: 字幕 TXT 源文件路径（直接改后缀）
        subtitles_txt_essay_path: 字幕 TXT 转换文件路径（去除时间戳）
        subtitles_md_essay_path: 字幕 MD 转换文件路径（去除时间戳）
        download_video_file: 是否下载视频文件（默认False，只下载字幕）
        logger: 日志记录器（可选）
    
    Returns:
        (video_data, video_id, video_title, has_subtitle, success, error_msg)
    """
    video_id = video['id']
    video_title = video['title']
    video_url = video['url']
    
    try:
        # 获取完整信息（带重试）
        info = get_full_video_info(video_url, logger=logger)
        
        if not info:
            error_msg = "无法获取视频信息（重试后仍失败）"
            if logger:
                logger.warning(f"视频 {video_id} 获取信息失败")
            return (None, video_id, video_title, False, False, error_msg)
        
        video_data = extract_video_data(info)
        if not video_data:
            error_msg = "无法提取视频数据"
            if logger:
                logger.warning(f"视频 {video_id} 提取数据失败")
            return (None, video_id, video_title, False, False, error_msg)
        
        # 如果启用视频下载，下载视频、字幕、封面
        if download_video_file and videos_path:
            folder_name = get_folder_name(video_title)
            video_folder = videos_path / folder_name
            video_folder.mkdir(parents=True, exist_ok=True)
            
            try:
                # 下载视频、字幕、封面
                download_video(video_url, videos_path, folder_name, logger=logger)
                
                # 生成视频信息文档
                info_filename = get_info_filename(video_title)
                info_file_path = video_folder / info_filename
                generate_video_info(video_url, info_file_path, logger=logger)
                
                # 转换字幕文件
                srt_files = list(video_folder.glob('*.srt'))
                for srt_file in srt_files:
                    try:
                        # 1. 直接复制并改后缀为 .txt（不做处理）
                        copy_srt_to_txt_source(srt_file, subtitles_txt_source_path)
                        
                        # 2. 转换为 TXT 和 MD（去除时间戳等处理）
                        convert_single_srt_to_text(srt_file, subtitles_txt_essay_path, subtitles_md_essay_path)
                        
                        if logger:
                            logger.debug(f"成功转换字幕: {srt_file.name} -> txt_source, txt_essay, md_essay")
                    except Exception as e:
                        if logger:
                            logger.warning(f"字幕转换失败: {srt_file.name} - {str(e)}")
            except Exception as e:
                # 视频下载失败不影响主流程（仍保存信息到CSV）
                if logger:
                    logger.warning(f"视频 {video_id} 下载失败: {str(e)}")
        else:
            # 只下载字幕（原有功能）
            try:
                download_subtitles(video_url, subtitles_path, video_id, video_title, logger=logger)
                
                # 转换下载的字幕文件
                subtitle_files = list(subtitles_path.glob(f'*{video_id}*.srt'))
                for srt_file in subtitle_files:
                    try:
                        # 1. 直接复制并改后缀为 .txt（不做处理）
                        copy_srt_to_txt_source(srt_file, subtitles_txt_source_path)
                        
                        # 2. 转换为 TXT 和 MD（去除时间戳等处理）
                        convert_single_srt_to_text(srt_file, subtitles_txt_essay_path, subtitles_md_essay_path)
                        
                        if logger:
                            logger.debug(f"成功转换字幕: {srt_file.name} -> txt_source, txt_essay, md_essay")
                    except Exception as e:
                        if logger:
                            logger.warning(f"字幕转换失败: {srt_file.name} - {str(e)}")
            except Exception as e:
                # 字幕下载失败不影响主流程
                if logger:
                    logger.debug(f"视频 {video_id} 字幕下载失败: {str(e)}")
        
        # 检查字幕文件是否存在
        if download_video_file and videos_path:
            folder_name = get_folder_name(video_title)
            video_folder = videos_path / folder_name
            subtitle_files = list(video_folder.glob('*.srt'))
        else:
            subtitle_files = list(subtitles_path.glob(f'*{video_id}*.srt'))
        has_subtitle = len(subtitle_files) > 0
        
        if logger:
            logger.info(f"成功处理视频 {video_id}: {video_title[:50]}")
        
        return (video_data, video_id, video_title, has_subtitle, True, None)
    
    except Exception as e:
        error_msg = f"处理异常: {str(e)}"
        if logger:
            logger.error(f"视频 {video_id} 处理异常: {str(e)}", exc_info=True)
        return (None, video_id, video_title, False, False, error_msg)

def get_all_videos(input_url, output_csv=None, resume=False, max_workers=None, content_types=None, download_video_file=False):
    """获取频道或播放列表的所有视频并保存完整信息到CSV
    
    Args:
        input_url: 频道URL或播放列表URL
        output_csv: 输出CSV文件路径
        resume: 是否从断点继续
        max_workers: 最大并发线程数（默认使用配置值）
        content_types: 要获取的内容类型列表，如 ['videos', 'shorts', 'playlists', 'posts']
                      如果为None，则根据URL自动检测或默认获取videos
        download_video_file: 是否下载视频文件、封面和信息文档（默认False，只下载字幕）
    """
    # 设置日志
    log_file = get_log_file_name('get_all_videos')
    logger = setup_logger('get_all_videos', log_file)
    logger.info("=" * 60)
    logger.info("YouTube 视频获取工具（支持频道和播放列表）")
    logger.info("=" * 60)
    
    print_colored("=" * 60, Colors.CYAN)
    print_colored("YouTube 视频获取工具（支持频道和播放列表）", Colors.GREEN)
    print_colored("=" * 60, Colors.CYAN)
    print()
    
    # 使用配置的默认并发数
    if max_workers is None:
        max_workers = DEFAULT_MAX_WORKERS
    
    # 检测URL类型
    url_type, normalized_url, detected_content_type = detect_url_type(input_url)
    logger.info(f"URL类型: {url_type}, URL: {normalized_url}, 内容类型: {detected_content_type}")
    
    if url_type == 'playlist':
        print_colored("📋 检测到播放列表URL", Colors.CYAN)
        videos = get_playlist_videos(normalized_url, logger=logger)
    else:
        print_colored("📺 检测到频道URL", Colors.CYAN)
        
        # 确定要获取的内容类型
        if content_types is None:
            # 如果URL中指定了内容类型，使用该类型；否则默认获取videos
            if detected_content_type:
                content_types = [detected_content_type]
            else:
                content_types = ['videos']
        
        # 获取频道基础URL
        base_url = extract_channel_base_url(input_url)
        
        # 获取所有指定类型的内容
        all_videos = []
        content_type_names = {
            'videos': '视频',
            'shorts': '短视频',
            'playlists': '播放列表',
            'posts': '社区帖子',
            'streams': '直播'
        }
        
        for content_type in content_types:
            if content_type not in ['videos', 'shorts', 'playlists', 'posts', 'streams']:
                print_colored(f"⚠️  不支持的内容类型: {content_type}，跳过", Colors.YELLOW)
                continue
            
            type_url = extract_channel_url(base_url, content_type)
            type_name = content_type_names.get(content_type, content_type)
            print_colored(f"📥 正在获取{type_name}...", Colors.CYAN)
            
            type_videos = get_channel_videos(type_url, content_type=content_type, logger=logger)
            if type_videos:
                all_videos.extend(type_videos)
                print_colored(f"✅ {type_name}获取完成: {len(type_videos)} 个", Colors.GREEN)
            else:
                print_colored(f"⚠️  {type_name}获取失败或为空", Colors.YELLOW)
            print()
        
        # 去重（基于视频ID）
        seen_ids = set()
        videos = []
        for video in all_videos:
            if video['id'] not in seen_ids:
                seen_ids.add(video['id'])
                videos.append(video)
        
        if len(all_videos) > len(videos):
            print_colored(f"🔄 去重: {len(all_videos)} -> {len(videos)} 个视频", Colors.CYAN)
            print()
    
    if not videos:
        print_colored("❌ 未能获取到任何视频", Colors.RED)
        return False
    
    # 提取名称（频道名或播放列表名）
    if url_type == 'playlist':
        # 从播放列表URL提取ID
        match = re.search(r'list=([a-zA-Z0-9_-]+)', normalized_url)
        if match:
            channel_name = f"playlist_{match.group(1)}"
        else:
            channel_name = 'unknown_playlist'
        # 播放列表使用默认输出路径
        user_output_path = OUTPUT_PATH / channel_name
        user_output_path.mkdir(parents=True, exist_ok=True)
    else:
        # 从频道URL提取频道名称
        channel_name = extract_channel_name_from_url(input_url)
        if not channel_name:
            # 如果无法从URL提取，尝试从第一个视频获取
            if videos:
                try:
                    first_info = get_full_video_info(videos[0]['url'])
                    if first_info:
                        channel_name = first_info.get('uploader', 'unknown_channel')
                        # 清理文件名中的特殊字符
                        channel_name = re.sub(r'[^\w\-_\.]', '_', channel_name)
                except:
                    channel_name = 'unknown_channel'
            else:
                channel_name = 'unknown_channel'
        
        # 使用新的配置函数获取输出路径（自动根据频道名称创建目录）
        user_output_path = get_output_path_for_channel(channel_name=channel_name, url=input_url)
    
    # 创建字幕文件夹
    subtitles_path = user_output_path / 'subtitles'
    subtitles_path.mkdir(parents=True, exist_ok=True)
    
    # 创建字幕转换文件夹
    subtitles_txt_source_path = user_output_path / 'subtitles_txt_source'  # 直接改后缀的 .txt 文件
    subtitles_txt_essay_path = user_output_path / 'subtitles_txt_essay'    # 转换后的 .txt 文件
    subtitles_md_essay_path = user_output_path / 'subtitles_md_essay'      # 转换后的 .md 文件
    subtitles_txt_source_path.mkdir(parents=True, exist_ok=True)
    subtitles_txt_essay_path.mkdir(parents=True, exist_ok=True)
    subtitles_md_essay_path.mkdir(parents=True, exist_ok=True)
    
    # 创建视频文件夹（如果启用视频下载）
    videos_path = user_output_path / 'videos' if download_video_file else None
    if videos_path:
        videos_path.mkdir(parents=True, exist_ok=True)
    
    # 生成CSV文件名
    if not output_csv:
        output_csv = str(user_output_path / f"{channel_name}_all_videos.csv")
    
    # 进度文件路径
    progress_file = user_output_path / f"{channel_name}_progress.json"
    
    # 加载已处理的视频ID
    processed_ids = set()
    
    # 总是从现有CSV文件加载（如果存在）
    csv_ids = load_existing_csv(output_csv)
    if csv_ids:
        processed_ids.update(csv_ids)
    
    if resume:
        # 从进度文件加载（补充CSV中可能没有的）
        progress_ids = load_progress(progress_file)
        processed_ids.update(progress_ids)
        
        if processed_ids:
            print_colored(f"🔄 断点续传模式: 将跳过 {len(processed_ids)} 个已处理的视频", Colors.YELLOW)
            print()
    elif processed_ids:
        # 即使没有使用 --resume，如果检测到已有CSV，也提示用户
        print_colored(f"⚠️  检测到现有CSV文件，将跳过 {len(processed_ids)} 个已存在的视频", Colors.YELLOW)
        print_colored(f"💡 提示: 使用 --resume 参数可以明确启用断点续传模式", Colors.CYAN)
        print()
    
    # 过滤掉已处理的视频
    total_videos = len(videos)
    videos_to_process = [v for v in videos if v['id'] not in processed_ids]
    skipped_count = total_videos - len(videos_to_process)
    
    if skipped_count > 0:
        print_colored(f"⏭️  跳过 {skipped_count} 个已处理的视频", Colors.CYAN)
        print_colored(f"📋 待处理: {len(videos_to_process)} 个视频", Colors.BLUE)
        print()
    
    if not videos_to_process:
        print_colored("✅ 所有视频已处理完成！", Colors.GREEN)
        return True
    
    print_colored(f"正在获取 {len(videos_to_process)} 个视频的完整信息...", Colors.BLUE)
    print_colored(f"输出目录: {user_output_path}", Colors.CYAN)
    print_colored(f"字幕保存目录: {subtitles_path}", Colors.CYAN)
    print_colored(f"字幕 TXT 源文件目录: {subtitles_txt_source_path}", Colors.CYAN)
    print_colored(f"字幕 TXT 转换文件目录: {subtitles_txt_essay_path}", Colors.CYAN)
    print_colored(f"字幕 MD 转换文件目录: {subtitles_md_essay_path}", Colors.CYAN)
    if download_video_file and videos_path:
        print_colored(f"视频保存目录: {videos_path}", Colors.CYAN)
    print_colored(f"进度文件: {progress_file}", Colors.CYAN)
    print_colored(f"并发线程数: {max_workers}", Colors.CYAN)
    if download_video_file:
        print_colored("📥 视频下载模式: 将下载视频、字幕、封面和信息文档", Colors.GREEN)
    else:
        print_colored("📝 信息收集模式: 只下载字幕，不下载视频文件", Colors.YELLOW)
    print_colored("这可能需要较长时间，请耐心等待...", Colors.YELLOW)
    print()
    
    # CSV表头
    headers = [
        '视频ID',
        '视频标题',
        '视频链接',
        '频道名称',
        '频道ID',
        '频道链接',
        '频道订阅数',
        '上传者',
        '上传者ID',
        '上传者链接',
        '上传日期',
        '发布日期',
        '视频时长（秒）',
        '视频时长',
        '播放量',
        '点赞量',
        '评论数',
        '点赞率(%)',
        '平均评分',
        '视频描述',
        '标签',
        '分类',
        '缩略图URL',
        '语言',
        '年龄限制',
        '可用性',
        '分辨率',
        '宽度',
        '高度',
        '格式',
        '帧率',
        '视频编码',
        '音频编码',
        '文件大小（字节）',
        '文件大小',
        '字幕语言',
        '自动字幕语言',
        '章节数量',
        '扩展名',
        '格式ID'
    ]
    
    # 如果是从断点继续，先加载现有CSV数据
    existing_data = []
    if resume and Path(output_csv).exists():
        try:
            with open(output_csv, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                existing_data = list(reader)
            print_colored(f"📂 已加载 {len(existing_data)} 条现有数据", Colors.CYAN)
        except Exception as e:
            print_colored(f"⚠️  加载现有数据失败: {str(e)}", Colors.YELLOW)
    
    # 多线程处理视频
    all_video_data = []
    success_count = 0
    failed_count = 0
    subtitle_count = 0
    completed_count = 0
    
    # 创建线程锁用于保护共享资源
    lock = Lock()
    
    logger.info(f"开始处理 {len(videos_to_process)} 个视频，并发数: {max_workers}")
    
    # 使用线程池并发处理
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_video = {
            executor.submit(process_single_video, video, subtitles_path, videos_path, subtitles_txt_source_path, subtitles_txt_essay_path, subtitles_md_essay_path, download_video_file, logger): video 
            for video in videos_to_process
        }
        
        # 处理完成的任务
        for future in as_completed(future_to_video):
            video = future_to_video[future]
            completed_count += 1
            current_index = skipped_count + completed_count
            
            try:
                video_data, video_id, video_title, has_subtitle, success, error_msg = future.result()
                
                if success and video_data:
                    with lock:
                        all_video_data.append(video_data)
                        success_count += 1
                        processed_ids.add(video_id)  # 添加到已处理集合
                        
                # 每处理指定数量视频保存一次进度
                if success_count % PROGRESS_SAVE_INTERVAL == 0:
                    save_progress(progress_file, processed_ids)
                    if logger:
                        logger.info(f"已保存进度: {success_count} 个视频处理完成")
                
                # 批量处理间隔：每处理 N 个视频后暂停
                if success_count > 0 and success_count % BATCH_PAUSE_INTERVAL == 0:
                    if BATCH_PAUSE_DURATION > 0:
                        print_colored(f"\n⏸️  已处理 {success_count} 个视频，暂停 {BATCH_PAUSE_DURATION} 秒以避免速率限制...", Colors.YELLOW)
                        if logger:
                            logger.info(f"批量处理暂停: 已处理 {success_count} 个视频，暂停 {BATCH_PAUSE_DURATION} 秒")
                        time.sleep(BATCH_PAUSE_DURATION)
                
                if success and video_data:
                    if has_subtitle:
                        with lock:
                            subtitle_count += 1
                        print_colored(f"[{current_index}/{total_videos}] ✅ {video_title[:60]} (字幕已下载)", Colors.GREEN)
                    else:
                        print_colored(f"[{current_index}/{total_videos}] ✅ {video_title[:60]} (无字幕)", Colors.YELLOW)
                else:
                    with lock:
                        failed_count += 1
                    error_info = f" - {error_msg}" if error_msg else ""
                    print_colored(f"[{current_index}/{total_videos}] ❌ 处理失败: {video_title[:60]}{error_info}", Colors.RED)
                
                # 显示进度
                progress_percent = (completed_count / len(videos_to_process)) * 100
                print_colored(f"进度: {completed_count}/{len(videos_to_process)} ({progress_percent:.1f}%) | 成功: {success_count} | 失败: {failed_count}", Colors.CYAN, end='\r')
                
            except Exception as e:
                with lock:
                    failed_count += 1
                video_title = video.get('title', 'Unknown')[:60]
                print_colored(f"[{current_index}/{total_videos}] ❌ 异常: {video_title} - {str(e)}", Colors.RED)
    
    print()  # 换行
    
    # 最终保存进度
    save_progress(progress_file, processed_ids)
    
    print()  # 换行
    print_colored(f"✅ 成功获取 {success_count} 个视频的完整信息", Colors.GREEN)
    print_colored(f"📝 成功下载 {subtitle_count} 个字幕文件", Colors.CYAN)
    if download_video_file:
        print_colored(f"📥 视频下载模式: 已下载视频、封面和信息文档", Colors.GREEN)
    if failed_count > 0:
        print_colored(f"⚠️  失败 {failed_count} 个视频", Colors.YELLOW)
    print()
    
    # 保存到CSV
    print_colored(f"正在保存到CSV文件: {output_csv}", Colors.BLUE)
    
    try:
        # 判断是追加还是新建
        file_exists = Path(output_csv).exists()
        # 如果文件存在或使用resume模式，使用追加模式；否则新建
        mode = 'a' if (file_exists or resume) else 'w'
        
        with open(output_csv, mode, newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            
            # 如果是新建文件，写入表头
            if not file_exists:
                writer.writeheader()
            
            # 写入新数据
            for video_data in all_video_data:
                writer.writerow({
                    '视频ID': video_data.get('video_id', ''),
                    '视频标题': video_data.get('title', ''),
                    '视频链接': video_data.get('url', ''),
                    '频道名称': video_data.get('channel', ''),
                    '频道ID': video_data.get('channel_id', ''),
                    '频道链接': video_data.get('channel_url', ''),
                    '频道订阅数': video_data.get('channel_follower_count', 0),
                    '上传者': video_data.get('uploader', ''),
                    '上传者ID': video_data.get('uploader_id', ''),
                    '上传者链接': video_data.get('uploader_url', ''),
                    '上传日期': video_data.get('upload_date', ''),
                    '发布日期': video_data.get('release_date', ''),
                    '视频时长（秒）': video_data.get('duration', 0),
                    '视频时长': video_data.get('duration_str', ''),
                    '播放量': video_data.get('view_count', 0),
                    '点赞量': video_data.get('like_count', 0),
                    '评论数': video_data.get('comment_count', 0),
                    '点赞率(%)': f"{video_data.get('like_rate', 0):.2f}",
                    '平均评分': video_data.get('average_rating', 0),
                    '视频描述': video_data.get('description', ''),
                    '标签': video_data.get('tags', ''),
                    '分类': video_data.get('categories', ''),
                    '缩略图URL': video_data.get('thumbnail', ''),
                    '语言': video_data.get('language', ''),
                    '年龄限制': video_data.get('age_limit', 0),
                    '可用性': video_data.get('availability', ''),
                    '分辨率': video_data.get('resolution', ''),
                    '宽度': video_data.get('width', 0),
                    '高度': video_data.get('height', 0),
                    '格式': video_data.get('format_note', ''),
                    '帧率': video_data.get('fps', 0),
                    '视频编码': video_data.get('vcodec', ''),
                    '音频编码': video_data.get('acodec', ''),
                    '文件大小（字节）': video_data.get('file_size', 0),
                    '文件大小': video_data.get('file_size_str', ''),
                    '字幕语言': video_data.get('subtitle_langs', ''),
                    '自动字幕语言': video_data.get('auto_caption_langs', ''),
                    '章节数量': video_data.get('chapter_count', 0),
                    '扩展名': video_data.get('ext', ''),
                    '格式ID': video_data.get('format_id', ''),
                })
        
        # 统计总数据（包括现有的）
        total_in_csv = len(existing_data) + len(all_video_data) if resume else len(all_video_data)
        
        print_colored(f"✅ CSV文件已更新: {output_csv}", Colors.GREEN)
        print_colored(f"📁 字幕文件夹: {subtitles_path}", Colors.CYAN)
        print_colored(f"📁 字幕 TXT 源文件: {subtitles_txt_source_path}", Colors.CYAN)
        print_colored(f"📁 字幕 TXT 转换文件: {subtitles_txt_essay_path}", Colors.CYAN)
        print_colored(f"📁 字幕 MD 转换文件: {subtitles_md_essay_path}", Colors.CYAN)
        if download_video_file and videos_path:
            print_colored(f"📁 视频文件夹: {videos_path}", Colors.CYAN)
        print_colored(f"📊 CSV中总视频数: {total_in_csv}", Colors.CYAN)
        print_colored(f"📝 本次新增: {len(all_video_data)} 个视频", Colors.CYAN)
        print()
        
        # 显示统计信息
        if all_video_data:
            total_views = sum(v.get('view_count', 0) for v in all_video_data)
            total_likes = sum(v.get('like_count', 0) for v in all_video_data)
            avg_views = total_views / len(all_video_data) if all_video_data else 0
            
            print_colored("本次处理统计:", Colors.YELLOW)
            print_colored(f"  新增视频数: {len(all_video_data)}", Colors.CYAN)
            print_colored(f"  新增字幕文件数: {subtitle_count}", Colors.CYAN)
            print_colored(f"  新增视频总播放量: {total_views:,}", Colors.BLUE)
            print_colored(f"  新增视频总点赞量: {total_likes:,}", Colors.MAGENTA)
            print_colored(f"  平均播放量: {avg_views:,.0f}", Colors.CYAN)
            print()
        
        # 显示总体进度
        if processed_ids:
            completion_rate = len(processed_ids) / total_videos * 100
            print_colored(f"📈 总体进度: {len(processed_ids)}/{total_videos} ({completion_rate:.1f}%)", Colors.MAGENTA)
            print()
        
        return True
    
    except Exception as e:
        print_colored(f"生成CSV时出错: {str(e)}", Colors.RED)
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='获取YouTube频道或播放列表的所有视频并保存完整信息到CSV',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
内容类型说明：
  默认行为：如果URL中没有指定类型，默认只获取 videos（普通视频）
  
  示例：
    # 只获取 videos（默认）
    python3 get_all_videos.py https://www.youtube.com/@channelname
    
    # 获取所有类型（videos + shorts + playlists + posts）
    python3 get_all_videos.py --all-types https://www.youtube.com/@channelname
    
    # 只获取 videos 和 shorts
    python3 get_all_videos.py --content-types videos shorts https://www.youtube.com/@channelname
    
    # URL中指定类型会自动检测
    python3 get_all_videos.py https://www.youtube.com/@channelname/shorts  # 只获取 shorts
        '''
    )
    parser.add_argument('input_url', help='YouTube频道URL、@用户名或播放列表URL')
    parser.add_argument('-o', '--output', help='输出CSV文件路径（默认自动生成）')
    parser.add_argument('-r', '--resume', action='store_true', 
                        help='从断点继续（跳过已处理的视频）')
    parser.add_argument('-w', '--workers', type=int, default=None,
                        help=f'并发线程数（默认{DEFAULT_MAX_WORKERS}，建议{RECOMMENDED_WORKERS_MIN}-{RECOMMENDED_WORKERS_MAX}）')
    parser.add_argument('--content-types', nargs='+', 
                        choices=['videos', 'shorts', 'playlists', 'posts', 'streams'],
                        help='要获取的内容类型（可多选）。默认：如果URL中未指定类型，则只获取videos')
    parser.add_argument('--all-types', action='store_true',
                        help='获取所有类型的内容（videos, shorts, playlists, posts）。等同于 --content-types videos shorts playlists posts')
    parser.add_argument('-d', '--download-video', action='store_true',
                        help='下载视频文件、封面图片和信息文档（默认：只下载字幕）')
    
    args = parser.parse_args()
    
    # 处理内容类型参数
    content_types = None
    if args.all_types:
        content_types = ['videos', 'shorts', 'playlists', 'posts']
    elif args.content_types:
        content_types = args.content_types
    
    # 使用配置的默认值
    if args.workers is None:
        args.workers = DEFAULT_MAX_WORKERS
    
    # 验证并发数
    if args.workers < 1:
        print_colored("错误: 并发线程数必须大于0", Colors.RED)
        sys.exit(1)
    if args.workers > MAX_WORKERS_LIMIT:
        print_colored(f"警告: 并发线程数过大可能导致API限制，建议使用{RECOMMENDED_WORKERS_MIN}-{RECOMMENDED_WORKERS_MAX}", Colors.YELLOW)
    elif args.workers < RECOMMENDED_WORKERS_MIN or args.workers > RECOMMENDED_WORKERS_MAX:
        print_colored(f"提示: 建议并发线程数范围为 {RECOMMENDED_WORKERS_MIN}-{RECOMMENDED_WORKERS_MAX}", Colors.CYAN)
    
    # 执行获取（自动检测URL类型）
    success = get_all_videos(
        args.input_url, 
        output_csv=args.output, 
        resume=args.resume, 
        max_workers=args.workers,
        content_types=content_types,
        download_video_file=args.download_video
    )
    
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

