#!/bin/bash

# 获取YouTube频道前100个播放量最高视频的示例脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/get_top_videos.py"

# 颜色定义
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${CYAN}========================================${NC}"
echo -e "${GREEN}YouTube 频道视频获取工具${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# 检查Python脚本是否存在
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo -e "${RED}错误: 找不到脚本 $PYTHON_SCRIPT${NC}"
    exit 1
fi

# 使用示例
echo -e "${YELLOW}使用方法:${NC}"
echo -e "${CYAN}  python3 get_top_videos.py <频道URL或@用户名> [选项]${NC}"
echo ""
echo -e "${YELLOW}示例:${NC}"
echo -e "${CYAN}  # 获取Dan Koe频道前100个视频${NC}"
echo -e "${CYAN}  python3 get_top_videos.py @DanKoeTalks${NC}"
echo ""
echo -e "${CYAN}  # 获取前50个视频${NC}"
echo -e "${CYAN}  python3 get_top_videos.py @DanKoeTalks -n 50${NC}"
echo ""
echo -e "${CYAN}  # 指定输出文件${NC}"
echo -e "${CYAN}  python3 get_top_videos.py @DanKoeTalks -o my_videos.csv${NC}"
echo ""
echo -e "${YELLOW}支持的URL格式:${NC}"
echo -e "  - @用户名 (例如: @DanKoeTalks)"
echo -e "  - 完整URL (例如: https://www.youtube.com/@DanKoeTalks)"
echo -e "  - 频道ID (例如: UCxxxxx...)"
echo ""

# 如果提供了参数，直接运行
if [ $# -gt 0 ]; then
    python3 "$PYTHON_SCRIPT" "$@"
else
    echo -e "${YELLOW}请输入YouTube频道URL或@用户名:${NC}"
    read -p "> " channel_input
    
    if [ -z "$channel_input" ]; then
        echo "未输入，退出"
        exit 0
    fi
    
    echo ""
    echo -e "${GREEN}开始获取视频...${NC}"
    echo ""
    python3 "$PYTHON_SCRIPT" "$channel_input"
fi

