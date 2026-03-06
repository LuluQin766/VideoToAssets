#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 Markdown 文件中提取纯中文内容
支持处理中英文混合的 markdown 文件，提取出纯中文版本
"""

import re
import sys
from pathlib import Path


def is_chinese_char(char: str) -> bool:
    """
    判断字符是否为中文字符（包括中文标点符号）
    
    Args:
        char: 单个字符
        
    Returns:
        是否为中文字符
    """
    # 中文字符的 Unicode 范围
    # \u4e00-\u9fff: CJK统一汉字
    # \u3000-\u303f: CJK符号和标点
    # \uff00-\uffef: 全角字符（包括中文标点）
    # \u3400-\u4dbf: CJK扩展A
    # \u20000-\u2a6df: CJK扩展B
    # \u2a700-\u2b73f: CJK扩展C
    # \u2b740-\u2b81f: CJK扩展D
    # \u2b820-\u2ceaf: CJK扩展E
    # \uf900-\ufaff: CJK兼容汉字
    # \u3300-\u33ff: CJK兼容
    # \ufe30-\ufe4f: CJK兼容形式
    # \u2e80-\u2eff: CJK部首补充
    # \u2f00-\u2fdf: 康熙部首
    # \u31c0-\u31ef: CJK笔画
    # \u3200-\u32ff: 带圈或带括号的CJK字母和月份
    # \u3000: 全角空格
    
    code = ord(char)
    return (
        (0x4e00 <= code <= 0x9fff) or      # CJK统一汉字
        (0x3000 <= code <= 0x303f) or      # CJK符号和标点
        (0xff00 <= code <= 0xffef) or      # 全角字符
        (0x3400 <= code <= 0x4dbf) or      # CJK扩展A
        (0xf900 <= code <= 0xfaff) or      # CJK兼容汉字
        (0x3300 <= code <= 0x33ff) or      # CJK兼容
        (0xfe30 <= code <= 0xfe4f) or      # CJK兼容形式
        (0x2e80 <= code <= 0x2eff) or      # CJK部首补充
        (0x2f00 <= code <= 0x2fdf) or      # 康熙部首
        (0x31c0 <= code <= 0x31ef) or      # CJK笔画
        (0x3200 <= code <= 0x32ff) or      # 带圈或带括号的CJK字母和月份
        code == 0x3000                      # 全角空格
    )


def extract_chinese_from_markdown(content: str) -> str:
    """
    从 markdown 内容中提取纯中文，保留 markdown 结构
    
    Args:
        content: markdown 文件内容
        
    Returns:
        提取的纯中文 markdown 内容
    """
    lines = content.split('\n')
    result_lines = []
    
    for line in lines:
        stripped_line = line.strip()
        
        # 检查是否是 markdown 标题
        if stripped_line.startswith('#'):
            # 提取标题标记（# 号）和缩进
            leading_spaces = len(line) - len(line.lstrip())
            marker = ''
            i = 0
            
            # 提取标题标记（# 号）
            while i < len(stripped_line) and stripped_line[i] == '#':
                marker += stripped_line[i]
                i += 1
            
            # 跳过空格
            while i < len(stripped_line) and stripped_line[i] == ' ':
                i += 1
            
            # 提取中文内容
            chinese_content = ''
            for char in stripped_line[i:]:
                if is_chinese_char(char) or char == ' ':
                    chinese_content += char
            
            chinese_content = chinese_content.strip()
            if chinese_content:
                result_lines.append(' ' * leading_spaces + marker + ' ' + chinese_content)
        
        # 检查是否是列表项（- 或 * 开头）
        elif stripped_line.startswith('-') or stripped_line.startswith('*'):
            # 提取缩进和标记
            leading_spaces = len(line) - len(line.lstrip())
            marker = stripped_line[0]  # - 或 *
            rest = stripped_line[1:].strip()
            
            # 提取中文内容
            chinese_parts = []
            for char in rest:
                if is_chinese_char(char) or char == ' ':
                    chinese_parts.append(char)
            
            chinese_content = ''.join(chinese_parts).strip()
            if chinese_content:
                result_lines.append(' ' * leading_spaces + marker + ' ' + chinese_content)
        
        # 检查是否是数字列表项（如 "1. " 或 "1) "）
        elif re.match(r'^\s*\d+[\.\)]\s+', stripped_line):
            # 提取缩进和数字标记
            leading_spaces = len(line) - len(line.lstrip())
            match = re.match(r'^(\d+[\.\)])\s+', stripped_line)
            if match:
                marker = match.group(1)
                rest = stripped_line[match.end():]
                
                # 提取中文内容
                chinese_parts = []
                for char in rest:
                    if is_chinese_char(char) or char == ' ':
                        chinese_parts.append(char)
                
                chinese_content = ''.join(chinese_parts).strip()
                if chinese_content:
                    result_lines.append(' ' * leading_spaces + marker + ' ' + chinese_content)
        
        # 普通文本行
        else:
            # 提取中文内容
            chinese_parts = []
            for char in line:
                if is_chinese_char(char) or char in [' ', '\t']:
                    chinese_parts.append(char)
            
            chinese_line = ''.join(chinese_parts).strip()
            if chinese_line:
                result_lines.append(chinese_line)
            elif not stripped_line:  # 保留空行以保持段落结构
                result_lines.append('')
    
    # 合并结果
    result = '\n'.join(result_lines)
    
    # 进一步清理：移除多余的空行（保留最多两个连续换行）
    result = re.sub(r'\n{3,}', '\n\n', result)
    
    return result.strip()


def process_markdown_file(input_file: Path, output_suffix: str = "_纯中文") -> bool:
    """
    处理单个 markdown 文件，提取纯中文内容
    
    Args:
        input_file: 输入文件路径
        output_suffix: 输出文件后缀（添加到原文件名后）
        
    Returns:
        是否处理成功
    """
    if not input_file.exists():
        print(f"错误: 文件不存在 - {input_file}")
        return False
    
    if not input_file.suffix.lower() == '.md':
        print(f"警告: 文件不是 .md 格式 - {input_file}")
    
    try:
        # 读取文件内容
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        try:
            with open(input_file, 'r', encoding='gbk') as f:
                content = f.read()
        except Exception as e:
            print(f"错误: 无法读取文件 {input_file} - {e}")
            return False
    except Exception as e:
        print(f"错误: 读取文件时出错 - {e}")
        return False
    
    # 提取纯中文内容
    chinese_content = extract_chinese_from_markdown(content)
    
    if not chinese_content.strip():
        print(f"警告: 文件 {input_file.name} 中未找到中文内容")
        return False
    
    # 生成输出文件名
    output_file = input_file.parent / f"{input_file.stem}{output_suffix}.md"
    
    try:
        # 写入输出文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(chinese_content)
        
        print(f"✓ 成功处理: {input_file.name}")
        print(f"  输出文件: {output_file.name}")
        print(f"  原文件大小: {len(content)} 字符")
        print(f"  中文内容大小: {len(chinese_content)} 字符")
        return True
    except Exception as e:
        print(f"错误: 写入文件时出错 - {e}")
        return False


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python extract_chinese_only.py <markdown文件路径> [输出后缀]")
        print("示例: python extract_chinese_only.py '/Volumes/UH100/YouTubeDownload202601/ElonMuskon/埃隆·马斯克谈 AGI 时间线.md'")
        print("示例: python extract_chinese_only.py 'file.md' '_中文版'")
        sys.exit(1)
    
    input_path = Path(sys.argv[1])
    output_suffix = sys.argv[2] if len(sys.argv) > 2 else "_纯中文"
    
    print("=" * 60)
    print("Markdown 文件中文提取工具")
    print("=" * 60)
    print(f"输入文件: {input_path}")
    print(f"输出后缀: {output_suffix}")
    print("=" * 60)
    print()
    
    success = process_markdown_file(input_path, output_suffix)
    
    if success:
        print("\n处理完成！")
    else:
        print("\n处理失败！")
        sys.exit(1)


if __name__ == "__main__":
    main()

