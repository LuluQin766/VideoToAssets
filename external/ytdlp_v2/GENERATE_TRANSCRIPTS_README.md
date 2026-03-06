# 为无字幕视频生成完整稿件

## 功能说明

这个脚本可以自动为没有字幕的YouTube视频生成完整稿件，使用 Whisper 语音识别技术。

### 工作流程

1. **读取CSV文件** - 从 `{channel_name}_all_videos.csv` 读取视频列表
2. **筛选无字幕视频** - 找出没有字幕文件的视频
3. **下载音频** - 使用 yt-dlp 只下载音频文件（节省带宽和存储）
4. **语音识别** - 使用 Whisper 将音频转换为文字
5. **生成字幕** - 生成 SRT 格式的字幕文件
6. **格式转换** - 自动转换为 TXT 和 Markdown 格式

## 使用方法

### 基本用法

```bash
python generate_transcripts_for_no_subtitle_videos.py \
  --channel-url "https://www.youtube.com/@xiaojunpodcast"
```

### 使用CPU模式

```bash
python generate_transcripts_for_no_subtitle_videos.py \
  --channel-url "https://www.youtube.com/@xiaojunpodcast" \
  --device cpu
```

### 限制处理数量（用于测试）

```bash
python generate_transcripts_for_no_subtitle_videos.py \
  --channel-url "https://www.youtube.com/@xiaojunpodcast" \
  --limit 5
```

## 参数说明

- `--channel-url`: YouTube频道URL
- `--csv`: CSV文件路径（可选）
- `--model`: Whisper模型（默认: large-v3）
- `--device`: 计算设备（cuda/cpu，默认: cuda）
- `--language`: 语言代码（默认: zh，可用 auto 自动检测）
- `--limit`: 限制处理数量
- `--skip-existing`: 跳过已有字幕的视频

## 输出文件

处理完成后，字幕文件会保存在：
- `subtitles/` - SRT格式字幕
- `subtitles_txt_source/` - TXT源文件
- `subtitles_txt_essay/` - TXT文章（去除时间戳）
- `subtitles_md_essay/` - Markdown文章
