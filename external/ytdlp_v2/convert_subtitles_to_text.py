#!/usr/bin/env python3
"""
将字幕文件(.srt)转换为连续的文本文件
支持输出 .md 和 .txt 两种格式
"""

import os
import re
from pathlib import Path
from typing import List


def parse_srt_file(srt_path: Path) -> str:
    """
    解析 SRT 字幕文件，提取文本内容
    
    Args:
        srt_path: SRT 文件路径
        
    Returns:
        提取的文本内容（连续文本）
    """
    try:
        with open(srt_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        # 如果 UTF-8 解码失败，尝试其他编码
        try:
            with open(srt_path, 'r', encoding='gbk') as f:
                content = f.read()
        except:
            with open(srt_path, 'r', encoding='latin-1') as f:
                content = f.read()
    
    # 使用正则表达式提取所有字幕文本
    # SRT 格式：序号\n时间戳 --> 时间戳\n文本（可能多行）\n空行
    # 匹配模式：数字\n时间戳 --> 时间戳\n文本内容（直到空行或下一个数字）
    
    # 方法1：使用正则表达式匹配字幕块
    pattern = r'\d+\s*\n\s*\d{2}:\d{2}:\d{2}[,\d]+\s*-->\s*\d{2}:\d{2}:\d{2}[,\d]+\s*\n(.*?)(?=\n\d+\s*\n|\n*$)'
    matches = re.findall(pattern, content, re.MULTILINE | re.DOTALL)
    
    text_lines = []
    for match in matches:
        # 清理匹配到的文本，移除 HTML 标签和多余空白
        text = match.strip()
        # 移除 HTML 标签（如 <i>, <b> 等）
        text = re.sub(r'<[^>]+>', '', text)
        # 将多行文本合并为单行
        text = re.sub(r'\s+', ' ', text)
        if text:
            text_lines.append(text.strip())
    
    # 如果正则匹配失败，使用逐行解析
    if not text_lines:
        lines = content.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # 跳过空行
            if not line:
                i += 1
                continue
            
            # 检查是否是序号行（纯数字）
            if line.isdigit():
                i += 1
                # 跳过时间戳行
                if i < len(lines) and '-->' in lines[i]:
                    i += 1
                # 收集文本行直到遇到空行或下一个序号
                subtitle_text = []
                while i < len(lines):
                    text_line = lines[i].strip()
                    # 遇到空行，结束当前字幕块
                    if not text_line:
                        break
                    # 如果下一行是序号，结束当前字幕块
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        if next_line.isdigit():
                            subtitle_text.append(text_line)
                            break
                    subtitle_text.append(text_line)
                    i += 1
                
                if subtitle_text:
                    # 移除 HTML 标签
                    combined = ' '.join(subtitle_text)
                    combined = re.sub(r'<[^>]+>', '', combined)
                    combined = re.sub(r'\s+', ' ', combined).strip()
                    if combined:
                        text_lines.append(combined)
            else:
                i += 1
    
    # 合并所有文本
    text = ' '.join(text_lines)
    
    # 最终清理
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    return text


def copy_srt_to_txt_source(srt_file: Path, output_dir: Path):
    """
    直接将 SRT 文件复制并改后缀为 .txt（不做任何内容处理）
    
    Args:
        srt_file: SRT 文件路径
        output_dir: 输出目录路径（subtitles_txt_source）
    
    Returns:
        bool: 是否成功
    """
    try:
        # 创建输出目录
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 提取文件名（不含扩展名），添加 .txt 后缀
        file_stem = srt_file.stem
        txt_file = output_dir / f"{file_stem}.txt"
        
        # 直接复制文件内容（不改动内容，只改后缀）
        import shutil
        shutil.copy2(srt_file, txt_file)
        
        return True
    except Exception as e:
        print(f"  错误: 复制 {srt_file.name} 为 .txt 时出错 - {e}")
        return False


def convert_single_srt_to_text(
    srt_file: Path,
    txt_output_dir: Path,
    md_output_dir: Path
):
    """
    将单个 SRT 文件转换为对应的 .txt 和 .md 文件（去除时间戳等处理）
    
    Args:
        srt_file: SRT 文件路径
        txt_output_dir: TXT 输出目录路径（subtitles_txt_essay）
        md_output_dir: MD 输出目录路径（subtitles_md_essay）
    """
    # 提取文件名（不含扩展名）
    file_stem = srt_file.stem
    
    # 解析字幕文件（去除时间戳等）
    text = parse_srt_file(srt_file)
    
    if not text:
        return False
    
    # 创建输出目录
    txt_output_dir.mkdir(parents=True, exist_ok=True)
    md_output_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成 Markdown 格式
    md_content = f"# {file_stem}\n\n{text}\n"
    
    # 生成纯文本格式
    txt_content = f"{file_stem}\n{'=' * 50}\n{text}\n"
    
    # 保存文件到对应的文件夹
    md_file = md_output_dir / f"{file_stem}.md"
    txt_file = txt_output_dir / f"{file_stem}.txt"
    
    try:
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(txt_content)
        
        return True
    except Exception as e:
        print(f"  错误: 保存 {srt_file.name} 时出错 - {e}")
        return False


def convert_subtitles_to_text(
    subtitles_dir: str,
    output_dir: str,
    output_name: str = "combined_subtitles",
    generate_individual: bool = True
):
    """
    将字幕文件夹中的所有 .srt 文件转换为文本文件
    
    Args:
        subtitles_dir: 字幕文件夹路径
        output_dir: 输出文件夹路径
        output_name: 合并文件的文件名（不含扩展名）
        generate_individual: 是否为每个文件生成单独的 .txt 和 .md 文件
    """
    subtitles_path = Path(subtitles_dir)
    output_path = Path(output_dir)
    
    # 创建输出目录
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 获取所有 .srt 文件
    srt_files = sorted(subtitles_path.glob('*.srt'))
    
    if not srt_files:
        print(f"警告: 在 {subtitles_dir} 中未找到 .srt 文件")
        return
    
    print(f"找到 {len(srt_files)} 个字幕文件")
    
    # 存储所有文本内容（用于合并文件）
    all_texts = []
    file_info = []
    
    # 处理每个字幕文件
    success_count = 0
    for srt_file in srt_files:
        print(f"处理: {srt_file.name}")
        text = parse_srt_file(srt_file)
        
        if text:
            all_texts.append(text)
            # 提取文件名（不含扩展名）作为标题
            file_title = srt_file.stem
            file_info.append({
                'title': file_title,
                'text': text
            })
            
            # 为每个文件生成单独的 .txt 和 .md 文件
            if generate_individual:
                # 注意：convert_subtitles_to_text 函数用于批量转换，使用旧的接口
                # 这里需要创建 txt 和 md 子文件夹
                txt_dir = output_path / 'txt'
                md_dir = output_path / 'md'
                if convert_single_srt_to_text(srt_file, txt_dir, md_dir):
                    success_count += 1
        else:
            print(f"  警告: {srt_file.name} 未提取到文本内容")
    
    if not all_texts:
        print("错误: 未能从任何字幕文件中提取文本")
        return
    
    # 生成合并的 Markdown 格式
    md_content = []
    md_content.append("# 字幕文本合集\n\n")
    md_content.append(f"共包含 {len(file_info)} 个视频的字幕文本\n\n")
    md_content.append("---\n\n")
    
    for i, info in enumerate(file_info, 1):
        md_content.append(f"## {i}. {info['title']}\n\n")
        md_content.append(f"{info['text']}\n\n")
        md_content.append("---\n\n")
    
    # 生成合并的纯文本格式
    txt_content = []
    txt_content.append(f"字幕文本合集\n")
    txt_content.append(f"{'=' * 50}\n")
    txt_content.append(f"共包含 {len(file_info)} 个视频的字幕文本\n\n")
    txt_content.append(f"{'=' * 50}\n\n")
    
    for i, info in enumerate(file_info, 1):
        txt_content.append(f"{i}. {info['title']}\n")
        txt_content.append(f"{'-' * 50}\n")
        txt_content.append(f"{info['text']}\n\n")
    
    # 保存合并文件
    md_file = output_path / f"{output_name}.md"
    txt_file = output_path / f"{output_name}.txt"
    
    try:
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(''.join(md_content))
        print(f"\n✓ 合并 Markdown 文件已保存: {md_file}")
        
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(''.join(txt_content))
        print(f"✓ 合并文本文件已保存: {txt_file}")
        
        if generate_individual:
            print(f"\n✓ 已为 {success_count} 个字幕文件生成单独的 .txt 和 .md 文件")
        
        print(f"\n总共处理了 {len(file_info)} 个字幕文件")
        print(f"输出目录: {output_path}")
        
    except Exception as e:
        print(f"错误: 保存文件时出错 - {e}")


def main():
    """主函数"""
    # 配置路径
    subtitles_dir = "/data/user/lulu/aMI_results/ytdlpDownload/DanKoeTalks/subtitles"
    output_dir = "/data/user/lulu/aMI_results/ytdlpDownload/DanKoeTalks/subtitles_text"
    output_name = "combined_subtitles"
    
    print("=" * 60)
    print("字幕文件转文本工具")
    print("=" * 60)
    print(f"输入目录: {subtitles_dir}")
    print(f"输出目录: {output_dir}")
    print("=" * 60)
    print()
    
    # 同时生成合并文件和单独文件
    convert_subtitles_to_text(subtitles_dir, output_dir, output_name, generate_individual=True)


if __name__ == "__main__":
    main()

