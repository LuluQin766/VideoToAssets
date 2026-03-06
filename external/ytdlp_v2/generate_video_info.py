#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成视频信息Markdown文件
"""

import json
import sys
from pathlib import Path
from datetime import datetime
import yt_dlp
from config import YT_DLP_DEFAULT_OPTS
from logger_utils import setup_logger, get_log_file_name

def format_duration(seconds):
    """将秒数格式化为 MM:SS 或 HH:MM:SS"""
    if not seconds or seconds == 0:
        return "未知"
    try:
        seconds = int(float(seconds))
    except (ValueError, TypeError):
        return "未知"
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
        return "未知"
    try:
        year = date_str[:4]
        month = date_str[4:6]
        day = date_str[6:8]
        return f"{year}-{month}-{day}"
    except:
        return date_str[:4] if len(date_str) >= 4 else "未知"

def get_language_name(lang_code):
    """将语言代码转换为友好的语言名称"""
    language_map = {
        'en': '英文',
        'en-US': '美式英文',
        'en-GB': '英式英文',
        'en-orig': '原始英文',
        'zh': '中文',
        'zh-Hans': '简体中文',
        'zh-Hant': '繁体中文',
        'zh-CN': '简体中文（中国）',
        'zh-TW': '繁体中文（台湾）',
        'ja': '日文',
        'ko': '韩文',
        'fr': '法文',
        'de': '德文',
        'es': '西班牙文',
        'it': '意大利文',
        'pt': '葡萄牙文',
        'ru': '俄文',
        'ar': '阿拉伯文',
        'hi': '印地文',
        'th': '泰文',
        'vi': '越南文',
    }
    # 如果找到映射，返回友好名称，否则返回原代码
    return language_map.get(lang_code, lang_code)

def get_video_info(video_url, logger=None):
    """获取视频的详细信息"""
    try:
        ydl_opts = YT_DLP_DEFAULT_OPTS.copy()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            if logger and info:
                logger.debug(f"成功获取视频信息: {video_url}")
            return info
    except Exception as e:
        if logger:
            logger.warning(f"获取视频信息失败: {video_url} - {str(e)}")
        return None

def generate_markdown(video_url, output_file, logger=None):
    """生成视频信息的Markdown文件"""
    info = get_video_info(video_url, logger=logger)
    
    if not info:
        # 如果无法获取信息，生成基本信息
        md_content = f"""# 视频信息

## 基本信息
- **视频链接**: {video_url}
- **获取时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **状态**: 无法获取详细信息

## 说明
此视频的信息无法自动获取，请手动查看视频页面获取详细信息。
"""
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(md_content)
        return False
    
    # 提取信息
    title = info.get('title', '未知标题')
    description = info.get('description', '无描述')
    view_count = info.get('view_count', 0) or 0
    like_count = info.get('like_count', 0) or 0
    comment_count = info.get('comment_count', 0) or 0
    duration = info.get('duration', 0) or 0
    upload_date = info.get('upload_date', '') or ''
    release_date = info.get('release_date', '') or ''
    channel = info.get('channel', '未知频道')
    channel_id = info.get('channel_id', '')
    channel_url = info.get('channel_url', '')
    channel_follower_count = info.get('channel_follower_count', 0) or 0
    uploader = info.get('uploader', '未知上传者')
    uploader_id = info.get('uploader_id', '')
    uploader_url = info.get('uploader_url', '')
    thumbnail = info.get('thumbnail', '')
    thumbnails = info.get('thumbnails', [])
    tags = info.get('tags', [])
    categories = info.get('categories', [])
    language = info.get('language', '未知')
    age_limit = info.get('age_limit', 0)
    availability = info.get('availability', 'public')
    webpage_url = info.get('webpage_url', video_url)
    video_id = info.get('id', '')
    
    # 视频格式信息
    format_note = info.get('format_note', '未知')
    width = info.get('width', 0) or 0
    height = info.get('height', 0) or 0
    fps = info.get('fps', 0) or 0
    vcodec = info.get('vcodec', '未知')
    acodec = info.get('acodec', '未知')
    filesize = info.get('filesize', 0) or 0
    filesize_approx = info.get('filesize_approx', 0) or 0
    
    # 其他信息
    average_rating = info.get('average_rating', 0) or 0
    chapters = info.get('chapters', [])
    subtitles = info.get('subtitles', {})
    automatic_captions = info.get('automatic_captions', {})
    
    # 格式化
    duration_str = format_duration(duration)
    date_str = format_date(upload_date)
    
    # 格式化文件大小
    def format_size(size_bytes):
        if size_bytes == 0:
            return "未知"
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"
    
    file_size_str = format_size(filesize if filesize > 0 else filesize_approx)
    
    # 生成Markdown内容
    md_content = f"""# {title}

## 📹 基本信息

| 项目 | 内容 |
|------|------|
| **视频标题** | {title} |
| **视频ID** | `{video_id}` |
| **视频链接** | [{webpage_url}]({webpage_url}) |
| **频道名称** | {channel} |
| **频道订阅数** | {channel_follower_count:,} |
| **频道链接** | {channel_url if channel_url else 'N/A'} |
| **上传者** | {uploader} |
| **上传日期** | {date_str} |
| **发布日期** | {format_date(release_date) if release_date else 'N/A'} |
| **视频时长** | {duration_str} |
| **语言** | {language} |
| **年龄限制** | {age_limit}+ |
| **可用性** | {availability} |

## 📊 统计数据

| 指标 | 数值 |
|------|------|
| **播放量** | {view_count:,} |
| **点赞量** | {like_count:,} |
| **评论数** | {comment_count:,} |
| **点赞率** | {(like_count/view_count*100) if view_count > 0 else 0:.2f}% |
| **平均评分** | {average_rating:.2f}/5.0 |

## 📝 视频描述

{description}

## 🏷️ 标签

"""
    
    if tags:
        for tag in tags:
            md_content += f"- `{tag}`\n"
    else:
        md_content += "无标签\n"
    
    md_content += f"""
## 📂 分类

"""
    if categories:
        for category in categories:
            md_content += f"- {category}\n"
    else:
        md_content += "无分类\n"
    
    md_content += f"""
## 🖼️ 缩略图

![视频缩略图]({thumbnail})

## 🎬 视频技术信息

| 项目 | 内容 |
|------|------|
| **分辨率** | {width}x{height} |
| **格式** | {format_note} |
| **视频编码** | {vcodec} |
| **音频编码** | {acodec} |
| **帧率** | {fps} fps |
| **文件大小** | {file_size_str} |

## 📝 字幕信息

"""
    
    # 添加字幕信息
    if subtitles:
        md_content += "### 可用字幕语言：\n"
        for lang in subtitles.keys():
            lang_name = get_language_name(lang)
            md_content += f"- {lang_name} (`{lang}`)\n"
    else:
        md_content += "无字幕\n"
    
    if automatic_captions:
        md_content += "\n### 自动生成字幕语言：\n"
        for lang in automatic_captions.keys():
            lang_name = get_language_name(lang)
            md_content += f"- {lang_name} (`{lang}`)\n"
    
    # 添加章节信息
    if chapters:
        md_content += f"""
## 📑 视频章节

"""
        for i, chapter in enumerate(chapters, 1):
            start_time = format_duration(chapter.get('start_time', 0))
            title = chapter.get('title', f'章节 {i}')
            md_content += f"{i}. **{start_time}** - {title}\n"
    
    md_content += f"""
## 📅 元数据

- **获取时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **视频格式**: {info.get('format', '未知')}
- **扩展名**: {info.get('ext', '未知')}

## 🔗 相关链接

- [YouTube视频页面]({webpage_url})
- [频道页面]({channel_url if channel_url else 'N/A'})
- [上传者页面]({uploader_url if uploader_url else 'N/A'})

---
*此文件由 batch_download.sh 自动生成*
"""
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    return True

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("使用方法: python3 generate_video_info.py <视频URL> <输出文件路径>")
        sys.exit(1)
    
    # 设置日志
    log_file = get_log_file_name('generate_video_info')
    logger = setup_logger('generate_video_info', log_file)
    
    video_url = sys.argv[1]
    output_file = sys.argv[2]
    
    logger.info(f"开始生成视频信息: {video_url} -> {output_file}")
    success = generate_markdown(video_url, output_file, logger=logger)
    if success:
        print(f"✅ 视频信息已生成: {output_file}")
        logger.info(f"视频信息已生成: {output_file}")
    else:
        print(f"⚠️  生成基本信息: {output_file}")
        logger.warning(f"仅生成基本信息: {output_file}")

