#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地配置文件 - 用于覆盖默认配置
"""

import re
from pathlib import Path

# ==================== 路径配置 ====================

# 输出目录根目录 - 修改为本地路径
OUTPUT_DIR_ROOT = "/Volumes/UH100/YouTubeDownload03"

# 默认频道名称（向后兼容）
DEFAULT_CHANNEL_NAME = "DanKoeTalks"

# 默认输出目录（向后兼容）
OUTPUT_DIR = f"{OUTPUT_DIR_ROOT}/{DEFAULT_CHANNEL_NAME}"

# 确保根目录存在
OUTPUT_DIR_ROOT_PATH = Path(OUTPUT_DIR_ROOT)
OUTPUT_DIR_ROOT_PATH.mkdir(parents=True, exist_ok=True)

# 默认输出路径（向后兼容）
OUTPUT_PATH = Path(OUTPUT_DIR)
OUTPUT_PATH.mkdir(parents=True, exist_ok=True)

# 其他配置保持与原config.py一致，但使用新的OUTPUT_DIR_ROOT
DEFAULT_DOWNLOAD_LIST = f"todownload_links_{DEFAULT_CHANNEL_NAME}.txt"
DEFAULT_CSV_SUMMARY = f"download_summary_{DEFAULT_CHANNEL_NAME}.csv"

DOWNLOAD_LIST_PATH = OUTPUT_PATH / DEFAULT_DOWNLOAD_LIST
CSV_SUMMARY_PATH = OUTPUT_PATH / DEFAULT_CSV_SUMMARY

LOG_DIR = OUTPUT_PATH / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ==================== 频道名称提取函数 ====================
def extract_channel_name_from_url(url):
    """从YouTube URL中提取频道名称"""
    if not url:
        return None
    
    url = url.strip()
    
    # 如果是 @handle 格式
    if url.startswith('@'):
        channel_name = url[1:].split('/')[0]
        return channel_name
    
    # 提取 @handle
    if '/@' in url:
        match = re.search(r'/@([^/?]+)', url)
        if match:
            channel_name = match.group(1).split('/')[0]
            return channel_name
    
    # 提取 /c/ 格式
    if '/c/' in url:
        match = re.search(r'/c/([^/?]+)', url)
        if match:
            channel_name = match.group(1).split('/')[0]
            return channel_name
    
    # 提取 /user/ 格式
    if '/user/' in url:
        match = re.search(r'/user/([^/?]+)', url)
        if match:
            channel_name = match.group(1).split('/')[0]
            return channel_name
    
    # 提取 /channel/ 格式（频道ID）
    if '/channel/' in url:
        match = re.search(r'/channel/([^/?]+)', url)
        if match:
            channel_id = match.group(1).split('/')[0]
            return f"channel_{channel_id}"
    
    return None

def get_output_path_for_channel(channel_name=None, url=None):
    """根据频道名称或URL获取输出路径"""
    if url and not channel_name:
        channel_name = extract_channel_name_from_url(url)
    
    if not channel_name:
        channel_name = DEFAULT_CHANNEL_NAME
    
    channel_name = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fa5_\-\.]', '_', channel_name)
    output_path = OUTPUT_DIR_ROOT_PATH / channel_name
    output_path.mkdir(parents=True, exist_ok=True)
    return output_path

def get_download_list_path_for_channel(channel_name=None, url=None):
    """根据频道名称或URL获取下载列表文件路径"""
    output_path = get_output_path_for_channel(channel_name, url)
    if url and not channel_name:
        channel_name = extract_channel_name_from_url(url)
    if not channel_name:
        channel_name = DEFAULT_CHANNEL_NAME
    channel_name = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fa5_\-\.]', '_', channel_name)
    return output_path / f"todownload_links_{channel_name}.txt"

def get_csv_summary_path_for_channel(channel_name=None, url=None):
    """根据频道名称或URL获取CSV汇总文件路径"""
    output_path = get_output_path_for_channel(channel_name, url)
    if url and not channel_name:
        channel_name = extract_channel_name_from_url(url)
    if not channel_name:
        channel_name = DEFAULT_CHANNEL_NAME
    channel_name = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fa5_\-\.]', '_', channel_name)
    return output_path / f"download_summary_{channel_name}.csv"

# ==================== 其他配置保持默认 ====================
GET_INFO_MAX_RETRIES = 3
GET_INFO_INITIAL_DELAY = 1
GET_INFO_BACKOFF_FACTOR = 2
DOWNLOAD_SUBTITLE_MAX_RETRIES = 2
DOWNLOAD_SUBTITLE_INITIAL_DELAY = 0.5
DOWNLOAD_SUBTITLE_BACKOFF_FACTOR = 2
DOWNLOAD_VIDEO_MAX_RETRIES = 3
DOWNLOAD_VIDEO_INITIAL_DELAY = 2
DOWNLOAD_VIDEO_BACKOFF_FACTOR = 2
DEFAULT_MAX_WORKERS = 5
MAX_WORKERS_LIMIT = 20
RECOMMENDED_WORKERS_MIN = 3
RECOMMENDED_WORKERS_MAX = 10
GET_INFO_TIMEOUT = 30
DOWNLOAD_SUBTITLE_TIMEOUT = 60
DOWNLOAD_VIDEO_TIMEOUT = 3600
GET_PLAYLIST_TIMEOUT = 300
PROGRESS_SAVE_INTERVAL = 10
REQUEST_DELAY = 1.0
BATCH_PAUSE_INTERVAL = 20
BATCH_PAUSE_DURATION = 10
RATE_LIMIT_EXTRA_DELAY = 30
RATE_LIMIT_MAX_RETRIES = 5
USER_AGENT = None
CUSTOM_HEADERS = {}
ENABLE_LOGGING = True
LOG_LEVEL = "INFO"
LOG_MAX_SIZE_MB = 10
LOG_BACKUP_COUNT = 5
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
YT_DLP_DEFAULT_OPTS = {'quiet': True, 'no_warnings': True}
YT_DLP_SUBTITLE_OPTS = {
    'writesubtitles': True,
    'writeautomaticsub': True,
    'subtitlesformat': 'srt',
    'skip_download': True,
    'subtitleslangs': ['en', 'zh-Hans'],
}
YT_DLP_VIDEO_OPTS = {
    'format': 'bestvideo+bestaudio/best',
    'writesubtitles': True,
    'writeautomaticsub': True,
    'subtitlesformat': 'srt',
    'subtitleslangs': ['en', 'zh-Hans'],
    'writethumbnail': True,
    'embedthumbnail': True,
    'ignoreerrors': True,
    'concurrent_fragments': 5,
    'noplaylist': True,
    'restrictfilenames': True,
    'nooverwrites': True,
    'nopostoverwrites': True,
}