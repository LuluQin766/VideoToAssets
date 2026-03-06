#!/bin/bash

# 单视频处理脚本
# 用法: ./run_single_video.sh "YOUTUBE_URL" "OUTPUT_DIR"

set -e

if [ $# -ne 2 ]; then
    echo "Usage: $0 \"YOUTUBE_URL\" \"OUTPUT_DIR\""
    exit 1
fi

YOUTUBE_URL="$1"
OUTPUT_DIR="$2"

# 创建输出目录
mkdir -p "$OUTPUT_DIR"

# 设置PYTHONPATH以使用本地配置
export PYTHONPATH="/Users/luluqin766/Documents/phd_paper/Luluphdpaper/ytdlp_v2:$PYTHONPATH"

# 运行转录脚本
python3 /Users/luluqin766/Documents/phd_paper/Luluphdpaper/ytdlp_v2/generate_transcripts_for_no_subtitle_videos.py \
    --video-url "$YOUTUBE_URL" \
    --output-dir "$OUTPUT_DIR"

echo "Processing completed for: $YOUTUBE_URL"
echo "Output directory: $OUTPUT_DIR"