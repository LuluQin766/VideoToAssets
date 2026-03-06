#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量下载YouTube视频的主程序
处理视频、音频、字幕下载和信息文件生成
"""

import re
import sys
import json
import csv
import subprocess
from pathlib import Path
from datetime import datetime
import yt_dlp
from config import (
    OUTPUT_PATH, DOWNLOAD_LIST_PATH, CSV_SUMMARY_PATH,
    DEFAULT_MAX_WORKERS,
    DOWNLOAD_VIDEO_MAX_RETRIES, DOWNLOAD_VIDEO_INITIAL_DELAY, DOWNLOAD_VIDEO_BACKOFF_FACTOR,
    DOWNLOAD_VIDEO_TIMEOUT,
    YT_DLP_DEFAULT_OPTS, YT_DLP_VIDEO_OPTS
)
from logger_utils import setup_logger, get_log_file_name
from convert_subtitles_to_text import convert_single_srt_to_text

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

def convert_url(url):
    """转换URL格式（去除引号，embed转watch）"""
    # 去除引号
    url = url.strip().strip('"').strip("'")
    
    # 如果是embed格式，转换为watch格式
    if 'youtube.com/embed/' in url:
        video_id = extract_video_id_from_url(url)
        if video_id:
            return f"https://www.youtube.com/watch?v={video_id}"
    # 如果是youtu.be格式，转换为watch格式
    elif 'youtu.be/' in url:
        video_id = extract_video_id_from_url(url)
        if video_id:
            return f"https://www.youtube.com/watch?v={video_id}"
    
    return url

def get_video_title(url, logger=None):
    """获取视频标题"""
    try:
        ydl_opts = YT_DLP_DEFAULT_OPTS.copy()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', '') if info else None
            if logger and title:
                logger.debug(f"获取视频标题: {title[:50]}")
            return title
    except Exception as e:
        if logger:
            logger.warning(f"获取视频标题失败: {url} - {str(e)}")
        pass
    return None

def clean_title_for_filename(title):
    """清理标题，用于文件名（只保留字母、数字、中文、下划线和连字符）"""
    if not title:
        return ""
    # 使用正则表达式清理特殊字符
    clean = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fa5_-]', '', title)
    return clean

def get_folder_name(url, logger=None):
    """获取文件夹名（视频标题前10个字符）"""
    title = get_video_title(url, logger=logger)
    if not title:
        return f"video_{int(datetime.now().timestamp())}"
    
    clean_title = clean_title_for_filename(title)
    if not clean_title:
        return f"video_{int(datetime.now().timestamp())}"
    
    # 截取前10个字符
    return clean_title[:10] if len(clean_title) > 10 else clean_title

def get_info_filename(url, logger=None):
    """获取信息文件名（视频标题前20个字符 + 时间戳）"""
    title = get_video_title(url, logger=logger)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    if not title:
        return f"video_info_{timestamp}.md"
    
    clean_title = clean_title_for_filename(title)
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
        
        ydl_opts = YT_DLP_DEFAULT_OPTS.copy()
        ydl_opts.update(YT_DLP_VIDEO_OPTS)
        ydl_opts['outtmpl'] = str(output_path / '%(title)s.%(ext)s')
        
        if logger:
            logger.info(f"开始下载视频: {url} -> {output_path}")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        if logger:
            logger.info(f"视频下载完成: {url}")
        return True, "", ""
    except Exception as e:
        error_msg = str(e)
        if logger:
            logger.error(f"视频下载失败: {url} - {error_msg}", exc_info=True)
        return False, "", error_msg

def get_video_details(url, logger=None):
    """获取视频详细信息"""
    try:
        ydl_opts = YT_DLP_DEFAULT_OPTS.copy()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if logger and info:
                logger.debug(f"成功获取视频详情: {url}")
            return info
    except Exception as e:
        if logger:
            logger.warning(f"获取视频详情失败: {url} - {str(e)}")
        pass
    return None

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

def check_subtitles_status(folder_path):
    """检查字幕下载和转换状态
    返回: (字幕状态字典, 缺失项列表)
    字幕状态字典包含：
    - has_en_srt: 是否有英文字幕文件
    - has_zh_srt: 是否有简体中文字幕文件
    - has_en_txt: 英文txt文件是否存在
    - has_en_md: 英文md文件是否存在
    - has_zh_txt: 简体中文txt文件是否存在
    - has_zh_md: 简体中文md文件是否存在
    """
    folder = Path(folder_path)
    if not folder.exists():
        return {}, ['文件夹不存在']
    
    status = {
        'has_en_srt': False,
        'has_zh_srt': False,
        'has_en_txt': False,
        'has_en_md': False,
        'has_zh_txt': False,
        'has_zh_md': False,
    }
    missing = []
    
    # 查找所有字幕文件
    srt_files = list(folder.glob('*.srt'))
    
    # 检查英文字幕
    en_srt_files = [f for f in srt_files if '.en.' in f.name or f.name.endswith('.en.srt')]
    if en_srt_files:
        status['has_en_srt'] = True
        en_stem = en_srt_files[0].stem
        en_txt = folder / f"{en_stem}.txt"
        en_md = folder / f"{en_stem}.md"
        if en_txt.exists():
            status['has_en_txt'] = True
        else:
            missing.append('英文字幕txt文件')
        if en_md.exists():
            status['has_en_md'] = True
        else:
            missing.append('英文字幕md文件')
    else:
        missing.append('英文字幕文件')
    
    # 检查简体中文字幕
    zh_srt_files = [f for f in srt_files if '.zh-Hans.' in f.name or f.name.endswith('.zh-Hans.srt')]
    if zh_srt_files:
        status['has_zh_srt'] = True
        zh_stem = zh_srt_files[0].stem
        zh_txt = folder / f"{zh_stem}.txt"
        zh_md = folder / f"{zh_stem}.md"
        if zh_txt.exists():
            status['has_zh_txt'] = True
        else:
            missing.append('简体中文字幕txt文件')
        if zh_md.exists():
            status['has_zh_md'] = True
        else:
            missing.append('简体中文字幕md文件')
    else:
        missing.append('简体中文字幕文件')
    
    return status, missing

def update_download_summary(save_path, video_data, update_existing=False, logger=None):
    """更新下载汇总CSV文件
    如果文件不存在，则新增文件。
    如果文件已存在，则先备份，然后搜索是否有这条视频的数据：
    - 如果有，将新数据进行替换
    - 如果不存在，则新增数据
    
    Args:
        save_path: 保存路径
        video_data: 视频数据字典
        update_existing: 已废弃，保留以兼容旧代码
        logger: 日志记录器（可选）
    """
    csv_file = Path(save_path) / "download_summary.csv"
    target_url = video_data.get('url', '').strip()
    
    # 定义CSV表头
    headers = [
        '下载时间',
        '文件夹名',
        '视频标题',
        '视频作者',
        '平台',
        '视频链接',
        '播放量',
        '点赞量',
        '视频简介（前200字符）',
        '视频文件',
        '音频文件',
        '字幕文件',
        '封面图片',
        '信息文件'
    ]
    
    try:
        # 如果文件不存在，创建新文件并写入数据
        if not csv_file.exists():
            with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                writer.writerow([
                    video_data.get('download_time', ''),
                    video_data.get('folder_name', ''),
                    video_data.get('title', ''),
                    video_data.get('uploader', ''),
                    video_data.get('platform', 'YouTube'),
                    video_data.get('url', ''),
                    video_data.get('view_count', 0),
                    video_data.get('like_count', 0),
                    video_data.get('description', '')[:200],
                    '✅' if video_data.get('has_video', False) else '❌',
                    '✅' if video_data.get('has_audio', False) else '❌',
                    '✅' if video_data.get('has_subtitle', False) else '❌',
                    '✅' if video_data.get('has_thumbnail', False) else '❌',
                    '✅' if video_data.get('has_info_file', False) else '❌'
                ])
            return True
        
        # 文件存在，先备份
        backup_file = csv_file.parent / f"download_summary_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        try:
            import shutil
            shutil.copy2(csv_file, backup_file)
            if logger:
                logger.debug(f"已备份CSV文件: {backup_file}")
        except Exception as e:
            if logger:
                logger.warning(f"备份CSV文件失败: {str(e)}")
        
        # 读取所有记录
        rows = []
        existing_headers = []
        found_existing = False
        
        with open(csv_file, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            existing_headers = list(reader.fieldnames) if reader.fieldnames else []
            
            # 如果旧的CSV文件没有某些列，添加它们
            for header in headers:
                if header not in existing_headers:
                    existing_headers.append(header)
            
            for row in reader:
                # 检查是否是要更新的记录（通过URL匹配）
                if row.get('视频链接', '').strip() == target_url:
                    # 更新这一行
                    row['下载时间'] = video_data.get('download_time', row.get('下载时间', ''))
                    row['文件夹名'] = video_data.get('folder_name', row.get('文件夹名', ''))
                    row['视频标题'] = video_data.get('title', row.get('视频标题', ''))
                    row['视频作者'] = video_data.get('uploader', row.get('视频作者', ''))
                    row['平台'] = video_data.get('platform', 'YouTube')
                    row['播放量'] = str(video_data.get('view_count', 0))
                    row['点赞量'] = str(video_data.get('like_count', 0))
                    row['视频简介（前200字符）'] = video_data.get('description', '')[:200]
                    row['视频文件'] = '✅' if video_data.get('has_video', False) else '❌'
                    row['音频文件'] = '✅' if video_data.get('has_audio', False) else '❌'
                    row['字幕文件'] = '✅' if video_data.get('has_subtitle', False) else '❌'
                    row['封面图片'] = '✅' if video_data.get('has_thumbnail', False) else '❌'
                    row['信息文件'] = '✅' if video_data.get('has_info_file', False) else '❌'
                    found_existing = True
                else:
                    # 对于未更新的旧记录，确保所有字段都存在
                    for header in headers:
                        if header not in row:
                            row[header] = '' if header not in ['视频文件', '音频文件', '字幕文件', '封面图片', '信息文件'] else '❌'
                
                rows.append(row)
        
        # 如果没有找到现有记录，添加新记录
        if not found_existing:
            new_row = {
                '下载时间': video_data.get('download_time', ''),
                '文件夹名': video_data.get('folder_name', ''),
                '视频标题': video_data.get('title', ''),
                '视频作者': video_data.get('uploader', ''),
                '平台': video_data.get('platform', 'YouTube'),
                '视频链接': video_data.get('url', ''),
                '播放量': str(video_data.get('view_count', 0)),
                '点赞量': str(video_data.get('like_count', 0)),
                '视频简介（前200字符）': video_data.get('description', '')[:200],
                '视频文件': '✅' if video_data.get('has_video', False) else '❌',
                '音频文件': '✅' if video_data.get('has_audio', False) else '❌',
                '字幕文件': '✅' if video_data.get('has_subtitle', False) else '❌',
                '封面图片': '✅' if video_data.get('has_thumbnail', False) else '❌',
                '信息文件': '✅' if video_data.get('has_info_file', False) else '❌'
            }
            rows.append(new_row)
        
        # 写回文件
        with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)
        
        return True
    except Exception as e:
        print_colored(f"更新汇总表出错: {str(e)}", Colors.YELLOW)
        if logger:
            logger.error(f"更新汇总表出错: {str(e)}", exc_info=True)
        return False

def generate_video_info(url, info_file_path):
    """生成视频信息文件"""
    try:
        cmd = [
            sys.executable,
            str(GENERATE_INFO_SCRIPT),
            url,
            str(info_file_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return result.returncode == 0
    except Exception:
        return False

def read_download_summary(csv_file):
    """读取下载汇总CSV文件，返回已下载的视频URL集合"""
    downloaded_urls = set()
    if not Path(csv_file).exists():
        return downloaded_urls
    
    try:
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                url = row.get('视频链接', '').strip()
                if url:
                    downloaded_urls.add(url)
    except Exception as e:
        print_colored(f"读取汇总表出错: {str(e)}", Colors.YELLOW)
    
    return downloaded_urls

def check_video_downloaded(url, save_path, folder_name):
    """检查视频是否已经完整下载（包括所有字幕和转换）
    返回: (状态, 状态消息, 详细信息字典)
    状态: True=完整下载, "partial"=部分下载, False=未下载
    """
    folder_path = save_path / folder_name
    
    # 检查文件夹是否存在
    if not folder_path.exists():
        return False, "文件夹不存在", {}
    
    # 检查视频文件
    has_video, has_audio, has_subtitle, has_thumbnail = check_files_exist(folder_path)
    
    # 检查信息文件（.md文件，排除字幕转换生成的md文件）
    all_md_files = list(folder_path.glob('*.md'))
    # 排除字幕转换生成的md文件（通常包含语言代码）
    info_md_files = [f for f in all_md_files if '.en.' not in f.name and '.zh-Hans.' not in f.name 
                     and not f.name.endswith('.en.md') and not f.name.endswith('.zh-Hans.md')]
    has_info_file = len(info_md_files) > 0
    
    # 检查字幕状态（英文和简体中文）
    subtitle_status, missing_subtitles = check_subtitles_status(folder_path)
    
    # 详细信息
    details = {
        'has_video': has_video,
        'has_audio': has_audio,
        'has_subtitle': has_subtitle,
        'has_thumbnail': has_thumbnail,
        'has_info_file': has_info_file,
        'folder_path': folder_path,
        'subtitle_status': subtitle_status,
        'missing_subtitles': missing_subtitles
    }
    
    # 检查是否完整：视频文件 + 信息文件 + 英文字幕完整 + 简体中文字幕完整
    is_complete = (
        has_video and 
        has_info_file and
        subtitle_status.get('has_en_srt', False) and
        subtitle_status.get('has_en_txt', False) and
        subtitle_status.get('has_en_md', False) and
        subtitle_status.get('has_zh_srt', False) and
        subtitle_status.get('has_zh_txt', False) and
        subtitle_status.get('has_zh_md', False)
    )
    
    if is_complete:
        return True, "已完整下载（包括所有字幕和转换）", details
    
    # 如果视频文件存在，但缺少字幕或转换，返回部分下载
    if has_video:
        missing_items = []
        if not subtitle_status.get('has_en_srt', False):
            missing_items.append('英文字幕')
        if not subtitle_status.get('has_zh_srt', False):
            missing_items.append('简体中文字幕')
        if missing_subtitles:
            missing_items.extend(missing_subtitles)
        if not has_info_file:
            missing_items.append('信息文件')
        
        status_msg = f"部分下载（缺少: {', '.join(missing_items) if missing_items else '未知'}）"
        return "partial", status_msg, details
    
    return False, "未下载", details

def read_download_list(list_file):
    """读取下载列表文件"""
    urls = []
    if not Path(list_file).exists():
        return urls
    
    try:
        with open(list_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    urls.append(line)
    except Exception as e:
        print_colored(f"读取下载列表出错: {str(e)}", Colors.RED)
    
    return urls

def convert_subtitles_in_download_dir(save_path, logger=None):
    """遍历下载目录中的所有视频文件夹，将字幕文件转换为txt和md格式
    
    Args:
        save_path: 下载保存路径
        logger: 日志记录器
    """
    save_path = Path(save_path)
    if not save_path.exists():
        print_colored(f"警告: 下载目录不存在: {save_path}", Colors.YELLOW)
        return
    
    # 获取所有子文件夹（视频文件夹）
    video_folders = [d for d in save_path.iterdir() if d.is_dir() and d.name != 'logs']
    
    if not video_folders:
        print_colored("未找到任何视频文件夹", Colors.YELLOW)
        return
    
    total_converted = 0
    total_skipped = 0
    
    print_colored(f"找到 {len(video_folders)} 个视频文件夹", Colors.BLUE)
    print()
    
    for folder in sorted(video_folders):
        # 查找该文件夹中的所有 .srt 字幕文件（主要格式）
        subtitle_files = list(folder.glob('*.srt'))
        
        if not subtitle_files:
            continue
        
        print_colored(f"处理文件夹: {folder.name}", Colors.CYAN)
        
        for subtitle_file in subtitle_files:
            # 检查是否已经存在对应的txt和md文件
            file_stem = subtitle_file.stem
            txt_file = folder / f"{file_stem}.txt"
            md_file = folder / f"{file_stem}.md"
            
            # 识别语言（从文件名中提取语言代码）
            lang_info = ""
            if '.en.' in subtitle_file.name or subtitle_file.name.endswith('.en.srt'):
                lang_info = " (英文)"
            elif '.zh-Hans.' in subtitle_file.name or subtitle_file.name.endswith('.zh-Hans.srt'):
                lang_info = " (简体中文)"
            elif '.zh-Hant.' in subtitle_file.name or subtitle_file.name.endswith('.zh-Hant.srt'):
                lang_info = " (繁体中文)"
            
            # 如果txt和md文件都已存在，跳过
            if txt_file.exists() and md_file.exists():
                if logger:
                    logger.debug(f"跳过已转换的字幕: {subtitle_file.name}")
                total_skipped += 1
                continue
            
            # 转换字幕文件
            try:
                if convert_single_srt_to_text(subtitle_file, folder):
                    print_colored(f"  ✅ 已转换: {subtitle_file.name}{lang_info}", Colors.GREEN)
                    total_converted += 1
                    if logger:
                        logger.info(f"成功转换字幕: {subtitle_file} -> {folder}")
                else:
                    print_colored(f"  ⚠️  转换失败: {subtitle_file.name}{lang_info}", Colors.YELLOW)
                    if logger:
                        logger.warning(f"字幕转换失败: {subtitle_file}")
            except Exception as e:
                print_colored(f"  ❌ 转换出错: {subtitle_file.name}{lang_info} - {str(e)}", Colors.RED)
                if logger:
                    logger.error(f"字幕转换异常: {subtitle_file} - {str(e)}", exc_info=True)
        
        print()
    
    # 显示统计信息
    print_colored(f"字幕转换完成:", Colors.GREEN)
    print_colored(f"  成功转换: {total_converted} 个", Colors.GREEN)
    if total_skipped > 0:
        print_colored(f"  跳过（已存在）: {total_skipped} 个", Colors.YELLOW)

def main():
    """主函数"""
    import argparse
    
    # 设置日志
    log_file = get_log_file_name('batch_download')
    logger = setup_logger('batch_download', log_file)
    logger.info("=" * 60)
    logger.info("批量下载YouTube视频")
    logger.info("=" * 60)
    
    parser = argparse.ArgumentParser(description='批量下载YouTube视频')
    parser.add_argument('-l', '--list', default=str(DOWNLOAD_LIST_PATH),
                        help=f'下载列表文件路径（默认: {DOWNLOAD_LIST_PATH}）')
    parser.add_argument('-p', '--path', default=str(OUTPUT_PATH),
                        help=f'下载保存路径（默认: {OUTPUT_PATH}）')
    parser.add_argument('-c', '--convert-subtitles', action='store_true',
                        help='在完成所有下载任务后，自动将字幕文件转换为txt和md格式（已默认启用，此参数保留以兼容旧代码）')
    parser.add_argument('-a', '--convert-all-subtitles', action='store_true',
                        help='在完成所有下载任务后，转换下载目录中所有视频文件夹的字幕文件（默认：仅转换当前下载任务的字幕）')
    
    args = parser.parse_args()
    logger.info(f"下载列表: {args.list}, 保存路径: {args.path}")
    
    # 检查列表文件是否存在
    list_file = args.list
    if not Path(list_file).exists():
        print_colored(f"错误: 找不到文件 {list_file}", Colors.RED)
        sys.exit(1)
    
    # 创建保存路径
    save_path = Path(args.path)
    save_path.mkdir(parents=True, exist_ok=True)
    
    # 读取下载列表
    urls = read_download_list(list_file)
    if not urls:
        print_colored("警告: 文件中没有找到有效的视频链接", Colors.YELLOW)
        sys.exit(1)
    
    # 读取已下载的视频列表（从CSV汇总表）
    csv_summary_file = save_path / "download_summary.csv"
    downloaded_urls = read_download_summary(csv_summary_file)
    
    total_count = len(urls)
    
    # 显示统计信息
    print_colored("=" * 60, Colors.CYAN)
    print_colored("📹 下载列表统计", Colors.GREEN)
    print_colored("=" * 60, Colors.CYAN)
    print_colored(f"总视频数: {total_count}", Colors.BLUE)
    if downloaded_urls:
        print_colored(f"已记录在汇总表: {len(downloaded_urls)} 个", Colors.YELLOW)
    print_colored("=" * 60, Colors.CYAN)
    print()
    
    # 处理每个视频
    current = 0
    success_count = 0
    failed_count = 0
    skipped_count = 0
    
    for url in urls:
        # 转换URL格式
        url = convert_url(url)
        
        current += 1
        print_colored("=" * 60, Colors.CYAN)
        print_colored(f"📥 正在处理 [{current}/{total_count}]", Colors.YELLOW)
        print_colored("=" * 60, Colors.CYAN)
        print_colored(f"链接: {url}", Colors.BLUE)
        
        # 获取文件夹名
        folder_name = get_folder_name(url, logger=logger)
        print_colored(f"文件夹名: {folder_name}", Colors.GREEN)
        
        # 检查是否已经在CSV汇总表中
        if url in downloaded_urls:
            print_colored("⚠️  已在汇总表中，检查文件状态...", Colors.YELLOW)
            folder_path = save_path / folder_name
            is_downloaded, status_msg, details = check_video_downloaded(url, save_path, folder_name)
            
            if is_downloaded is True:
                print_colored(f"✅ 已完整下载: {status_msg}", Colors.GREEN)
                print_colored("⏭️  跳过下载", Colors.CYAN)
                skipped_count += 1
                print()
                continue
            elif is_downloaded == "partial":
                print_colored(f"⚠️  {status_msg}", Colors.YELLOW)
                print_colored("📋 检测到部分下载，将继续完成缺失的任务...", Colors.CYAN)
                
                subtitle_status = details.get('subtitle_status', {})
                missing_subtitles = details.get('missing_subtitles', [])
                
                # 检查是否需要重新下载字幕
                need_download_subtitles = (
                    not subtitle_status.get('has_en_srt', False) or 
                    not subtitle_status.get('has_zh_srt', False)
                )
                
                if need_download_subtitles:
                    print_colored("📥 检测到字幕文件缺失，正在重新下载字幕...", Colors.CYAN)
                    # 重新下载视频（会下载字幕），但使用nooverwrites确保不覆盖视频
                    success, stdout, stderr = download_video(url, str(save_path), folder_name, logger=logger)
                    if success:
                        print_colored("✅ 字幕下载完成", Colors.GREEN)
                    else:
                        print_colored(f"⚠️  字幕下载失败: {stderr[:200] if stderr else '未知错误'}", Colors.YELLOW)
                
                # 检查并转换缺失的字幕文件
                folder_path = details['folder_path']
                srt_files = list(folder_path.glob('*.srt'))
                
                for srt_file in srt_files:
                    file_stem = srt_file.stem
                    txt_file = folder_path / f"{file_stem}.txt"
                    md_file = folder_path / f"{file_stem}.md"
                    
                    # 如果txt或md文件缺失，进行转换
                    if not txt_file.exists() or not md_file.exists():
                        print_colored(f"📝 转换字幕文件: {srt_file.name}", Colors.CYAN)
                        try:
                            if convert_single_srt_to_text(srt_file, folder_path):
                                print_colored(f"  ✅ 已转换: {srt_file.name}", Colors.GREEN)
                            else:
                                print_colored(f"  ⚠️  转换失败: {srt_file.name}", Colors.YELLOW)
                        except Exception as e:
                            print_colored(f"  ❌ 转换出错: {srt_file.name} - {str(e)}", Colors.RED)
                
                # 检查是否需要补充信息文件
                if details.get('has_video', False) and not details.get('has_info_file', False):
                    print_colored("📝 检测到信息文件缺失，正在补充...", Colors.CYAN)
                    video_details = get_video_details(url, logger=logger)
                    info_filename = get_info_filename(url, logger=logger)
                    info_file_path = details['folder_path'] / info_filename
                    has_info_file = generate_video_info(url, info_file_path)
                    if has_info_file:
                        print_colored(f"✅ 信息文件已生成: {info_filename}", Colors.GREEN)
                    else:
                        print_colored(f"⚠️  信息文件生成失败", Colors.YELLOW)
                else:
                    has_info_file = details.get('has_info_file', False)
                
                # 更新文件状态并重新检查
                has_video, has_audio, has_subtitle, has_thumbnail = check_files_exist(folder_path)
                subtitle_status, _ = check_subtitles_status(folder_path)
                
                # 更新CSV汇总表
                video_details = get_video_details(url, logger=logger)
                download_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                video_data = {
                    'download_time': download_time,
                    'folder_name': folder_name,
                    'title': video_details.get('title', '') if video_details else get_video_title(url, logger=logger) or '',
                    'uploader': video_details.get('uploader', '') if video_details else '',
                    'platform': 'YouTube',
                    'url': url,
                    'view_count': video_details.get('view_count', 0) or 0 if video_details else 0,
                    'like_count': video_details.get('like_count', 0) or 0 if video_details else 0,
                    'description': video_details.get('description', '') if video_details else '',
                    'has_video': has_video,
                    'has_audio': has_audio,
                    'has_subtitle': subtitle_status.get('has_en_srt', False) or subtitle_status.get('has_zh_srt', False),
                    'has_thumbnail': has_thumbnail,
                    'has_info_file': has_info_file
                }
                if update_download_summary(save_path, video_data, update_existing=True, logger=logger):
                    print_colored("✅ 已更新汇总表", Colors.GREEN)
                
                success_count += 1
                print()
                continue
            else:
                print_colored(f"⚠️  汇总表中有记录但文件不存在，将重新下载", Colors.YELLOW)
        
        # 检查文件是否存在（即使不在汇总表中）
        folder_path = save_path / folder_name
        is_downloaded, status_msg, details = check_video_downloaded(url, save_path, folder_name)
        
        if is_downloaded is True:
            print_colored(f"✅ 文件已存在: {status_msg}", Colors.GREEN)
            print_colored("⏭️  跳过下载", Colors.CYAN)
            skipped_count += 1
            
            # 如果文件存在但不在汇总表中，添加到汇总表
            if url not in downloaded_urls:
                print_colored("正在添加到汇总表...", Colors.CYAN)
                video_details = get_video_details(url)
                has_video, has_audio, has_subtitle, has_thumbnail = check_files_exist(folder_path)
                md_files = list(folder_path.glob('*.md'))
                has_info_file = len(md_files) > 0
                
                download_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                video_data = {
                    'download_time': download_time,
                    'folder_name': folder_name,
                    'title': video_details.get('title', '') if video_details else get_video_title(url) or '',
                    'uploader': video_details.get('uploader', '') if video_details else '',
                    'platform': 'YouTube',
                    'url': url,
                    'view_count': video_details.get('view_count', 0) or 0 if video_details else 0,
                    'like_count': video_details.get('like_count', 0) or 0 if video_details else 0,
                    'description': video_details.get('description', '') if video_details else '',
                    'has_video': has_video,
                    'has_audio': has_audio,
                    'has_subtitle': has_subtitle,
                    'has_thumbnail': has_thumbnail,
                    'has_info_file': has_info_file
                }
                update_download_summary(save_path, video_data, logger=logger)
                downloaded_urls.add(url)
                print_colored("✅ 已添加到汇总表", Colors.GREEN)
            elif not details.get('has_info_file', False) and details.get('has_video', False):
                # 如果已在汇总表中但信息文件刚生成，更新汇总表
                print_colored("正在更新汇总表...", Colors.CYAN)
                video_details = get_video_details(url)
                download_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                video_data = {
                    'download_time': download_time,
                    'folder_name': folder_name,
                    'title': video_details.get('title', '') if video_details else get_video_title(url) or '',
                    'uploader': video_details.get('uploader', '') if video_details else '',
                    'platform': 'YouTube',
                    'url': url,
                    'view_count': video_details.get('view_count', 0) or 0 if video_details else 0,
                    'like_count': video_details.get('like_count', 0) or 0 if video_details else 0,
                    'description': video_details.get('description', '') if video_details else '',
                    'has_video': details.get('has_video', False),
                    'has_audio': details.get('has_audio', False),
                    'has_subtitle': details.get('has_subtitle', False),
                    'has_thumbnail': details.get('has_thumbnail', False),
                    'has_info_file': details.get('has_info_file', False)
                }
                if update_download_summary(save_path, video_data, update_existing=True, logger=logger):
                    print_colored("✅ 已更新汇总表", Colors.GREEN)
            print()
            continue
        elif is_downloaded == "partial":
            print_colored(f"⚠️  部分文件存在: {status_msg}", Colors.YELLOW)
            print_colored("📋 检测到部分下载，将继续完成缺失的任务...", Colors.CYAN)
            
            subtitle_status = details.get('subtitle_status', {})
            missing_subtitles = details.get('missing_subtitles', [])
            
            # 检查是否需要重新下载字幕
            need_download_subtitles = (
                not subtitle_status.get('has_en_srt', False) or 
                not subtitle_status.get('has_zh_srt', False)
            )
            
            if need_download_subtitles:
                print_colored("📥 检测到字幕文件缺失，正在重新下载字幕...", Colors.CYAN)
                # 重新下载视频（会下载字幕），但使用nooverwrites确保不覆盖视频
                success, stdout, stderr = download_video(url, str(save_path), folder_name, logger=logger)
                if success:
                    print_colored("✅ 字幕下载完成", Colors.GREEN)
                else:
                    print_colored(f"⚠️  字幕下载失败: {stderr[:200] if stderr else '未知错误'}", Colors.YELLOW)
            
            # 检查并转换缺失的字幕文件
            folder_path = details['folder_path']
            srt_files = list(folder_path.glob('*.srt'))
            
            for srt_file in srt_files:
                file_stem = srt_file.stem
                txt_file = folder_path / f"{file_stem}.txt"
                md_file = folder_path / f"{file_stem}.md"
                
                # 如果txt或md文件缺失，进行转换
                if not txt_file.exists() or not md_file.exists():
                    print_colored(f"📝 转换字幕文件: {srt_file.name}", Colors.CYAN)
                    try:
                        if convert_single_srt_to_text(srt_file, folder_path):
                            print_colored(f"  ✅ 已转换: {srt_file.name}", Colors.GREEN)
                        else:
                            print_colored(f"  ⚠️  转换失败: {srt_file.name}", Colors.YELLOW)
                    except Exception as e:
                        print_colored(f"  ❌ 转换出错: {srt_file.name} - {str(e)}", Colors.RED)
            
            # 检查是否需要补充信息文件
            if details.get('has_video', False) and not details.get('has_info_file', False):
                print_colored("📝 检测到信息文件缺失，正在补充...", Colors.CYAN)
                video_details = get_video_details(url, logger=logger)
                info_filename = get_info_filename(url, logger=logger)
                info_file_path = details['folder_path'] / info_filename
                has_info_file = generate_video_info(url, info_file_path)
                if has_info_file:
                    print_colored(f"✅ 信息文件已生成: {info_filename}", Colors.GREEN)
                else:
                    print_colored(f"⚠️  信息文件生成失败", Colors.YELLOW)
            else:
                has_info_file = details.get('has_info_file', False)
            
            # 更新文件状态并重新检查
            has_video, has_audio, has_subtitle, has_thumbnail = check_files_exist(folder_path)
            subtitle_status, _ = check_subtitles_status(folder_path)
            
            # 更新CSV汇总表
            video_details = get_video_details(url, logger=logger)
            download_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            video_data = {
                'download_time': download_time,
                'folder_name': folder_name,
                'title': video_details.get('title', '') if video_details else get_video_title(url) or '',
                'uploader': video_details.get('uploader', '') if video_details else '',
                'platform': 'YouTube',
                'url': url,
                'view_count': video_details.get('view_count', 0) or 0 if video_details else 0,
                'like_count': video_details.get('like_count', 0) or 0 if video_details else 0,
                'description': video_details.get('description', '') if video_details else '',
                'has_video': has_video,
                'has_audio': has_audio,
                'has_subtitle': subtitle_status.get('has_en_srt', False) or subtitle_status.get('has_zh_srt', False),
                'has_thumbnail': has_thumbnail,
                'has_info_file': has_info_file
            }
            if url in downloaded_urls:
                if update_download_summary(save_path, video_data, update_existing=True, logger=logger):
                    print_colored("✅ 已更新汇总表", Colors.GREEN)
            else:
                if update_download_summary(save_path, video_data, logger=logger):
                    downloaded_urls.add(url)
                    print_colored("✅ 已更新汇总表", Colors.GREEN)
            
            success_count += 1
            print()
            continue
        
        print()
        
        # 获取视频详细信息（用于汇总表，在下载前获取）
        print_colored("正在获取视频信息...", Colors.CYAN)
        video_details = get_video_details(url, logger=logger)
        
        # 下载视频
        print_colored("正在下载视频、音频、字幕、封面图片...", Colors.CYAN)
        success, stdout, stderr = download_video(url, str(save_path), folder_name, logger=logger)
        
        if success:
            print_colored(f"✅ 下载完成 [{current}/{total_count}]: {url}", Colors.GREEN)
            success_count += 1
            
            # 检查文件是否存在
            has_video, has_audio, has_subtitle, has_thumbnail = check_files_exist(folder_path)
            
            # 检查字幕下载状态
            subtitle_status, missing_subtitles = check_subtitles_status(folder_path)
            srt_files = list(folder_path.glob('*.srt'))
            has_en_srt = subtitle_status.get('has_en_srt', False)
            has_zh_srt = subtitle_status.get('has_zh_srt', False)
            
            # 显示字幕下载状态并给出提醒
            print_colored("📝 字幕下载状态:", Colors.CYAN)
            if has_en_srt:
                print_colored("  ✅ 英文字幕已下载", Colors.GREEN)
            else:
                print_colored("  ⚠️  英文字幕未下载", Colors.YELLOW)
            
            if has_zh_srt:
                print_colored("  ✅ 简体中文字幕已下载", Colors.GREEN)
            else:
                print_colored("  ⚠️  简体中文字幕未下载（视频可能没有中文字幕或字幕下载失败）", Colors.YELLOW)
            
            if not has_en_srt and not has_zh_srt:
                print_colored("  ❌ 警告: 未检测到任何字幕文件", Colors.RED)
            
            # 生成视频信息文件
            info_filename = get_info_filename(url, logger=logger)
            info_file_path = folder_path / info_filename
            
            print_colored(f"正在生成视频信息文件: {info_filename}", Colors.CYAN)
            has_info_file = generate_video_info(url, info_file_path)
            if has_info_file:
                print_colored(f"✅ 视频信息已生成: {info_file_path}", Colors.GREEN)
            else:
                print_colored(f"⚠️  视频信息生成失败", Colors.YELLOW)
            
            # 默认自动转换字幕文件（不再需要 -c 参数）
            if srt_files:
                print_colored("📝 正在转换字幕文件...", Colors.CYAN)
                converted_count = 0
                skipped_count = 0
                for srt_file in srt_files:
                    file_stem = srt_file.stem
                    txt_file = folder_path / f"{file_stem}.txt"
                    md_file = folder_path / f"{file_stem}.md"
                    
                    # 识别语言
                    lang_info = ""
                    if '.en.' in srt_file.name or srt_file.name.endswith('.en.srt'):
                        lang_info = " (英文)"
                    elif '.zh-Hans.' in srt_file.name or srt_file.name.endswith('.zh-Hans.srt'):
                        lang_info = " (简体中文)"
                    
                    # 如果txt或md文件缺失，进行转换
                    if not txt_file.exists() or not md_file.exists():
                        try:
                            if convert_single_srt_to_text(srt_file, folder_path):
                                print_colored(f"  ✅ 已转换: {srt_file.name}{lang_info}", Colors.GREEN)
                                converted_count += 1
                            else:
                                print_colored(f"  ⚠️  转换失败: {srt_file.name}{lang_info}", Colors.YELLOW)
                        except Exception as e:
                            print_colored(f"  ❌ 转换出错: {srt_file.name}{lang_info} - {str(e)}", Colors.RED)
                    else:
                        print_colored(f"  ⏭️  已存在: {srt_file.name}{lang_info}", Colors.CYAN)
                        skipped_count += 1
                
                if converted_count > 0:
                    print_colored(f"✅ 已转换 {converted_count} 个字幕文件", Colors.GREEN)
                if skipped_count > 0:
                    print_colored(f"⏭️  跳过 {skipped_count} 个已转换的字幕文件", Colors.CYAN)
            else:
                print_colored("⚠️  未找到字幕文件，跳过转换", Colors.YELLOW)
            
            # 更新下载汇总CSV
            download_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            video_data = {
                'download_time': download_time,
                'folder_name': folder_name,
                'title': video_details.get('title', '') if video_details else get_video_title(url) or '',
                'uploader': video_details.get('uploader', '') if video_details else '',
                'platform': 'YouTube',
                'url': url,
                'view_count': video_details.get('view_count', 0) or 0 if video_details else 0,
                'like_count': video_details.get('like_count', 0) or 0 if video_details else 0,
                'description': video_details.get('description', '') if video_details else '',
                'has_video': has_video,
                'has_audio': has_audio,
                'has_subtitle': has_en_srt or has_zh_srt,  # 使用实际检查的字幕状态
                'has_thumbnail': has_thumbnail,
                'has_info_file': has_info_file
            }
            
            if update_download_summary(save_path, video_data, logger=logger):
                print_colored(f"✅ 已更新下载汇总表", Colors.GREEN)
            else:
                print_colored(f"⚠️  更新汇总表失败", Colors.YELLOW)
        else:
            print_colored(f"❌ 下载失败 [{current}/{total_count}]: {url}", Colors.RED)
            if stderr:
                print_colored(f"错误信息: {stderr[:200]}", Colors.RED)
            failed_count += 1
            
            # 即使下载失败，也尝试记录到汇总表（标记为失败）
            download_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            video_data = {
                'download_time': download_time,
                'folder_name': folder_name,
                'title': get_video_title(url, logger=logger) or '',
                'uploader': video_details.get('uploader', '') if video_details else '',
                'platform': 'YouTube',
                'url': url,
                'view_count': video_details.get('view_count', 0) or 0 if video_details else 0,
                'like_count': video_details.get('like_count', 0) or 0 if video_details else 0,
                'description': video_details.get('description', '') if video_details else '',
                'has_video': False,
                'has_audio': False,
                'has_subtitle': False,
                'has_thumbnail': False,
                'has_info_file': False
            }
            update_download_summary(save_path, video_data, logger=logger)
        
        print()
    
    # 显示最终统计
    print_colored("=" * 60, Colors.CYAN)
    print_colored("🎉 所有任务已处理完毕！", Colors.GREEN)
    print_colored(f"共处理: {total_count} 个视频", Colors.BLUE)
    print_colored(f"成功下载: {success_count} 个", Colors.GREEN)
    print_colored(f"跳过（已存在）: {skipped_count} 个", Colors.YELLOW)
    print_colored(f"失败: {failed_count} 个", Colors.RED if failed_count > 0 else Colors.GREEN)
    print_colored("=" * 60, Colors.CYAN)
    
    # 根据参数决定是否转换所有文件夹的字幕
    # 默认情况下（不传 -a 参数），只转换当前下载任务的字幕，不处理全部文件夹
    if args.convert_all_subtitles:
        # 在所有下载任务完成后，再次检查并转换所有缺失的字幕文件（作为补充）
        # 这样可以确保即使某些视频在下载时转换失败，也能在最后统一处理
        print()
        print_colored("=" * 60, Colors.CYAN)
        print_colored("📝 检查并转换所有缺失的字幕文件", Colors.GREEN)
        print_colored("=" * 60, Colors.CYAN)
        
        convert_subtitles_in_download_dir(save_path, logger)
        
        print_colored("=" * 60, Colors.CYAN)
        print_colored("✅ 字幕转换任务完成", Colors.GREEN)
        print_colored("=" * 60, Colors.CYAN)

if __name__ == '__main__':
    main()

