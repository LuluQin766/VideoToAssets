#!/bin/bash

# 快速查找YouTube链接的便捷脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/find_youtube_links.py"
INPUT_FILE="$SCRIPT_DIR/DanKoe_top30.txt"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}========================================${NC}"
echo -e "${GREEN}YouTube 视频链接查找工具${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# 检查文件是否存在
if [ ! -f "$INPUT_FILE" ]; then
    echo -e "${RED}错误: 找不到文件 $INPUT_FILE${NC}"
    exit 1
fi

# 检查Python脚本是否存在
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo -e "${RED}错误: 找不到脚本 $PYTHON_SCRIPT${NC}"
    exit 1
fi

# 默认选择选项3（仅搜索Dan Koe频道），自动模式
echo -e "${GREEN}运行模式: 仅搜索Dan Koe频道，自动添加前3个结果到下载列表，自动更新源文件${NC}"
echo ""
python3 "$PYTHON_SCRIPT" "$INPUT_FILE" -c DanKoeTalks --add-to-download-list -y --csv-output

echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${GREEN}完成！${NC}"
echo -e "${CYAN}========================================${NC}"

