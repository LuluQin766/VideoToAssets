#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将 SRT 字幕文件拆分为多个文件
每 N 条字幕条目保存为一个文件，在输出目录下创建子文件夹保存
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple, Optional


class SubtitleEntry:
    """字幕条目类"""
    def __init__(self, index: int, timestamp: str, text: str):
        self.index = index
        self.timestamp = timestamp
        self.text = text
    
    def to_srt_format(self, new_index: int) -> str:
        """转换为 SRT 格式字符串"""
        return f"{new_index}\n{self.timestamp}\n{self.text}\n"


def parse_srt_file(srt_path: Path) -> List[SubtitleEntry]:
    """
    解析 SRT 文件，提取所有字幕条目
    
    Args:
        srt_path: SRT 文件路径
        
    Returns:
        字幕条目列表
    """
    try:
        with open(srt_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        try:
            with open(srt_path, 'r', encoding='gbk') as f:
                content = f.read()
        except:
            with open(srt_path, 'r', encoding='latin-1') as f:
                content = f.read()
    
    entries = []
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
            index = int(line)
            i += 1
            
            # 读取时间戳行
            if i < len(lines):
                timestamp_line = lines[i].strip()
                if '-->' in timestamp_line:
                    timestamp = timestamp_line
                    i += 1
                    
                    # 收集文本行（直到遇到空行或下一个序号）
                    text_lines = []
                    while i < len(lines):
                        text_line = lines[i]
                        stripped_text = text_line.strip()
                        
                        # 遇到空行，结束当前字幕块
                        if not stripped_text:
                            i += 1
                            break
                        
                        # 如果下一行是序号，结束当前字幕块
                        if i + 1 < len(lines):
                            next_line = lines[i + 1].strip()
                            if next_line.isdigit():
                                text_lines.append(text_line.rstrip())
                                break
                        
                        text_lines.append(text_line.rstrip())
                        i += 1
                    
                    if text_lines:
                        text = '\n'.join(text_lines)
                        entries.append(SubtitleEntry(index, timestamp, text))
                else:
                    i += 1
            else:
                i += 1
        else:
            i += 1
    
    return entries


def write_srt_file(entries: List[SubtitleEntry], output_path: Path):
    """
    将字幕条目写入 SRT 文件
    
    Args:
        entries: 字幕条目列表
        output_path: 输出文件路径
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        for i, entry in enumerate(entries, 1):
            f.write(entry.to_srt_format(i))
            if i < len(entries):
                f.write('\n')


def split_srt_file(
    input_file: Path,
    output_dir: Path,
    entries_per_file: int = 50,
    subfolder_name: Optional[str] = None
) -> bool:
    """
    将 SRT 文件拆分为多个文件
    
    Args:
        input_file: 输入 SRT 文件路径
        output_dir: 输出目录路径
        entries_per_file: 每个文件包含的字幕条目数
        subfolder_name: 子文件夹名称（如果为 None，则使用输入文件名）
        
    Returns:
        是否处理成功
    """
    if not input_file.exists():
        print(f"错误: 文件不存在 - {input_file}")
        return False
    
    if not input_file.suffix.lower() == '.srt':
        print(f"警告: 文件不是 .srt 格式 - {input_file}")
    
    print(f"正在解析文件: {input_file.name}")
    
    # 解析 SRT 文件
    entries = parse_srt_file(input_file)
    
    if not entries:
        print(f"错误: 未能从文件中提取任何字幕条目")
        return False
    
    total_entries = len(entries)
    print(f"共找到 {total_entries} 条字幕条目")
    
    # 确定子文件夹名称
    if subfolder_name is None:
        subfolder_name = input_file.stem + "_split"
    
    # 创建子文件夹
    subfolder_path = output_dir / subfolder_name
    subfolder_path.mkdir(parents=True, exist_ok=True)
    print(f"输出目录: {subfolder_path}")
    
    # 计算需要创建的文件数
    num_files = (total_entries + entries_per_file - 1) // entries_per_file
    
    print(f"将拆分为 {num_files} 个文件，每个文件最多 {entries_per_file} 条")
    print()
    
    # 拆分并保存文件
    file_stem = input_file.stem
    success_count = 0
    
    for file_index in range(num_files):
        start_idx = file_index * entries_per_file
        end_idx = min(start_idx + entries_per_file, total_entries)
        
        chunk_entries = entries[start_idx:end_idx]
        
        # 生成输出文件名
        output_filename = f"{file_stem}_part{file_index + 1:03d}.srt"
        output_path = subfolder_path / output_filename
        
        # 写入文件
        try:
            write_srt_file(chunk_entries, output_path)
            success_count += 1
            print(f"✓ 已创建: {output_filename} (条目 {start_idx + 1}-{end_idx})")
        except Exception as e:
            print(f"✗ 错误: 创建 {output_filename} 时出错 - {e}")
    
    print()
    print("=" * 60)
    print(f"处理完成！")
    print(f"  总条目数: {total_entries}")
    print(f"  成功创建: {success_count}/{num_files} 个文件")
    print(f"  输出目录: {subfolder_path}")
    print("=" * 60)
    
    return success_count == num_files


def main():
    """主函数"""
    if len(sys.argv) < 3:
        print("用法: python split_srt_file.py <输入文件路径> <输出目录路径> [每文件条目数] [子文件夹名]")
        print()
        print("参数说明:")
        print("  <输入文件路径>    - 要拆分的 SRT 文件路径（必需）")
        print("  <输出目录路径>    - 输出文件的目录路径（必需）")
        print("  [每文件条目数]    - 每个文件包含的字幕条目数（可选，默认: 50）")
        print("  [子文件夹名]      - 输出子文件夹名称（可选，默认: 输入文件名_split）")
        print()
        print("示例:")
        print("  # 使用默认值（每文件50条）")
        print("  python split_srt_file.py 'file.srt' './output'")
        print()
        print("  # 指定每文件30条")
        print("  python split_srt_file.py 'file.srt' './output' 30")
        print()
        print("  # 指定每文件100条，并自定义子文件夹名")
        print("  python split_srt_file.py 'file.srt' './output' 100 'my_split'")
        print()
        print("  # 实际使用示例")
        print("  python split_srt_file.py '/Volumes/UH100/YouTubeDownload202601/ElonMuskon/Elon_Musk_on_AGI_Timeline_US_vs_China_Job_Markets_Clean_Energy_Humanoid_Robots_220.en.srt' '/Volumes/UH100/YouTubeDownload202601/ElonMuskon/' 50")
        sys.exit(1)
    
    input_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    
    # 解析每文件条目数
    entries_per_file = 50  # 默认值
    if len(sys.argv) > 3:
        try:
            entries_per_file = int(sys.argv[3])
            if entries_per_file <= 0:
                print(f"错误: 每文件条目数必须大于 0，当前值: {entries_per_file}")
                sys.exit(1)
        except ValueError:
            print(f"错误: 每文件条目数必须是整数，当前值: {sys.argv[3]}")
            sys.exit(1)
    
    # 解析子文件夹名
    subfolder_name = sys.argv[4] if len(sys.argv) > 4 else None
    
    print("=" * 60)
    print("SRT 文件拆分工具")
    print("=" * 60)
    print(f"输入文件: {input_path}")
    print(f"输出目录: {output_dir}")
    print(f"每文件条目数: {entries_per_file} 条")
    if subfolder_name:
        print(f"子文件夹名: {subfolder_name}")
    else:
        print(f"子文件夹名: {input_path.stem}_split (自动生成)")
    print("=" * 60)
    print()
    
    success = split_srt_file(input_path, output_dir, entries_per_file, subfolder_name)
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()

