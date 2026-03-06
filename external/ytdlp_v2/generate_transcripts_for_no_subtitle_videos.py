#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为无字幕视频生成完整稿件
使用 Whisper 进行语音识别，生成字幕文件

功能：
1. 读取CSV文件，找出没有字幕的视频
2. 下载这些视频的音频（使用 yt-dlp 只下载音频）
3. 使用 Whisper 进行语音识别
4. 生成字幕文件（SRT格式）
5. 转换为文本和Markdown格式
"""

import re
import csv
import sys
import subprocess
import shutil
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import yt_dlp
import yt_dlp.utils
from config import (
    OUTPUT_DIR_ROOT, get_output_path_for_channel, extract_channel_name_from_url,
    YT_DLP_DEFAULT_OPTS
)
from logger_utils import setup_logger, get_log_file_name
from convert_subtitles_to_text import convert_single_srt_to_text, copy_srt_to_txt_source
from safety_utils import get_ydl_opts

# Whisper 配置
WHISPER_MODEL = "large-v3"  # 可选: tiny, base, small, medium, large, large-v2, large-v3
WHISPER_DEVICE = "cuda"  # 可选: cuda, cpu
WHISPER_COMPUTE_TYPE = "float16"  # 可选: float16, int8, int8_float16
WHISPER_LANGUAGE = "zh"  # 可选: zh, en, auto (自动检测)

# 音频下载配置
AUDIO_FORMAT = "bestaudio/best"  # 下载最佳音频质量
AUDIO_EXT = "m4a"  # 音频文件扩展名

# 颜色输出
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    MAGENTA = '\033[0;35m'
    NC = '\033[0m'

def print_colored(text, color=Colors.NC, end='\n'):
    """打印彩色文本"""
    print(f"{color}{text}{Colors.NC}", end=end)

def check_whisper_available() -> bool:
    """检查 Whisper 是否可用"""
    whisper_path = Path(__file__).parent.parent / ".conda" / "bin" / "whisper-ctranslate2"
    if whisper_path.exists():
        return True
    
    # 尝试在 PATH 中查找
    if shutil.which("whisper-ctranslate2"):
        return True
    
    return False

def get_whisper_command() -> str:
    """获取 Whisper 命令路径"""
    whisper_path = Path(__file__).parent.parent / ".conda" / "bin" / "whisper-ctranslate2"
    if whisper_path.exists():
        return str(whisper_path)
    
    # 尝试在 PATH 中查找
    which_result = shutil.which("whisper-ctranslate2")
    if which_result:
        return which_result
    
    raise FileNotFoundError("找不到 whisper-ctranslate2 命令")

def download_audio_only(url: str, output_path: Path, video_title: str, logger=None, max_retries=3) -> Optional[Path]:
    """只下载音频文件
    
    Args:
        url: 视频URL
        output_path: 输出目录
        video_title: 视频标题（用于文件名）
        logger: 日志记录器
        max_retries: 最大重试次数
    
    Returns:
        音频文件路径，如果失败返回 None
    """
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 清理文件名，移除非法字符
    safe_title = re.sub(r'[<>:"/\\|?*]', '_', video_title)
    safe_title = safe_title[:100]  # 限制文件名长度
    
    for attempt in range(max_retries):
        try:
            # 使用更兼容的配置来避免403错误
            ydl_opts = get_ydl_opts(YT_DLP_DEFAULT_OPTS)
            ydl_opts.update({
                'format': AUDIO_FORMAT,
                'outtmpl': str(output_path / f'{safe_title}.%(ext)s'),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'm4a',
                    'preferredquality': '192',
                }],
                'quiet': False,
                'no_warnings': False,
                # 添加更多选项来避免403错误
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android', 'web'],  # 尝试使用android客户端
                    }
                },
                'http_chunk_size': 10485760,  # 10MB chunks
                'retries': 3,
                'fragment_retries': 3,
                'ignoreerrors': False,
                'no_check_certificate': False,
                # 添加延迟避免速率限制
                'sleep_interval': 1,
                'max_sleep_interval': 5,
            })
            
            if logger:
                if attempt > 0:
                    logger.info(f"开始下载音频（重试 {attempt}/{max_retries-1}）: {url} -> {output_path}")
                else:
                    logger.info(f"开始下载音频: {url} -> {output_path}")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        
            # 查找生成的音频文件
            audio_files = list(output_path.glob(f'{safe_title}*.m4a'))
            if not audio_files:
                # 尝试其他格式
                for ext in ['mp3', 'opus', 'ogg', 'wav']:
                    audio_files = list(output_path.glob(f'{safe_title}*.{ext}'))
                    if audio_files:
                        break
            
            if audio_files:
                audio_file = audio_files[0]
                if logger:
                    logger.info(f"音频下载完成: {audio_file}")
                return audio_file
            else:
                if logger:
                    logger.warning(f"未找到下载的音频文件: {output_path}")
                return None
                
        except yt_dlp.utils.DownloadError as e:
            error_str = str(e).lower()
            is_403 = '403' in error_str or 'forbidden' in error_str
            is_429 = '429' in error_str or 'too many requests' in error_str
            
            if attempt < max_retries - 1:
                if is_403:
                    wait_time = 10 * (attempt + 1)  # 403错误等待更长时间
                    if logger:
                        logger.warning(f"⚠️  遇到403错误，等待 {wait_time} 秒后重试 ({attempt + 1}/{max_retries-1})")
                    time.sleep(wait_time)
                    continue
                elif is_429:
                    wait_time = 30 * (attempt + 1)  # 429错误等待更长时间
                    if logger:
                        logger.warning(f"⚠️  遇到速率限制，等待 {wait_time} 秒后重试 ({attempt + 1}/{max_retries-1})")
                    time.sleep(wait_time)
                    continue
                else:
                    wait_time = 5 * (attempt + 1)
                    if logger:
                        logger.warning(f"⚠️  下载失败，等待 {wait_time} 秒后重试 ({attempt + 1}/{max_retries-1}): {str(e)[:100]}")
                    time.sleep(wait_time)
                    continue
            else:
                # 最后一次尝试也失败了
                if logger:
                    logger.error(f"音频下载失败（已重试 {max_retries} 次）: {url} - {str(e)[:200]}")
                return None
                
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 5 * (attempt + 1)
                if logger:
                    logger.warning(f"⚠️  下载异常，等待 {wait_time} 秒后重试 ({attempt + 1}/{max_retries-1}): {str(e)[:100]}")
                time.sleep(wait_time)
                continue
            else:
                if logger:
                    logger.error(f"音频下载失败（已重试 {max_retries} 次）: {url} - {str(e)}", exc_info=True)
                return None
    
    # 所有重试都失败了
    return None

def transcribe_audio_with_whisper(
    audio_path: Path,
    output_path: Path,
    video_title: str,
    logger=None
) -> Optional[Path]:
    """使用 Whisper 转录音频文件
    
    Args:
        audio_path: 音频文件路径
        output_path: 输出目录（字幕文件保存位置）
        video_title: 视频标题（用于文件名）
        logger: 日志记录器
    
    Returns:
        生成的SRT文件路径，如果失败返回 None
    """
    try:
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 清理文件名
        safe_title = re.sub(r'[<>:"/\\|?*]', '_', video_title)
        safe_title = safe_title[:100]
        
        # 生成输出文件名（SRT格式）
        srt_filename = f"{safe_title}.srt"
        srt_path = output_path / srt_filename
        
        # 如果已存在，跳过
        if srt_path.exists():
            if logger:
                logger.info(f"字幕文件已存在，跳过: {srt_path}")
            return srt_path
        
        # 获取 Whisper 命令
        whisper_cmd = get_whisper_command()
        
        # 构建命令
        # 注意：Whisper会使用音频文件的basename作为输出文件名
        cmd = [
            whisper_cmd,
            str(audio_path),
            '--model', WHISPER_MODEL,
            '--device', WHISPER_DEVICE,
            '--compute_type', WHISPER_COMPUTE_TYPE,
            '--output_dir', str(output_path),
            '--output_format', 'srt',
            '--verbose', 'False',
        ]
        
        # 如果语言不是auto，添加--language参数
        if WHISPER_LANGUAGE.lower() != 'auto':
            cmd.extend(['--language', WHISPER_LANGUAGE])
        
        if logger:
            logger.info(f"开始转录: {audio_path} -> {srt_path}")
            logger.debug(f"Whisper 命令: {' '.join(cmd)}")
        
        # 设置环境变量（如果需要）
        env = None
        if WHISPER_DEVICE == "cuda":
            conda_lib_path = Path(__file__).parent.parent / ".conda" / "lib" / "python3.10" / "site-packages" / "ctranslate2.libs"
            if conda_lib_path.exists():
                import os
                env = os.environ.copy()
                env['LD_LIBRARY_PATH'] = str(conda_lib_path) + ':' + env.get('LD_LIBRARY_PATH', '')
        
        # 运行 Whisper
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            timeout=3600  # 1小时超时
        )
        
        if result.returncode != 0:
            if logger:
                logger.error(f"Whisper 转录失败: {result.stderr}")
            return None
        
        # Whisper使用音频文件的basename（不含扩展名）作为输出文件名
        audio_basename = audio_path.stem  # 不含扩展名的文件名
        expected_srt_name = f"{audio_basename}.srt"
        expected_srt_path = output_path / expected_srt_name
        
        # 首先尝试预期的文件名（基于音频文件名）
        if expected_srt_path.exists():
            # 如果文件名不同，重命名为我们期望的名称
            if expected_srt_path != srt_path:
                expected_srt_path.rename(srt_path)
            if logger:
                logger.info(f"转录完成: {srt_path}")
            return srt_path
        
        # 查找所有SRT文件（按修改时间排序，取最新的）
        srt_files = list(output_path.glob('*.srt'))
        if srt_files:
            # 使用最新的SRT文件
            srt_file = max(srt_files, key=lambda p: p.stat().st_mtime)
            # 重命名为预期名称
            if srt_file != srt_path:
                srt_file.rename(srt_path)
            if logger:
                logger.info(f"转录完成（重命名）: {srt_path}")
            return srt_path
        
        if logger:
            logger.warning(f"未找到生成的SRT文件: {output_path}")
        return None
        
    except subprocess.TimeoutExpired:
        if logger:
            logger.error(f"Whisper 转录超时: {audio_path}")
        return None
    except Exception as e:
        if logger:
            logger.error(f"Whisper 转录失败: {audio_path} - {str(e)}", exc_info=True)
        return None

def read_csv_videos(csv_path: Path, logger=None) -> List[Dict]:
    """从CSV文件读取视频列表
    
    Returns:
        视频信息列表，每个元素包含 id, title, url 等字段
    """
    videos = []
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:  # 使用 utf-8-sig 处理BOM
            reader = csv.DictReader(f)
            
            # 尝试多种可能的列名（支持中英文）
            for row in reader:
                # 尝试中文列名（get_all_videos.py 生成的CSV使用中文列名）
                video_id = row.get('视频ID', '') or row.get('video_id', '')
                video_title = row.get('视频标题', '') or row.get('title', '')
                video_url = row.get('视频链接', '') or row.get('url', '')
                
                # 如果还是空的，尝试其他可能的列名
                if not video_id:
                    video_id = row.get('id', '') or row.get('ID', '')
                if not video_title:
                    video_title = row.get('标题', '') or row.get('Title', '')
                if not video_url:
                    video_url = row.get('链接', '') or row.get('URL', '') or row.get('Link', '')
                
                if video_id and video_title and video_url:
                    videos.append({
                        'id': video_id,
                        'title': video_title,
                        'url': video_url,
                        'row': row  # 保留原始行数据
                    })
        
        if logger:
            logger.info(f"从CSV读取了 {len(videos)} 个视频")
        
    except Exception as e:
        if logger:
            logger.error(f"读取CSV失败: {csv_path} - {str(e)}", exc_info=True)
    
    return videos

def check_has_subtitle(video_id: str, video_title: str, subtitles_path: Path, logger=None) -> bool:
    """检查视频是否已有字幕文件
    
    Args:
        video_id: 视频ID
        video_title: 视频标题
        subtitles_path: 字幕目录
    
    Returns:
        如果有字幕返回 True，否则返回 False
    """
    if not subtitles_path.exists():
        return False
    
    # 查找包含 video_id 的SRT文件
    srt_files = list(subtitles_path.glob(f'*{video_id}*.srt'))
    if srt_files:
        return True
    
    # 也可以根据标题查找（如果文件名包含标题）
    safe_title = re.sub(r'[<>:"/\\|?*]', '_', video_title[:50])
    srt_files = list(subtitles_path.glob(f'*{safe_title}*.srt'))
    if srt_files:
        return True
    
    return False

def process_video_without_subtitle(
    video: Dict,
    channel_output_path: Path,
    logger=None
) -> Tuple[bool, str]:
    """处理无字幕视频：下载音频 -> 转录 -> 生成字幕
    
    Args:
        video: 视频信息字典
        channel_output_path: 频道输出目录
        logger: 日志记录器
    
    Returns:
        (success, message)
    """
    video_id = video['id']
    video_title = video['title']
    video_url = video['url']
    
    try:
        # 创建临时目录用于下载音频
        temp_audio_dir = channel_output_path / "temp_audio"
        temp_audio_dir.mkdir(parents=True, exist_ok=True)
        
        # 字幕目录
        subtitles_path = channel_output_path / "subtitles"
        subtitles_txt_source_path = channel_output_path / "subtitles_txt_source"
        subtitles_txt_essay_path = channel_output_path / "subtitles_txt_essay"
        subtitles_md_essay_path = channel_output_path / "subtitles_md_essay"
        
        # 步骤1: 下载音频
        if logger:
            logger.info(f"[{video_id}] 步骤1: 下载音频...")
        audio_file = download_audio_only(video_url, temp_audio_dir, video_title, logger=logger)
        
        if not audio_file:
            return False, "音频下载失败"
        
        # 步骤2: 使用 Whisper 转录
        if logger:
            logger.info(f"[{video_id}] 步骤2: 使用 Whisper 转录...")
        srt_file = transcribe_audio_with_whisper(
            audio_file,
            subtitles_path,
            video_title,
            logger=logger
        )
        
        if not srt_file:
            # 清理临时音频文件
            try:
                audio_file.unlink()
            except:
                pass
            return False, "Whisper 转录失败"
        
        # 步骤3: 转换字幕格式
        if logger:
            logger.info(f"[{video_id}] 步骤3: 转换字幕格式...")
        try:
            # 复制到 txt_source
            copy_srt_to_txt_source(srt_file, subtitles_txt_source_path)
            
            # 转换为 txt_essay 和 md_essay
            convert_single_srt_to_text(
                srt_file,
                subtitles_txt_essay_path,
                subtitles_md_essay_path
            )
        except Exception as e:
            if logger:
                logger.warning(f"[{video_id}] 字幕转换失败: {str(e)}")
        
        # 清理临时音频文件
        try:
            audio_file.unlink()
        except:
            pass
        
        return True, "成功生成字幕"
        
    except Exception as e:
        if logger:
            logger.error(f"[{video_id}] 处理失败: {str(e)}", exc_info=True)
        return False, f"处理失败: {str(e)}"

def main():
    """主函数"""
    import argparse
    
    # 在函数开始就声明 global，避免后续使用时出错
    global WHISPER_MODEL, WHISPER_DEVICE, WHISPER_LANGUAGE, WHISPER_COMPUTE_TYPE
    
    parser = argparse.ArgumentParser(
        description='为无字幕视频生成完整稿件（使用 Whisper 语音识别）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 处理指定频道的无字幕视频
  python generate_transcripts_for_no_subtitle_videos.py --channel-url "https://www.youtube.com/@xiaojunpodcast"
  
  # 指定CSV文件
  python generate_transcripts_for_no_subtitle_videos.py --csv /path/to/videos.csv
  
  # 使用CPU模式
  python generate_transcripts_for_no_subtitle_videos.py --channel-url "..." --device cpu
        """
    )
    
    parser.add_argument(
        '--channel-url',
        type=str,
        help='YouTube频道URL（会自动提取频道名称）'
    )
    
    parser.add_argument(
        '--csv',
        type=str,
        help='CSV文件路径（如果指定，将使用此文件而不是自动查找）'
    )
    
    parser.add_argument(
        '--model',
        type=str,
        default=WHISPER_MODEL,
        help=f'Whisper模型（默认: {WHISPER_MODEL}）'
    )
    
    parser.add_argument(
        '--device',
        type=str,
        default=WHISPER_DEVICE,
        choices=['cuda', 'cpu'],
        help=f'计算设备（默认: {WHISPER_DEVICE}）'
    )
    
    parser.add_argument(
        '--language',
        type=str,
        default=WHISPER_LANGUAGE,
        help=f'语言代码（默认: {WHISPER_LANGUAGE}，使用 auto 自动检测）'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        help='限制处理视频数量（用于测试）'
    )
    
    parser.add_argument(
        '--skip-existing',
        action='store_true',
        help='跳过已有字幕的视频'
    )
    
    args = parser.parse_args()
    
    # 检查 Whisper 是否可用
    if not check_whisper_available():
        print_colored("❌ 错误: 找不到 whisper-ctranslate2 命令", Colors.RED)
        print_colored("   请确保已安装 whisper-ctranslate2", Colors.YELLOW)
        sys.exit(1)
    
    # 确定输出路径和CSV文件
    if args.csv:
        csv_path = Path(args.csv)
        if not csv_path.exists():
            print_colored(f"❌ 错误: CSV文件不存在: {csv_path}", Colors.RED)
            sys.exit(1)
        channel_output_path = csv_path.parent
    elif args.channel_url:
        channel_name = extract_channel_name_from_url(args.channel_url)
        if not channel_name:
            print_colored(f"❌ 错误: 无法从URL提取频道名称: {args.channel_url}", Colors.RED)
            sys.exit(1)
        channel_output_path = get_output_path_for_channel(channel_name=channel_name)
        csv_path = channel_output_path / f"{channel_name}_all_videos.csv"
        if not csv_path.exists():
            print_colored(f"❌ 错误: CSV文件不存在: {csv_path}", Colors.RED)
            print_colored(f"   请先运行 get_all_videos.py 生成CSV文件", Colors.YELLOW)
            sys.exit(1)
    else:
        print_colored("❌ 错误: 必须指定 --channel-url 或 --csv", Colors.RED)
        parser.print_help()
        sys.exit(1)
    
    # 设置日志（先设置日志，再更新配置）
    log_file = channel_output_path / "logs" / get_log_file_name('generate_transcripts')
    logger = setup_logger('generate_transcripts', log_file)
    
    # 更新全局配置（global 已在函数开头声明）
    WHISPER_MODEL = args.model
    WHISPER_DEVICE = args.device
    WHISPER_LANGUAGE = args.language
    
    # 如果使用CPU模式，自动调整compute_type为int8
    if args.device == 'cpu' and WHISPER_COMPUTE_TYPE == 'float16':
        WHISPER_COMPUTE_TYPE = 'int8'
        logger.info("检测到CPU模式，自动调整compute_type为int8")
    
    print_colored("=" * 60, Colors.CYAN)
    print_colored("为无字幕视频生成完整稿件", Colors.CYAN)
    print_colored("=" * 60, Colors.CYAN)
    print_colored(f"📁 输出目录: {channel_output_path}", Colors.BLUE)
    print_colored(f"📄 CSV文件: {csv_path}", Colors.BLUE)
    print_colored(f"🤖 Whisper模型: {WHISPER_MODEL}", Colors.BLUE)
    print_colored(f"💻 计算设备: {WHISPER_DEVICE}", Colors.BLUE)
    print_colored(f"🌐 语言: {WHISPER_LANGUAGE}", Colors.BLUE)
    print_colored("=" * 60, Colors.CYAN)
    
    # 读取视频列表
    videos = read_csv_videos(csv_path, logger=logger)
    if not videos:
        print_colored("❌ 未找到视频", Colors.RED)
        sys.exit(1)
    
    # 筛选无字幕视频
    subtitles_path = channel_output_path / "subtitles"
    videos_without_subtitle = []
    
    for video in videos:
        if args.skip_existing:
            if check_has_subtitle(video['id'], video['title'], subtitles_path, logger=logger):
                continue
        
        videos_without_subtitle.append(video)
    
    if not videos_without_subtitle:
        print_colored("✅ 所有视频都有字幕，无需处理", Colors.GREEN)
        sys.exit(0)
    
    print_colored(f"\n📊 找到 {len(videos_without_subtitle)} 个无字幕视频", Colors.YELLOW)
    
    # 限制处理数量
    if args.limit:
        videos_without_subtitle = videos_without_subtitle[:args.limit]
        print_colored(f"⚠️  限制处理数量: {len(videos_without_subtitle)}", Colors.YELLOW)
    
    # 处理视频
    success_count = 0
    fail_count = 0
    
    for i, video in enumerate(videos_without_subtitle, 1):
        video_id = video['id']
        video_title = video['title']
        
        print_colored(f"\n[{i}/{len(videos_without_subtitle)}] 处理: {video_title[:60]}...", Colors.CYAN)
        print_colored(f"   视频ID: {video_id}", Colors.BLUE)
        
        success, message = process_video_without_subtitle(
            video,
            channel_output_path,
            logger=logger
        )
        
        if success:
            success_count += 1
            print_colored(f"   ✅ {message}", Colors.GREEN)
        else:
            fail_count += 1
            print_colored(f"   ❌ {message}", Colors.RED)
    
    # 输出统计
    print_colored("\n" + "=" * 60, Colors.CYAN)
    print_colored("处理完成", Colors.CYAN)
    print_colored("=" * 60, Colors.CYAN)
    print_colored(f"✅ 成功: {success_count}", Colors.GREEN)
    print_colored(f"❌ 失败: {fail_count}", Colors.RED)
    print_colored(f"📊 总计: {len(videos_without_subtitle)}", Colors.BLUE)

if __name__ == "__main__":
    main()
