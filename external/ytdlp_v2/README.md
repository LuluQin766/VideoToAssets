# YouTube 视频工具集使用指南

这是一个基于 `yt-dlp` 的 YouTube 视频处理工具集，提供了完整的视频搜索、下载、信息提取、数据分析和管理的功能。

## 📋 目录

- [功能概览](#功能概览)
- [安装与配置](#安装与配置)
- [安全使用指南](#安全使用指南) ⚠️ **重要**
- [核心脚本](#核心脚本)
- [辅助脚本](#辅助脚本)
- [工具脚本](#工具脚本)
- [配置文件](#配置文件)
- [使用示例](#使用示例)
- [常见问题](#常见问题)

---

## 🎯 功能概览

本工具集提供以下主要功能：

1. **视频搜索与链接获取** - 通过标题搜索 YouTube 视频并获取真实链接
2. **批量下载** - 批量下载视频、音频、字幕和封面图片
3. **信息提取** - 提取视频的详细元数据信息
4. **数据收集** - 获取频道/播放列表的所有视频信息并下载字幕
5. **数据管理** - 更新视频统计数据、检查视频可用性
6. **数据分析** - 筛选、过滤和分析视频数据
7. **统计分析** - 生成详细的视频数据分析报告

---

## 🔧 安装与配置

### 前置要求

- Python 3.7+
- `yt-dlp` Python 库（通过 `pip install yt-dlp` 安装）

### 快速开始

1. **安装依赖**：
   ```bash
   pip install yt-dlp
   ```

2. **配置输出目录**（可选）：
   编辑 `config.py`，修改 `OUTPUT_DIR` 为你的输出目录

3. **开始使用**：
   ```bash
   # 搜索视频
   python3 find_youtube_links.py -t "视频标题"
   
   # 获取频道所有视频
   python3 get_all_videos.py https://www.youtube.com/@channelname
   ```

### 配置文件

所有脚本使用统一的配置文件 `config.py`，主要配置项包括：

- **输出目录**：`/data/user/lulu/aMI_results/ytdlpDownload`
- **并发设置**：默认 5 个线程，最大 20 个
- **重试机制**：自动重试失败的操作，支持指数退避
- **日志配置**：日志级别、文件大小限制等

详细配置请查看 `config.py` 文件。

---

## ⚠️ 安全使用指南

**重要提示**：使用本工具集爬取 YouTube 数据存在风险，请务必阅读安全指南！

### 主要风险

1. **IP 封禁风险**：高频率请求可能导致 IP 被 YouTube 封禁
2. **速率限制**：超过速率限制会收到 429 错误
3. **法律风险**：需遵守 YouTube 服务条款和版权法律

### 已实现的安全措施

✅ **速率控制**：可配置请求间隔和批量处理暂停  
✅ **错误检测**：自动检测速率限制和 IP 封禁错误  
✅ **重试机制**：智能重试，遇到速率限制时自动增加延迟  
✅ **并发控制**：限制并发线程数，防止过度请求  
✅ **日志记录**：详细记录所有操作，便于排查问题  

### 推荐配置

在 `config.py` 中建议设置：

```python
REQUEST_DELAY = 1.0  # 每个请求间隔 1 秒
DEFAULT_MAX_WORKERS = 3  # 使用 3-5 个并发线程
BATCH_PAUSE_INTERVAL = 20  # 每 20 个视频暂停一次
BATCH_PAUSE_DURATION = 10  # 暂停 10 秒
```

### 使用建议

- ✅ 使用较低的并发数（3-5 个线程）
- ✅ 分批处理，每次处理 100-500 个视频
- ✅ 在非高峰时段运行
- ✅ 监控日志，发现异常及时停止
- ❌ 不要一次性爬取大量数据
- ❌ 不要使用过高的并发数（>10）

**详细安全指南请查看 [SAFETY_GUIDE.md](SAFETY_GUIDE.md)**

---

## 📚 核心脚本

### 1. `find_youtube_links.py` - 视频链接搜索工具

**功能**：通过视频标题在 YouTube 中搜索并获取真实链接

**使用方法**：
```bash
python3 find_youtube_links.py [选项]
```

**主要参数**：
- `-t, --title`: 要搜索的视频标题
- `-c, --channel`: 限制搜索范围到特定频道（可选）
- `-o, --output`: 输出文件路径（默认：`add-to-download-list`）
- `-csv, --csv-output`: CSV 输出文件路径（可选）

**示例**：
```bash
# 搜索视频标题
python3 find_youtube_links.py -t "Python 教程"

# 限制在特定频道搜索
python3 find_youtube_links.py -t "机器学习" -c "3Blue1Brown"

# 输出到指定文件
python3 find_youtube_links.py -t "深度学习" -o my_list.txt
```

**输出**：
- 文本文件：包含找到的视频链接（可直接用于批量下载）
- CSV 文件（可选）：包含视频标题、链接、频道等信息

---

### 2. `batch_download.py` - 批量下载工具

**功能**：批量下载 YouTube 视频，包括视频、音频、字幕、封面图片，并生成信息文件

**使用方法**：
```bash
python3 batch_download.py [选项]
```

**主要参数**：
- `-l, --list`: 下载列表文件路径（默认：`todownload_links_DanKoe.txt`）
- `-p, --path`: 下载保存路径（默认：配置的输出目录）

**功能特点**：
- 自动下载视频、音频、字幕和封面图片（**支持同时下载中英文字幕**）
- 自动生成视频信息 Markdown 文件
- 生成 CSV 汇总表，记录所有下载的视频信息
- 支持断点续传（跳过已下载的视频）

**字幕下载说明**：
- 默认同时下载英文和中文（简体/繁体）字幕
- 字幕文件会自动包含语言代码，例如：`视频标题.en.srt`、`视频标题.zh.srt`
- 如果视频没有某个语言的字幕，会自动跳过该语言
- 可在 `config.py` 中修改 `YT_DLP_VIDEO_OPTS` 的 `subtitleslangs` 参数自定义要下载的语言
- 自动检测并补充缺失的文件

**输出结构**：
```
输出目录/
├── 视频标题前10字符/
│   ├── 视频文件.mp4
│   ├── 字幕文件.srt
│   ├── 封面图片.jpg
│   └── 信息文件.md
└── download_summary.csv  # 下载汇总表
```

**示例**：
```bash
# 使用默认列表和路径
python3 batch_download.py

# 指定自定义列表和路径
python3 batch_download.py -l my_list.txt -p /path/to/download
```

---

### 3. `get_all_videos.py` - 完整视频信息收集工具

**功能**：获取 YouTube 频道或播放列表的所有视频，下载字幕，并保存完整信息到 CSV

**使用方法**：
```bash
python3 get_all_videos.py [选项] <URL>
```

**主要参数**：
- `URL`: 频道或播放列表 URL（必需）
- `-o, --output`: 输出 CSV 文件路径（可选）
- `-w, --workers`: 并发线程数（默认：5）
- `--resume`: 启用断点续传
- `--no-subtitles`: 不下载字幕
- `--content-types`: 指定要获取的内容类型（可多选：`videos`, `shorts`, `playlists`, `posts`, `streams`）
- `--all-types`: 获取所有类型的内容（videos, shorts, playlists, posts）

**⚠️ 重要：内容类型说明**

**默认行为**：
- 如果 URL 中没有指定类型（如 `@channelname`），**默认只获取 `videos`（普通视频）**
- 如果 URL 中指定了类型（如 `@channelname/videos` 或 `@channelname/shorts`），则获取该类型

**获取不同类型的内容**：

```bash
# 默认：只获取 videos（普通视频）
python3 get_all_videos.py https://www.youtube.com/@DanKoeTalks

# 获取所有类型的内容（videos + shorts + playlists + posts）
python3 get_all_videos.py --all-types https://www.youtube.com/@DanKoeTalks

# 只获取 videos 和 shorts
python3 get_all_videos.py --content-types videos shorts https://www.youtube.com/@DanKoeTalks

# 只获取 shorts
python3 get_all_videos.py --content-types shorts https://www.youtube.com/@DanKoeTalks

# 获取 videos、shorts 和 playlists
python3 get_all_videos.py --content-types videos shorts playlists https://www.youtube.com/@DanKoeTalks

# 如果 URL 中已指定类型，会自动检测
python3 get_all_videos.py https://www.youtube.com/@DanKoeTalks/shorts  # 只获取 shorts
python3 get_all_videos.py https://www.youtube.com/@DanKoeTalks/videos  # 只获取 videos
```

**功能特点**：
- 支持频道和播放列表 URL
- 支持获取多种内容类型（videos、shorts、playlists、posts）
- 自动下载所有视频的字幕文件（**支持同时下载中英文字幕**）
- 保存完整的视频元数据到 CSV
- 支持断点续传，中断后可继续
- 多线程并发处理，提高效率

**字幕下载说明**：
- 默认同时下载英文和中文（简体/繁体）字幕
- 字幕文件会自动包含语言代码，例如：`视频标题.en.srt`、`视频标题.zh.srt`
- 如果视频没有某个语言的字幕，会自动跳过该语言
- 可在 `config.py` 中修改 `YT_DLP_SUBTITLE_OPTS` 的 `subtitleslangs` 参数自定义要下载的语言
- 自动重试机制，提高成功率
- 自动去重（如果同一视频出现在多个类型中）

**输出结构**：
```
输出目录/
└── 用户名或播放列表名/
    ├── subtitles/
    │   ├── 视频标题_video_id.en.srt      # 英文字幕
    │   ├── 视频标题_video_id.zh.srt      # 中文字幕
    │   ├── 视频标题_video_id.en-US.srt   # 美式英文字幕（如果可用）
    │   └── ...                           # 更多字幕文件
    └── all_videos.csv  # 完整视频信息
```

**CSV 包含字段**：
- 视频ID、标题、链接
- 频道信息、上传者信息
- 上传日期、时长
- 播放量、点赞量、评论数
- 描述、标签、分类
- 分辨率、语言等

**示例**：
```bash
# 获取频道所有视频（默认只获取 videos）
python3 get_all_videos.py https://www.youtube.com/@channelname

# 获取所有类型的内容（videos + shorts + playlists + posts）
python3 get_all_videos.py --all-types https://www.youtube.com/@channelname

# 只获取 videos 和 shorts
python3 get_all_videos.py --content-types videos shorts https://www.youtube.com/@channelname

# 获取播放列表
python3 get_all_videos.py https://www.youtube.com/playlist?list=PLxxx

# 使用断点续传
python3 get_all_videos.py --resume https://www.youtube.com/@channelname

# 自定义并发数和输出文件
python3 get_all_videos.py -w 10 -o my_videos.csv https://www.youtube.com/@channelname

# 组合使用：获取所有类型，使用断点续传，低并发
python3 get_all_videos.py --all-types --resume -w 3 https://www.youtube.com/@channelname
```

---

### 4. `get_top_videos.py` - 热门视频获取工具

**功能**：获取 YouTube 频道播放量最高的 N 个视频

**使用方法**：
```bash
python3 get_top_videos.py [选项] <频道URL>
```

**主要参数**：
- `频道URL`: 频道 URL（必需）
- `-n, --top-n`: 获取数量（默认：100）
- `-o, --output`: 输出 CSV 文件路径（可选）

**示例**：
```bash
# 获取前 50 个热门视频
python3 get_top_videos.py -n 50 https://www.youtube.com/@channelname

# 输出到指定文件
python3 get_top_videos.py -n 20 -o top20.csv https://www.youtube.com/@channelname
```

---

## 🛠️ 工具脚本

### 5. `update_video_stats.py` - 视频统计数据更新工具

**功能**：更新已有 CSV 文件中的视频统计数据（播放量、点赞数、评论数等）

**使用方法**：
```bash
python3 update_video_stats.py [选项] <CSV文件>
```

**主要参数**：
- `CSV文件`: 输入 CSV 文件路径（必需）
- `-o, --output`: 输出 CSV 文件路径（默认：覆盖原文件）
- `-w, --workers`: 并发线程数（默认：5）

**功能特点**：
- 自动创建原文件备份
- 只更新会变化的字段（播放量、点赞数等）
- 多线程并发更新，提高速度

**示例**：
```bash
# 更新 CSV 文件中的统计数据
python3 update_video_stats.py all_videos.csv

# 输出到新文件
python3 update_video_stats.py -o updated_stats.csv all_videos.csv

# 使用更多线程加速
python3 update_video_stats.py -w 10 all_videos.csv
```

---

### 6. `check_videos.py` - 视频可用性检查工具

**功能**：批量检查 CSV 文件中的视频是否仍可用（未被删除、设为私有等）

**使用方法**：
```bash
python3 check_videos.py [选项] <CSV文件>
```

**主要参数**：
- `CSV文件`: 输入 CSV 文件路径（必需）
- `-o, --output`: 输出 CSV 文件路径（默认：覆盖原文件）
- `-w, --workers`: 并发线程数（默认：5）
- `--update-stats`: 同时更新可用视频的统计数据

**功能特点**：
- 检查视频状态：可用、不可用、私有、已删除
- 自动创建原文件备份
- 在 CSV 中添加"视频状态"和"状态说明"列
- 可选更新可用视频的统计数据

**示例**：
```bash
# 检查视频可用性
python3 check_videos.py all_videos.csv

# 同时更新统计数据
python3 check_videos.py --update-stats all_videos.csv

# 输出到新文件
python3 check_videos.py -o checked_videos.csv all_videos.csv
```

---

### 7. `filter_videos.py` - 视频筛选和导出工具

**功能**：根据各种条件筛选 CSV 文件中的视频并导出

**使用方法**：
```bash
python3 filter_videos.py [选项] <CSV文件> <输出文件>
```

**主要参数**：
- `CSV文件`: 输入 CSV 文件路径（必需）
- `输出文件`: 输出 CSV 文件路径（必需）

**筛选条件**：
- `--min-views`: 最小播放量
- `--max-views`: 最大播放量
- `--min-likes`: 最小点赞量
- `--max-likes`: 最大点赞量
- `--min-duration`: 最小时长（秒）
- `--max-duration`: 最大时长（秒）
- `--date-from`: 起始日期（YYYY-MM-DD）
- `--date-to`: 结束日期（YYYY-MM-DD）
- `--year`: 年份（YYYY）
- `--keywords`: 关键词（在标题或描述中搜索，可多次使用）
- `--has-subtitles`: 是否有字幕（True/False）

**示例**：
```bash
# 筛选播放量大于 10000 的视频
python3 filter_videos.py all_videos.csv filtered.csv --min-views 10000

# 筛选 2023 年的视频
python3 filter_videos.py all_videos.csv filtered.csv --year 2023

# 筛选包含特定关键词的视频
python3 filter_videos.py all_videos.csv filtered.csv --keywords "Python" --keywords "教程"

# 组合多个条件
python3 filter_videos.py all_videos.csv filtered.csv \
    --min-views 5000 \
    --min-likes 100 \
    --date-from 2023-01-01 \
    --date-to 2023-12-31 \
    --keywords "机器学习"
```

---

### 8. `analyze_videos.py` - 视频数据分析工具

**功能**：分析 CSV 文件中的视频数据并生成详细的 Markdown 分析报告

**使用方法**：
```bash
python3 analyze_videos.py [选项] <CSV文件>
```

**主要参数**：
- `CSV文件`: 输入 CSV 文件路径（必需）
- `-o, --output`: 输出报告文件路径（默认：`视频分析报告.md`）

**分析内容**：
- 基本统计：总视频数、总播放量、总点赞量、平均值等
- 时间分布：按年份、月份统计视频数量
- 热门视频：播放量、点赞量 Top 10
- 时长分布：视频时长分布统计
- 分类统计：视频分类分布
- 标签分析：最受欢迎的标签
- 语言分布：视频语言统计
- 年度趋势：播放量和点赞量趋势分析
- 视频状态：可用性统计

**示例**：
```bash
# 生成分析报告
python3 analyze_videos.py all_videos.csv

# 输出到指定文件
python3 analyze_videos.py all_videos.csv -o my_analysis.md
```

---

### 9. `generate_video_info.py` - 视频信息生成工具

**功能**：为单个视频生成详细的 Markdown 信息文件

**使用方法**：
```bash
python3 generate_video_info.py <视频URL> <输出文件路径>
```

**示例**：
```bash
python3 generate_video_info.py \
    "https://www.youtube.com/watch?v=xxx" \
    video_info.md
```

**输出内容**：
- 视频基本信息（标题、上传者、上传日期等）
- 统计数据（播放量、点赞量、评论数等）
- 视频详情（时长、分辨率、语言等）
- 描述、标签、分类
- 缩略图链接等

---

## 🔧 辅助脚本

### Shell 包装脚本

#### `batch_download.sh`
批量下载的 Shell 包装脚本，方便快速调用。

**使用方法**：
```bash
./batch_download.sh [选项]
```

#### `get_top_videos_example.sh`
获取热门视频的示例脚本，包含使用示例。

**使用方法**：
```bash
./get_top_videos_example.sh
```

#### `quick_find_links.sh`
快速查找链接的 Shell 脚本。

**使用方法**：
```bash
./quick_find_links.sh "视频标题"
```

### 工具模块

#### `logger_utils.py`
日志工具模块，提供统一的日志设置功能。所有脚本自动使用此模块进行日志记录。

#### `config.py`
统一配置文件，包含所有脚本的配置项。修改此文件可以调整所有脚本的行为。

---

## ⚙️ 配置文件

### `config.py` - 统一配置文件

所有脚本的配置都集中在这个文件中，包括：

**路径配置**：
- `OUTPUT_DIR`: 输出目录
- `DOWNLOAD_LIST_PATH`: 默认下载列表路径
- `CSV_SUMMARY_PATH`: CSV 汇总文件路径

**重试配置**：
- `GET_INFO_MAX_RETRIES`: 获取信息最大重试次数
- `DOWNLOAD_SUBTITLE_MAX_RETRIES`: 下载字幕最大重试次数
- `DOWNLOAD_VIDEO_MAX_RETRIES`: 下载视频最大重试次数

**并发配置**：
- `DEFAULT_MAX_WORKERS`: 默认并发线程数
- `MAX_WORKERS_LIMIT`: 最大并发线程数限制

**超时配置**：
- `GET_INFO_TIMEOUT`: 获取信息超时时间
- `DOWNLOAD_SUBTITLE_TIMEOUT`: 下载字幕超时时间
- `DOWNLOAD_VIDEO_TIMEOUT`: 下载视频超时时间

**日志配置**：
- `LOG_LEVEL`: 日志级别
- `LOG_MAX_SIZE_MB`: 日志文件最大大小
- `LOG_BACKUP_COUNT`: 日志备份数量

---

## 📖 使用示例

### 完整工作流程示例

#### 示例 1：收集频道所有视频并分析

```bash
# 1. 获取频道所有视频
python3 get_all_videos.py https://www.youtube.com/@channelname

# 2. 生成分析报告
python3 analyze_videos.py output/channelname/all_videos.csv

# 3. 筛选热门视频（播放量 > 10000）
python3 filter_videos.py \
    output/channelname/all_videos.csv \
    output/channelname/popular_videos.csv \
    --min-views 10000

# 4. 更新统计数据
python3 update_video_stats.py output/channelname/all_videos.csv

# 5. 检查视频可用性
python3 check_videos.py output/channelname/all_videos.csv
```

#### 示例 2：搜索并批量下载视频

```bash
# 1. 搜索视频并生成下载列表
python3 find_youtube_links.py -t "Python 教程" -o my_list.txt

# 2. 批量下载
python3 batch_download.py -l my_list.txt
```

#### 示例 3：获取热门视频并筛选

```bash
# 1. 获取前 50 个热门视频
python3 get_top_videos.py -n 50 https://www.youtube.com/@channelname

# 2. 筛选 2023 年的视频
python3 filter_videos.py \
    top_videos.csv \
    top_videos_2023.csv \
    --year 2023
```

---

## 🔍 常见问题

### Q1: 如何修改输出目录？

A: 输出目录现在会根据频道名称自动设置，无需手动修改。

**自动模式（推荐）**：
- 使用 `get_all_videos.py` 时，程序会自动从URL中提取频道名称
- 例如：`https://www.youtube.com/@channelname` 会自动创建 `/data/user/lulu/aMI_results/ytdlpDownload02/channelname/` 目录
- 支持的URL格式：
  - `https://www.youtube.com/@channelname`
  - `https://www.youtube.com/@channelname/videos`
  - `https://www.youtube.com/c/channelname`
  - `https://www.youtube.com/channel/UCxxxxx`
  - `https://www.youtube.com/user/username`

**手动配置（向后兼容）**：
- 如果需要使用固定的默认目录，可以编辑 `config.py` 文件，修改 `DEFAULT_CHANNEL_NAME` 变量
- 默认输出目录：`{OUTPUT_DIR_ROOT}/{DEFAULT_CHANNEL_NAME}`

**编程方式**：
```python
from config import get_output_path_for_channel

# 从URL自动提取频道名称并获取输出路径
output_path = get_output_path_for_channel(url="https://www.youtube.com/@channelname")

# 或直接指定频道名称
output_path = get_output_path_for_channel(channel_name="channelname")
```

### Q2: 下载速度很慢怎么办？

A: 可以增加并发线程数，使用 `-w` 参数，例如：
```bash
python3 get_all_videos.py -w 10 <URL>
```
注意：不要设置过大，建议 3-10 之间。

### Q3: 脚本中断后如何继续？

A: 使用 `--resume` 参数（适用于 `get_all_videos.py`），或直接重新运行（`batch_download.py` 会自动跳过已下载的文件）。

### Q4: 如何查看日志？

A: 日志文件保存在输出目录的 `logs` 文件夹中，文件名包含脚本名称和时间戳。

### Q5: 如何处理网络错误？

A: 所有脚本都内置了自动重试机制，会在失败时自动重试。如果仍然失败，请检查网络连接或稍后重试。

### Q6: CSV 文件格式是什么？

A: CSV 文件使用 UTF-8 编码，包含视频的完整元数据信息。可以使用 Excel、Google Sheets 等工具打开查看。

---

## 📝 注意事项

1. **API 限制**：YouTube 可能会限制请求频率，建议合理设置并发数
2. **网络稳定性**：确保网络连接稳定，脚本会自动重试失败的操作
3. **存储空间**：批量下载会占用大量存储空间，请确保有足够的磁盘空间
4. **版权问题**：请遵守 YouTube 的使用条款和版权法律
5. **配置备份**：修改 `config.py` 前建议先备份

---

## 🚀 高级功能

### 断点续传

`get_all_videos.py` 支持断点续传功能：
- 使用 `--resume` 参数启用
- 自动保存进度到 JSON 文件
- 中断后重新运行会自动从上次停止的地方继续

### 多线程并发

多个脚本支持多线程并发处理：
- `get_all_videos.py`: 使用 `-w` 参数设置线程数
- `update_video_stats.py`: 使用 `-w` 参数设置线程数
- `check_videos.py`: 使用 `-w` 参数设置线程数

### 日志系统

所有脚本都集成了日志系统：
- 日志文件保存在 `logs` 目录
- 自动日志轮转（按大小和数量）
- 同时输出到控制台和文件

---

## 📄 许可证

本工具集基于 `yt-dlp` 开发，请遵守相关许可证要求。

---

## 🤝 贡献

如有问题或建议，欢迎提出 Issue 或 Pull Request。

---

**最后更新**：2024年

