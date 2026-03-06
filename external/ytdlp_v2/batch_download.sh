#!/bin/bash

# 批量下载YouTube视频 - 轻量级Shell脚本
# 主要逻辑在 batch_download.py 中实现

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/batch_download.py"

# 颜色定义
CYAN='\033[0;36m'
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${CYAN}========================================${NC}"
echo -e "${GREEN}YouTube 视频批量下载工具${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# 检查Python脚本是否存在
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "错误: 找不到脚本 $PYTHON_SCRIPT"
    exit 1
fi

# 运行Python脚本，传递所有参数
# 支持参数：
#   -l, --list: 指定下载列表文件（默认: 配置文件中的 DOWNLOAD_LIST_PATH）
#   -p, --path: 指定下载保存路径（默认: /data/user/lulu/aMI_results/ytdlpDownload）
python3 "$PYTHON_SCRIPT" "$@"
