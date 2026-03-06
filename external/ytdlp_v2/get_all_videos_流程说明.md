# get_all_videos.py 完整流程说明文档

## 📋 目录

1. [程序概述](#程序概述)
2. [整体流程图](#整体流程图)
3. [详细流程说明](#详细流程说明)
4. [关键函数说明](#关键函数说明)
5. [数据流说明](#数据流说明)
6. [输出文件结构](#输出文件结构)
7. [错误处理机制](#错误处理机制)
8. [性能优化策略](#性能优化策略)

---

## 程序概述

`get_all_videos.py` 是一个用于批量获取 YouTube 频道或播放列表所有视频信息的工具。它可以：

- ✅ 获取频道/播放列表的所有视频列表
- ✅ 并发获取每个视频的完整详细信息
- ✅ 下载视频字幕文件（中英文）
- ✅ 可选下载视频文件、封面图片和信息文档
- ✅ 自动转换字幕为 txt 和 md 格式
- ✅ 将所有信息保存到 CSV 文件
- ✅ 支持断点续传
- ✅ 自动进度保存

---

## 整体流程图

```
开始
  │
  ├─→ 1. 初始化阶段
  │   ├─→ 设置日志系统
  │   ├─→ 解析命令行参数
  │   └─→ 加载配置
  │
  ├─→ 2. URL 检测与解析阶段
  │   ├─→ 检测 URL 类型（频道/播放列表）
  │   ├─→ 提取频道名称
  │   └─→ 确定内容类型（videos/shorts/playlists/posts）
  │
  ├─→ 3. 视频列表获取阶段
  │   ├─→ 获取频道/播放列表视频列表
  │   ├─→ 去重处理
  │   └─→ 检查已处理视频（断点续传）
  │
  ├─→ 4. 目录结构创建阶段
  │   ├─→ 创建频道输出目录
  │   ├─→ 创建字幕文件夹（默认创建）
  │   └─→ 创建视频文件夹（可选，默认不创建，需 -d 参数）
  │
  ├─→ 5. 并发处理阶段（多线程）
  │   ├─→ 创建线程池
  │   ├─→ 提交所有视频处理任务
  │   └─→ 并发执行以下操作（每个视频）：
  │       ├─→ 获取视频完整信息（带重试）
  │       ├─→ 提取视频数据
  │       ├─→ 下载字幕文件（默认启用）
  │       ├─→ 下载视频文件（可选，默认关闭，需 -d 参数）
  │       ├─→ 下载封面图片（可选，默认关闭，需 -d 参数）
  │       ├─→ 生成信息文档（可选，默认关闭，需 -d 参数）
  │       └─→ 转换字幕格式（可选，默认关闭，需 -d 参数）
  │
  ├─→ 6. 进度管理阶段
  │   ├─→ 定期保存进度文件
  │   ├─→ 批量处理暂停（避免速率限制）
  │   └─→ 实时显示进度
  │
  ├─→ 7. 数据保存阶段
  │   ├─→ 收集所有视频数据
  │   ├─→ 写入 CSV 文件
  │   └─→ 更新统计信息
  │
  └─→ 结束
```

---

## 详细流程说明

### 阶段 1: 初始化阶段

**位置**: `main()` 函数开始

**步骤**:

1. **设置日志系统**
   ```python
   log_file = get_log_file_name('get_all_videos')
   logger = setup_logger('get_all_videos', log_file)
   ```
   - 创建日志文件：`logs/get_all_videos_YYYYMMDD_HHMMSS.log`
   - 配置日志级别和格式

2. **解析命令行参数**
   - `input_url`: 频道或播放列表 URL（必需）
   - `-o, --output`: 输出 CSV 文件路径（可选）
   - `-r, --resume`: 断点续传模式（可选）
   - `-w, --workers`: 并发线程数（可选，默认 5）
   - `--content-types`: 内容类型列表（可选）
   - `--all-types`: 获取所有类型（可选）
   - `-d, --download-video`: 下载视频文件（可选）

3. **参数验证**
   - 验证并发线程数范围（1-20，推荐 3-10）
   - 验证内容类型参数

---

### 阶段 2: URL 检测与解析阶段

**位置**: `get_all_videos()` 函数开始部分

**步骤**:

1. **检测 URL 类型**
   ```python
   url_type, normalized_url, detected_content_type = detect_url_type(input_url)
   ```
   - 返回：`('channel' | 'playlist', normalized_url, content_type)`
   - 支持的 URL 格式：
     - `https://www.youtube.com/@channelname`
     - `https://www.youtube.com/@channelname/videos`
     - `https://www.youtube.com/c/channelname`
     - `https://www.youtube.com/channel/UCxxxxx`
     - `https://www.youtube.com/playlist?list=xxxxx`

2. **提取频道名称**
   ```python
   channel_name = extract_channel_name_from_url(input_url)
   ```
   - 从 URL 中提取频道标识符
   - 如果无法提取，尝试从第一个视频获取上传者名称

3. **确定内容类型**
   - 如果 URL 中包含 `/videos`、`/shorts` 等，自动检测
   - 如果未指定，默认获取 `videos`
   - 支持的内容类型：`videos`, `shorts`, `playlists`, `posts`, `streams`

---

### 阶段 3: 视频列表获取阶段

**位置**: `get_all_videos()` 函数中间部分

**步骤**:

1. **获取视频列表**

   **如果是播放列表**:
   ```python
   videos = get_playlist_videos(normalized_url, logger=logger)
   ```
   - 使用 `yt-dlp` 的 `extract_flat=True` 快速获取
   - 返回：`[{'id': 'xxx', 'url': 'xxx', 'title': 'xxx'}, ...]`

   **如果是频道**:
   ```python
   for content_type in content_types:
       type_url = extract_channel_url(base_url, content_type)
       type_videos = get_channel_videos(type_url, content_type=content_type, logger=logger)
       all_videos.extend(type_videos)
   ```
   - 遍历所有指定的内容类型
   - 分别获取每种类型的视频列表
   - 合并所有结果

2. **去重处理**
   ```python
   seen_ids = set()
   videos = []
   for video in all_videos:
       if video['id'] not in seen_ids:
           seen_ids.add(video['id'])
           videos.append(video)
   ```
   - 基于视频 ID 去重
   - 避免重复处理同一视频

3. **检查已处理视频（断点续传）**
   ```python
   # 从现有 CSV 文件加载已处理的视频 ID
   csv_ids = load_existing_csv(output_csv)
   processed_ids.update(csv_ids)
   
   # 从进度文件加载（如果启用断点续传）
   if resume:
       progress_ids = load_progress(progress_file)
       processed_ids.update(progress_ids)
   
   # 过滤掉已处理的视频
   videos_to_process = [v for v in videos if v['id'] not in processed_ids]
   ```

---

### 阶段 4: 目录结构创建阶段

**位置**: `get_all_videos()` 函数中间部分

**步骤**:

1. **创建频道输出目录**
   ```python
   user_output_path = get_output_path_for_channel(channel_name=channel_name, url=input_url)
   ```
   - 自动从 URL 提取频道名称
   - 创建目录：`{OUTPUT_DIR_ROOT}/{channel_name}/`
   - 例如：`/data/user/lulu/aMI_results/ytdlpDownload02/channelname/`

2. **创建字幕文件夹**
   ```python
   subtitles_path = user_output_path / 'subtitles'
   subtitles_path.mkdir(parents=True, exist_ok=True)
   ```
   - 路径：`{user_output_path}/subtitles/`

3. **创建视频文件夹（如果启用）**
   ```python
   if download_video_file:
       videos_path = user_output_path / 'videos'
       videos_path.mkdir(parents=True, exist_ok=True)
   ```
   - 路径：`{user_output_path}/videos/`

4. **生成文件路径**
   ```python
   # CSV 文件路径
   output_csv = user_output_path / f"{channel_name}_all_videos.csv"
   
   # 进度文件路径
   progress_file = user_output_path / f"{channel_name}_progress.json"
   ```

---

### 阶段 5: 并发处理阶段（核心阶段）

**位置**: `get_all_videos()` 函数核心部分

**步骤**:

1. **创建线程池**
   ```python
   with ThreadPoolExecutor(max_workers=max_workers) as executor:
       # 提交所有任务
       future_to_video = {
           executor.submit(process_single_video, video, subtitles_path, videos_path, download_video_file, logger): video 
           for video in videos_to_process
       }
   ```
   - 默认并发数：5 个线程
   - 可配置范围：1-20（推荐 3-10）

2. **处理每个视频**（`process_single_video` 函数）

   **步骤 2.1: 获取视频完整信息**
   ```python
   info = get_full_video_info(video_url, logger=logger)
   ```
   - 使用 `@retry_with_backoff` 装饰器，自动重试
   - 最大重试次数：3 次
   - 指数退避策略：1秒 → 2秒 → 4秒
   - 特别处理速率限制错误（429）

   **步骤 2.2: 提取视频数据**
   ```python
   video_data = extract_video_data(info)
   ```
   - 提取 40+ 个字段的信息
   - 包括：标题、时长、播放量、点赞量、描述、标签等

   **步骤 2.3: 下载字幕文件（默认模式）**
   ```python
   if not download_video_file:
       download_subtitles(video_url, subtitles_path, video_id, video_title, logger=logger)
   ```
   - 使用 `YT_DLP_SUBTITLE_OPTS` 配置
   - 下载中英文字幕（`.en.srt`, `.zh-Hans.srt`）
   - 保存到 `subtitles/` 文件夹

   **步骤 2.4: 下载视频文件（可选）**
   ```python
   if download_video_file and videos_path:
       download_video(video_url, videos_path, folder_name, logger=logger)
   ```
   - 使用 `YT_DLP_VIDEO_OPTS` 配置
   - 下载视频、音频、字幕、封面
   - 保存到 `videos/{folder_name}/` 文件夹

   **步骤 2.5: 生成信息文档（可选）**
   ```python
   if download_video_file:
       generate_video_info(video_url, info_file_path, logger=logger)
   ```
   - 调用 `generate_video_info.py` 脚本
   - 生成 Markdown 格式的信息文档
   - 包含视频的完整元数据

   **步骤 2.6: 转换字幕格式（可选）**
   ```python
   if download_video_file:
       for srt_file in srt_files:
           convert_single_srt_to_text(srt_file, video_folder)
   ```
   - 将 `.srt` 转换为 `.txt` 和 `.md`
   - 每个字幕文件生成两个格式

3. **收集处理结果**
   ```python
   for future in as_completed(future_to_video):
       video_data, video_id, video_title, has_subtitle, success, error_msg = future.result()
       
       if success and video_data:
           all_video_data.append(video_data)
           processed_ids.add(video_id)
   ```
   - 使用线程锁保护共享资源
   - 收集成功处理的视频数据

---

### 阶段 6: 进度管理阶段

**位置**: 并发处理循环中

**步骤**:

1. **定期保存进度**
   ```python
   if success_count % PROGRESS_SAVE_INTERVAL == 0:
       save_progress(progress_file, processed_ids)
   ```
   - 每处理 10 个视频保存一次（可配置）
   - 保存到 JSON 文件：`{channel_name}_progress.json`
   - 格式：
     ```json
     {
       "processed_video_ids": ["video_id1", "video_id2", ...],
       "last_update": "2024-01-01 12:00:00",
       "total_processed": 10
     }
     ```

2. **批量处理暂停**
   ```python
   if success_count % BATCH_PAUSE_INTERVAL == 0:
       time.sleep(BATCH_PAUSE_DURATION)
   ```
   - 每处理 20 个视频暂停 10 秒（可配置）
   - 避免触发 YouTube 速率限制

3. **实时显示进度**
   ```python
   progress_percent = (completed_count / len(videos_to_process)) * 100
   print_colored(f"进度: {completed_count}/{len(videos_to_process)} ({progress_percent:.1f}%) | 成功: {success_count} | 失败: {failed_count}", Colors.CYAN, end='\r')
   ```
   - 实时更新进度条
   - 显示成功/失败数量

---

### 阶段 7: 数据保存阶段

**位置**: `get_all_videos()` 函数结束部分

**步骤**:

1. **最终保存进度**
   ```python
   save_progress(progress_file, processed_ids)
   ```

2. **保存到 CSV 文件**
   ```python
   # 判断是追加还是新建
   mode = 'a' if (file_exists or resume) else 'w'
   
   with open(output_csv, mode, newline='', encoding='utf-8-sig') as f:
       writer = csv.DictWriter(f, fieldnames=headers)
       
       # 如果是新建文件，写入表头
       if not file_exists:
           writer.writeheader()
       
       # 写入新数据
       for video_data in all_video_data:
           writer.writerow({...})
   ```

3. **CSV 文件结构**
   - 包含 40+ 个字段
   - 字段列表：
     - 基本信息：视频ID、标题、链接
     - 频道信息：频道名称、ID、链接、订阅数
     - 上传者信息：上传者、ID、链接
     - 日期信息：上传日期、发布日期
     - 时长信息：视频时长（秒）、格式化时长
     - 统计数据：播放量、点赞量、评论数、点赞率
     - 内容信息：描述、标签、分类
     - 技术信息：分辨率、编码、文件大小
     - 字幕信息：字幕语言、自动字幕语言
     - 其他：章节数量、扩展名、格式ID

4. **显示统计信息**
   ```python
   print_colored(f"✅ 成功获取 {success_count} 个视频的完整信息", Colors.GREEN)
   print_colored(f"📝 成功下载 {subtitle_count} 个字幕文件", Colors.CYAN)
   print_colored(f"📊 CSV中总视频数: {total_in_csv}", Colors.CYAN)
   ```

---

## 关键函数说明

### 1. `detect_url_type(url)`

**功能**: 检测 URL 类型和内容类型

**返回**: `(url_type, normalized_url, content_type)`

**示例**:
```python
detect_url_type("https://www.youtube.com/@channelname/videos")
# 返回: ('channel', 'https://www.youtube.com/@channelname/videos', 'videos')
```

---

### 2. `get_channel_videos(channel_url, content_type='videos')`

**功能**: 获取频道的视频列表

**参数**:
- `channel_url`: 频道 URL
- `content_type`: 内容类型（videos/shorts/playlists/posts）

**返回**: `[{'id': 'xxx', 'url': 'xxx', 'title': 'xxx'}, ...]`

**特点**:
- 使用 `extract_flat=True` 快速获取（不下载）
- 不限制数量

---

### 3. `get_full_video_info(video_url)`

**功能**: 获取视频的完整详细信息

**装饰器**: `@retry_with_backoff`（自动重试）

**返回**: 包含所有字段的字典

**重试策略**:
- 最大重试：3 次
- 初始延迟：1 秒
- 退避因子：2（指数退避）
- 特别处理速率限制错误

---

### 4. `extract_video_data(info)`

**功能**: 从 yt-dlp 的 info 字典中提取所有字段

**返回**: 包含 40+ 个字段的字典

**提取的字段**:
- 基本信息（标题、ID、链接）
- 频道信息（名称、ID、订阅数）
- 统计数据（播放量、点赞量、评论数）
- 技术信息（分辨率、编码、文件大小）
- 字幕信息（可用语言）
- 等等

---

### 5. `process_single_video(video, subtitles_path, videos_path, download_video_file, logger)`

**功能**: 处理单个视频（核心处理函数）

**参数**:
- `video`: 视频信息字典（包含 id, title, url）
- `subtitles_path`: 字幕保存路径
- `videos_path`: 视频保存路径（可选）
- `download_video_file`: 是否下载视频文件
- `logger`: 日志记录器

**返回**: `(video_data, video_id, video_title, has_subtitle, success, error_msg)`

**执行流程**:
1. 获取视频完整信息
2. 提取视频数据
3. 下载字幕（默认）或视频文件（可选）
4. 生成信息文档（可选）
5. 转换字幕格式（可选）

---

### 6. `download_subtitles(video_url, subtitle_path, video_id, video_title)`

**功能**: 下载视频字幕文件

**配置**: 使用 `YT_DLP_SUBTITLE_OPTS`

**下载的语言**: 英文（en）、简体中文（zh-Hans）

**输出格式**: `.srt`

---

### 7. `download_video(url, save_path, folder_name)`

**功能**: 下载视频、音频、字幕、封面

**配置**: 使用 `YT_DLP_VIDEO_OPTS`

**下载内容**:
- 视频文件（最佳质量）
- 音频文件
- 字幕文件（中英文）
- 封面图片

---

### 8. `generate_video_info(url, info_file_path)`

**功能**: 生成视频信息文档

**实现**: 调用 `generate_video_info.py` 脚本

**输出格式**: Markdown (`.md`)

**内容**: 包含视频的完整元数据信息

---

### 9. `convert_single_srt_to_text(srt_file, output_dir)`

**功能**: 将 SRT 字幕文件转换为 TXT 和 MD 格式

**输入**: `.srt` 文件

**输出**: 
- `.txt` 文件（纯文本）
- `.md` 文件（Markdown 格式）

---

## 数据流说明

### 输入数据流

```
用户输入 URL
  │
  ├─→ detect_url_type() → (url_type, normalized_url, content_type)
  │
  ├─→ get_channel_videos() / get_playlist_videos()
  │   └─→ [{'id': 'xxx', 'url': 'xxx', 'title': 'xxx'}, ...]
  │
  └─→ 过滤已处理视频
      └─→ videos_to_process
```

### 处理数据流

```
videos_to_process
  │
  ├─→ ThreadPoolExecutor（并发处理）
  │   │
  │   ├─→ process_single_video(video1)
  │   │   ├─→ get_full_video_info() → info1
  │   │   ├─→ extract_video_data() → video_data1
  │   │   ├─→ download_subtitles() → subtitle_files1
  │   │   └─→ (可选) download_video() → video_file1
  │   │
  │   ├─→ process_single_video(video2)
  │   │   └─→ ...
  │   │
  │   └─→ process_single_video(videoN)
  │       └─→ ...
  │
  └─→ 收集结果
      └─→ all_video_data = [video_data1, video_data2, ...]
```

### 输出数据流

```
all_video_data
  │
  ├─→ 写入 CSV 文件
  │   └─→ {channel_name}_all_videos.csv
  │
  ├─→ 保存进度文件
  │   └─→ {channel_name}_progress.json
  │
  ├─→ 字幕文件（subtitles/）
  │   ├─→ video1.en.srt
  │   ├─→ video1.zh-Hans.srt
  │   └─→ ...
  │
  └─→ 视频文件（videos/，可选）
      ├─→ folder1/
      │   ├─→ video1.mp4
      │   ├─→ video1.en.srt
      │   ├─→ video1.en.txt
      │   ├─→ video1.en.md
      │   ├─→ video1.zh-Hans.srt
      │   ├─→ video1.zh-Hans.txt
      │   ├─→ video1.zh-Hans.md
      │   ├─→ thumbnail.jpg
      │   └─→ info.md
      └─→ ...
```

---

## 输出文件结构

### 目录结构概览

程序会根据运行模式创建不同的目录结构：

#### 模式 1: 默认模式（只下载字幕）

```
{OUTPUT_DIR_ROOT}/                    # 默认: /data/user/lulu/aMI_results/ytdlpDownload02
└── {channel_name}/                   # 从URL自动提取的频道名称
    ├── subtitles/                    # 字幕文件夹（默认创建）
    │   ├── {video_title}_{video_id}.en.srt
    │   ├── {video_title}_{video_id}.zh-Hans.srt
    │   ├── {video_title2}_{video_id2}.en.srt
    │   ├── {video_title2}_{video_id2}.zh-Hans.srt
    │   └── ...
    │
    ├── {channel_name}_all_videos.csv  # CSV 汇总文件（包含所有视频信息）
    ├── {channel_name}_progress.json   # 进度文件（断点续传用）
    └── logs/                          # 日志文件夹
        └── get_all_videos_YYYYMMDD_HHMMSS.log
```

#### 模式 2: 完整下载模式（-d 参数）

```
{OUTPUT_DIR_ROOT}/
└── {channel_name}/
    ├── subtitles/                    # 字幕文件夹（默认创建）
    │   ├── {video_title}_{video_id}.en.srt
    │   ├── {video_title}_{video_id}.zh-Hans.srt
    │   └── ...
    │
    ├── videos/                        # 视频文件夹（-d 参数启用）
    │   ├── {folder_name1}/            # 视频标题前10个字符作为文件夹名
    │   │   ├── {video_title}.mp4      # 视频文件（最佳质量）
    │   │   ├── {video_title}.en.srt   # 英文字幕（SRT格式）
    │   │   ├── {video_title}.en.txt   # 英文字幕文本（纯文本）
    │   │   ├── {video_title}.en.md    # 英文字幕Markdown
    │   │   ├── {video_title}.zh-Hans.srt   # 中文字幕（SRT格式）
    │   │   ├── {video_title}.zh-Hans.txt   # 中文字幕文本（纯文本）
    │   │   ├── {video_title}.zh-Hans.md    # 中文字幕Markdown
    │   │   ├── {video_title}.jpg            # 封面图片（JPG格式）
    │   │   └── {info_filename}.md           # 视频信息文档（Markdown）
    │   │
    │   ├── {folder_name2}/            # 第二个视频文件夹
    │   │   └── ...
    │   └── ...
    │
    ├── {channel_name}_all_videos.csv  # CSV 汇总文件
    ├── {channel_name}_progress.json   # 进度文件
    └── logs/                          # 日志文件夹
        └── get_all_videos_YYYYMMDD_HHMMSS.log
```

### 文件命名规则

#### 1. 频道名称提取规则

- **从 URL 提取**: `https://www.youtube.com/@channelname` → `channelname`
- **从 URL 提取**: `https://www.youtube.com/c/channelname` → `channelname`
- **从 URL 提取**: `https://www.youtube.com/channel/UCxxxxx` → `channel_UCxxxxx`
- **无法提取时**: 尝试从第一个视频获取上传者名称，或使用 `unknown_channel`

#### 2. 字幕文件命名（subtitles/ 文件夹）

**格式**: `{video_title}_{video_id}.{lang}.srt`

**规则**:
- `video_title`: 视频标题（清理特殊字符，限制长度）
- `video_id`: YouTube 视频 ID
- `lang`: 语言代码（`en` 或 `zh-Hans`）

**示例**:
```
How_to_Learn_Python_dQw4w9WgXcQ.en.srt
How_to_Learn_Python_dQw4w9WgXcQ.zh-Hans.srt
```

#### 3. 视频文件夹命名（videos/ 文件夹）

**格式**: `{folder_name}`

**规则**:
- 使用视频标题的前 10 个字符（清理特殊字符后）
- 如果标题不足 10 个字符，使用完整标题
- 只保留字母、数字、中文、下划线和连字符

**示例**:
- 标题: `How to Learn Python in 2024`
- 文件夹名: `HowtoLearnP`（前10个字符）

#### 4. 视频文件命名（videos/{folder_name}/ 文件夹）

**视频文件**:
- 格式: `{video_title}.{ext}`
- 扩展名: `.mp4`, `.mkv`, `.webm` 等（取决于可用格式）
- 示例: `How to Learn Python in 2024.mp4`

**字幕文件**:
- SRT: `{video_title}.{lang}.srt`
- TXT: `{video_title}.{lang}.txt`
- MD: `{video_title}.{lang}.md`
- 示例:
  - `How to Learn Python in 2024.en.srt`
  - `How to Learn Python in 2024.en.txt`
  - `How to Learn Python in 2024.en.md`

**封面图片**:
- 格式: `{video_title}.{ext}`
- 扩展名: `.jpg`, `.png`, `.webp` 等
- 示例: `How to Learn Python in 2024.jpg`

**信息文档**:
- 格式: `{title_prefix}_{timestamp}.md`
- 规则: 视频标题前20个字符 + 时间戳
- 示例: `HowtoLearnPythonin_20240101_120000.md`

#### 5. CSV 文件命名

**格式**: `{channel_name}_all_videos.csv`

**示例**: `channelname_all_videos.csv`

#### 6. 进度文件命名

**格式**: `{channel_name}_progress.json`

**示例**: `channelname_progress.json`

#### 7. 日志文件命名

**格式**: `get_all_videos_YYYYMMDD_HHMMSS.log`

**示例**: `get_all_videos_20240101_120000.log`

### 文件格式说明

| 文件类型 | 格式 | 编码 | 说明 |
|---------|------|------|------|
| CSV 文件 | `.csv` | UTF-8 with BOM | Excel 可直接打开 |
| 进度文件 | `.json` | UTF-8 | JSON 格式，用于断点续传 |
| 字幕文件 | `.srt` | UTF-8 | 标准字幕格式 |
| 字幕文本 | `.txt` | UTF-8 | 纯文本格式（去除时间戳） |
| 字幕Markdown | `.md` | UTF-8 | Markdown 格式（去除时间戳） |
| 视频文件 | `.mp4`/`.mkv`/`.webm` | - | 视频容器格式 |
| 封面图片 | `.jpg`/`.png`/`.webp` | - | 图片格式 |
| 信息文档 | `.md` | UTF-8 | Markdown 格式 |
| 日志文件 | `.log` | UTF-8 | 文本日志格式 |

### 目录结构示例

#### 实际示例 1: 默认模式

```
/data/user/lulu/aMI_results/ytdlpDownload02/
└── channelname/
    ├── subtitles/
    │   ├── How_to_Learn_Python_dQw4w9WgXcQ.en.srt
    │   ├── How_to_Learn_Python_dQw4w9WgXcQ.zh-Hans.srt
    │   ├── Advanced_Python_Tips_abc123xyz.en.srt
    │   └── Advanced_Python_Tips_abc123xyz.zh-Hans.srt
    │
    ├── channelname_all_videos.csv
    ├── channelname_progress.json
    └── logs/
        └── get_all_videos_20240101_120000.log
```

#### 实际示例 2: 完整下载模式

```
/data/user/lulu/aMI_results/ytdlpDownload02/
└── channelname/
    ├── subtitles/
    │   ├── How_to_Learn_Python_dQw4w9WgXcQ.en.srt
    │   └── How_to_Learn_Python_dQw4w9WgXcQ.zh-Hans.srt
    │
    ├── videos/
    │   ├── HowtoLearnP/                    # 视频标题前10字符
    │   │   ├── How to Learn Python in 2024.mp4
    │   │   ├── How to Learn Python in 2024.en.srt
    │   │   ├── How to Learn Python in 2024.en.txt
    │   │   ├── How to Learn Python in 2024.en.md
    │   │   ├── How to Learn Python in 2024.zh-Hans.srt
    │   │   ├── How to Learn Python in 2024.zh-Hans.txt
    │   │   ├── How to Learn Python in 2024.zh-Hans.md
    │   │   ├── How to Learn Python in 2024.jpg
    │   │   └── HowtoLearnPython_20240101_120000.md
    │   │
    │   └── AdvancedPy/                     # 第二个视频
    │       ├── Advanced Python Tips.mp4
    │       ├── Advanced Python Tips.en.srt
    │       ├── Advanced Python Tips.en.txt
    │       ├── Advanced Python Tips.en.md
    │       ├── Advanced Python Tips.zh-Hans.srt
    │       ├── Advanced Python Tips.zh-Hans.txt
    │       ├── Advanced Python Tips.zh-Hans.md
    │       ├── Advanced Python Tips.jpg
    │       └── AdvancedPythonTip_20240101_120500.md
    │
    ├── channelname_all_videos.csv
    ├── channelname_progress.json
    └── logs/
        └── get_all_videos_20240101_120000.log
```

### 文件大小估算

| 文件类型 | 典型大小 | 说明 |
|---------|---------|------|
| CSV 文件 | 10-100 KB/视频 | 取决于视频数量 |
| 进度文件 | 1-10 KB | JSON 格式，包含视频ID列表 |
| 字幕文件 (.srt) | 10-100 KB/视频 | 取决于视频时长 |
| 字幕文本 (.txt) | 5-50 KB/视频 | 去除时间戳后更小 |
| 字幕Markdown (.md) | 5-50 KB/视频 | 与文本类似 |
| 视频文件 | 50-500 MB/视频 | 取决于质量和时长 |
| 封面图片 | 50-500 KB/视频 | JPG/PNG 格式 |
| 信息文档 (.md) | 5-20 KB/视频 | Markdown 格式 |
| 日志文件 | 1-10 MB | 取决于处理视频数量 |

### 目录权限说明

所有目录和文件默认权限：
- **目录**: `755` (rwxr-xr-x)
- **文件**: `644` (rw-r--r--)

### 注意事项

1. **文件名清理**: 所有文件名中的特殊字符会被清理，只保留字母、数字、中文、下划线和连字符
2. **路径长度**: 某些系统对路径长度有限制，过长的标题会被截断
3. **并发安全**: 多线程环境下，文件写入使用锁保护，确保数据一致性
4. **断点续传**: 进度文件定期保存，程序中断后可恢复
5. **编码统一**: 所有文本文件使用 UTF-8 编码，确保中文正常显示

### CSV 文件字段说明

| 字段名 | 说明 | 示例 |
|--------|------|------|
| 视频ID | YouTube 视频 ID | `dQw4w9WgXcQ` |
| 视频标题 | 视频标题 | `Example Video` |
| 视频链接 | 完整 URL | `https://www.youtube.com/watch?v=...` |
| 频道名称 | 频道名称 | `Channel Name` |
| 频道ID | 频道 ID | `UCxxxxx` |
| 播放量 | 播放次数 | `1000000` |
| 点赞量 | 点赞数 | `50000` |
| 评论数 | 评论数 | `1000` |
| 点赞率(%) | 点赞率 | `5.00` |
| 视频时长 | 格式化时长 | `10:30` |
| 字幕语言 | 可用字幕语言 | `en; zh-Hans` |
| ... | ... | ... |

---

## 错误处理机制

### 1. 重试机制

**装饰器**: `@retry_with_backoff`

**策略**:
- 最大重试次数：3 次（可配置）
- 初始延迟：1 秒
- 退避因子：2（指数退避）
- 延迟序列：1秒 → 2秒 → 4秒

**特别处理**:
- 速率限制错误（429）：额外等待 30 秒
- 其他错误：标准指数退避

### 2. 错误分类

**可重试错误**:
- 网络超时
- 临时服务器错误
- 速率限制错误

**不可重试错误**:
- 视频不存在（404）
- 视频已删除
- 权限错误

### 3. 错误记录

- 所有错误记录到日志文件
- 失败视频记录到控制台输出
- 最终统计显示失败数量

---

## 性能优化策略

### 1. 并发处理

- **默认并发数**: 5 个线程
- **推荐范围**: 3-10 个线程
- **最大限制**: 20 个线程

**权衡**:
- 并发数过高 → 触发速率限制
- 并发数过低 → 处理速度慢

### 2. 速率控制

**请求延迟**:
- 每个请求之间延迟 1 秒（可配置）

**批量暂停**:
- 每处理 20 个视频暂停 10 秒（可配置）

**速率限制检测**:
- 自动检测 429 错误
- 额外等待 30 秒后重试

### 3. 进度保存

- 每处理 10 个视频保存一次进度（可配置）
- 避免大量数据丢失

### 4. 断点续传

- 自动检测已处理的视频
- 跳过已存在的视频
- 支持从进度文件恢复

---

## 使用示例

### 基本用法（只下载字幕）

```bash
python3 get_all_videos.py https://www.youtube.com/@channelname
```

### 完整下载（下载视频、字幕、封面、信息文档）

```bash
python3 get_all_videos.py -d https://www.youtube.com/@channelname
```

### 断点续传

```bash
python3 get_all_videos.py -r https://www.youtube.com/@channelname
```

### 自定义并发数

```bash
python3 get_all_videos.py -w 10 https://www.youtube.com/@channelname
```

### 获取所有类型内容

```bash
python3 get_all_videos.py --all-types https://www.youtube.com/@channelname
```

### 组合使用

```bash
python3 get_all_videos.py \
    -d \
    -r \
    -w 8 \
    --all-types \
    https://www.youtube.com/@channelname
```

---

## 配置说明

### 关键配置项（config.py）

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `DEFAULT_MAX_WORKERS` | 5 | 默认并发线程数 |
| `PROGRESS_SAVE_INTERVAL` | 10 | 进度保存间隔 |
| `BATCH_PAUSE_INTERVAL` | 20 | 批量暂停间隔 |
| `BATCH_PAUSE_DURATION` | 10 | 批量暂停时长（秒） |
| `REQUEST_DELAY` | 1.0 | 请求延迟（秒） |
| `GET_INFO_MAX_RETRIES` | 3 | 获取信息最大重试次数 |
| `RATE_LIMIT_EXTRA_DELAY` | 30 | 速率限制额外延迟（秒） |

---

## 总结

`get_all_videos.py` 是一个功能完整、性能优化的 YouTube 视频信息获取工具。它通过以下特性实现了高效、可靠的数据获取：

1. ✅ **自动化**: 自动识别频道、提取信息、创建目录
2. ✅ **并发处理**: 多线程并发提高处理速度
3. ✅ **错误处理**: 完善的重试机制和错误处理
4. ✅ **进度管理**: 自动保存进度，支持断点续传
5. ✅ **速率控制**: 智能控制请求频率，避免触发限制
6. ✅ **灵活配置**: 支持多种参数和配置选项

通过合理使用这些功能，可以高效地批量获取 YouTube 频道的所有视频信息。
