#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一配置文件
用于管理所有 ytdlp 相关脚本的配置
"""

import re
from pathlib import Path

# ==================== 路径配置 ====================

# 输出目录根目录
OUTPUT_DIR_ROOT = "/Volumes/UH100/YouTubeDownload03"

# 默认频道名称（向后兼容）
DEFAULT_CHANNEL_NAME = "DanKoeTalks"

# 默认输出目录（向后兼容）
OUTPUT_DIR = f"{OUTPUT_DIR_ROOT}/{DEFAULT_CHANNEL_NAME}"

# 默认下载列表文件名
DEFAULT_DOWNLOAD_LIST = f"todownload_links_{DEFAULT_CHANNEL_NAME}.txt"

# 默认CSV汇总文件名
DEFAULT_CSV_SUMMARY = f"download_summary_{DEFAULT_CHANNEL_NAME}.csv"


# 确保根目录存在
OUTPUT_DIR_ROOT_PATH = Path(OUTPUT_DIR_ROOT)
OUTPUT_DIR_ROOT_PATH.mkdir(parents=True, exist_ok=True)

# 默认输出路径（向后兼容）
OUTPUT_PATH = Path(OUTPUT_DIR)
OUTPUT_PATH.mkdir(parents=True, exist_ok=True)

# 下载列表文件路径（在输出目录下）
DOWNLOAD_LIST_PATH = OUTPUT_PATH / DEFAULT_DOWNLOAD_LIST

# CSV汇总文件路径（在输出目录下）
CSV_SUMMARY_PATH = OUTPUT_PATH / DEFAULT_CSV_SUMMARY

# 日志目录（在输出目录下）
LOG_DIR = OUTPUT_PATH / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


# ==================== 频道名称提取函数 ====================

def extract_channel_name_from_url(url):
    """从YouTube URL中提取频道名称
    
    Args:
        url: YouTube频道URL，支持以下格式：
            - https://www.youtube.com/@channelname
            - https://www.youtube.com/@channelname/videos
            - https://www.youtube.com/c/channelname
            - https://www.youtube.com/channel/UCxxxxx
            - https://www.youtube.com/user/username
            - @channelname
    
    Returns:
        频道名称字符串，如果无法提取则返回 None
    """
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
            # 频道ID通常以 UC 开头，使用ID作为名称
            return f"channel_{channel_id}"
    
    return None


def get_output_path_for_channel(channel_name=None, url=None):
    """根据频道名称或URL获取输出路径
    
    Args:
        channel_name: 频道名称（可选）
        url: YouTube频道URL（可选，如果提供会从中提取频道名称）
    
    Returns:
        Path对象，指向该频道的输出目录
    """
    # 如果提供了URL，尝试从中提取频道名称
    if url and not channel_name:
        channel_name = extract_channel_name_from_url(url)
    
    # 如果仍然没有频道名称，使用默认值
    if not channel_name:
        channel_name = DEFAULT_CHANNEL_NAME
    
    # 清理频道名称，确保可以作为文件夹名
    # 只保留字母、数字、中文、下划线、连字符和点
    channel_name = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fa5_\-\.]', '_', channel_name)
    
    # 构建输出路径
    output_path = OUTPUT_DIR_ROOT_PATH / channel_name
    output_path.mkdir(parents=True, exist_ok=True)
    
    return output_path


def get_download_list_path_for_channel(channel_name=None, url=None):
    """根据频道名称或URL获取下载列表文件路径
    
    Args:
        channel_name: 频道名称（可选）
        url: YouTube频道URL（可选）
    
    Returns:
        Path对象，指向该频道的下载列表文件
    """
    output_path = get_output_path_for_channel(channel_name, url)
    
    # 如果提供了URL，尝试从中提取频道名称
    if url and not channel_name:
        channel_name = extract_channel_name_from_url(url)
    
    # 如果仍然没有频道名称，使用默认值
    if not channel_name:
        channel_name = DEFAULT_CHANNEL_NAME
    
    # 清理频道名称
    channel_name = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fa5_\-\.]', '_', channel_name)
    
    return output_path / f"todownload_links_{channel_name}.txt"


def get_csv_summary_path_for_channel(channel_name=None, url=None):
    """根据频道名称或URL获取CSV汇总文件路径
    
    Args:
        channel_name: 频道名称（可选）
        url: YouTube频道URL（可选）
    
    Returns:
        Path对象，指向该频道的CSV汇总文件
    """
    output_path = get_output_path_for_channel(channel_name, url)
    
    # 如果提供了URL，尝试从中提取频道名称
    if url and not channel_name:
        channel_name = extract_channel_name_from_url(url)
    
    # 如果仍然没有频道名称，使用默认值
    if not channel_name:
        channel_name = DEFAULT_CHANNEL_NAME
    
    # 清理频道名称
    channel_name = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fa5_\-\.]', '_', channel_name)
    
    return output_path / f"download_summary_{channel_name}.csv"

# ==================== 重试配置 ====================

# 获取视频信息的重试配置
GET_INFO_MAX_RETRIES = 3
GET_INFO_INITIAL_DELAY = 1  # 秒
GET_INFO_BACKOFF_FACTOR = 2  # 指数退避因子

# 下载字幕的重试配置
DOWNLOAD_SUBTITLE_MAX_RETRIES = 2
DOWNLOAD_SUBTITLE_INITIAL_DELAY = 0.5  # 秒
DOWNLOAD_SUBTITLE_BACKOFF_FACTOR = 2

# 下载视频的重试配置
DOWNLOAD_VIDEO_MAX_RETRIES = 3
DOWNLOAD_VIDEO_INITIAL_DELAY = 2  # 秒
DOWNLOAD_VIDEO_BACKOFF_FACTOR = 2

# ==================== 并发配置 ====================

# 默认并发线程数
DEFAULT_MAX_WORKERS = 5

# 最大并发线程数（安全限制）
MAX_WORKERS_LIMIT = 20

# 推荐并发线程数范围
RECOMMENDED_WORKERS_MIN = 3
RECOMMENDED_WORKERS_MAX = 10

# ==================== 超时配置 ====================

# 获取视频信息超时时间（秒）
GET_INFO_TIMEOUT = 30

# 下载字幕超时时间（秒）
DOWNLOAD_SUBTITLE_TIMEOUT = 60

# 下载视频超时时间（秒）
DOWNLOAD_VIDEO_TIMEOUT = 3600  # 1小时

# 获取频道/播放列表超时时间（秒）
GET_PLAYLIST_TIMEOUT = 300  # 5分钟

# ==================== 进度保存配置 ====================

# 每处理多少个视频保存一次进度
PROGRESS_SAVE_INTERVAL = 10

# ==================== 速率控制配置 ====================

# 每个请求之间的延迟（秒）- 防止速率限制
# 建议值：1-3 秒，不要设置为 0
REQUEST_DELAY = 1.0  # 秒

# 批量处理间隔：每处理多少个视频后暂停
BATCH_PAUSE_INTERVAL = 20  # 每处理 20 个视频暂停一次

# 批量处理暂停时长（秒）
BATCH_PAUSE_DURATION = 10  # 暂停 10 秒

# 速率限制检测：遇到 429 错误时的额外延迟（秒）
RATE_LIMIT_EXTRA_DELAY = 30  # 遇到速率限制时额外等待 30 秒

# 速率限制最大重试次数
RATE_LIMIT_MAX_RETRIES = 5

# ==================== 用户代理配置 ====================

# 用户代理字符串（模拟真实浏览器）
# 如果为 None，使用 yt-dlp 默认值
USER_AGENT = None  # 例如: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# 自定义请求头（可选）
CUSTOM_HEADERS = {
    # 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    # 'Accept-Language': 'en-US,en;q=0.5',
    # 'Accept-Encoding': 'gzip, deflate',
    # 'Connection': 'keep-alive',
}

# ==================== 日志配置 ====================

# 是否启用日志记录
ENABLE_LOGGING = True

# 日志级别: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL = "INFO"

# 日志文件最大大小（MB）
LOG_MAX_SIZE_MB = 10

# 日志文件保留数量
LOG_BACKUP_COUNT = 5

# 日志格式
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ==================== yt-dlp 配置 ====================

# yt-dlp 默认选项
YT_DLP_DEFAULT_OPTS = {
    'quiet': True,
    'no_warnings': True,
}

# 字幕下载选项
YT_DLP_SUBTITLE_OPTS = {
    'writesubtitles': True,
    'writeautomaticsub': True,
    'subtitlesformat': 'srt',
    'skip_download': True,
    # 指定要下载的字幕语言：英文和简体中文
    # 语言代码说明：
    #   en: 英文
    #   zh-Hans: 简体中文
    'subtitleslangs': ['en', 'zh-Hans'],
}

# 视频下载选项
YT_DLP_VIDEO_OPTS = {
    'format': 'bestvideo+bestaudio/best',
    'writesubtitles': True,
    'writeautomaticsub': True,
    'subtitlesformat': 'srt',
    # 指定要下载的字幕语言：英文和简体中文
    # 语言代码说明：
    #   en: 英文
    #   zh-Hans: 简体中文
    'subtitleslangs': ['en', 'zh-Hans'],
    'writethumbnail': True,
    'embedthumbnail': True,
    'ignoreerrors': True,
    'concurrent_fragments': 5,
    'noplaylist': True,
    'restrictfilenames': True,
    # 跳过已存在的文件，不覆盖
    'nooverwrites': True,
    # 不覆盖后处理生成的文件（如字幕、缩略图等）
    'nopostoverwrites': True,
}

