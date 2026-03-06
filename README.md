# VideoToAssets (Round 2)

VideoToAssets 将单个视频 URL 加工为结构化内容资产，输出到 `data/outputs/{video_id}/`。

## 当前能力
- 抓取视频 metadata
- 优先下载字幕，低质量时回退 ASR
- 清洗与标准化字幕/转写
- 导出标准文本文件
- 运行 LLM 质检与整理稿生成（无 API Key 时可走 mock 模式）
- 多层摘要与知识提取
- 来源归因与发布说明
- 微信长文 3 篇生成
- 小红书短帖 5 篇生成
- 高光候选三轮筛选（不做实际剪辑）
- 任务化执行：`--tasks summary|wechat|xhs|highlights|all`
- 每视频 README 资产索引与阶段状态日志

## 快速开始
1. 安装依赖：
```bash
pip install -r requirements.txt
```
2. 配置环境变量：
```bash
cp .env.example .env
```
3. 运行（全量）：
```bash
python scripts/run_single.py --url "https://www.youtube.com/watch?v=VIDEO_ID"
```
4. 按任务执行（增量）：
```bash
python scripts/run_single.py --url "https://www.youtube.com/watch?v=VIDEO_ID" --tasks summary --tasks highlights
```
或：
```bash
PYTHONPATH=src python -m video_to_assets.cli run --url "https://www.youtube.com/watch?v=VIDEO_ID"
```

## 输出目录
每次单视频输出在：
`data/outputs/{video_id}/`

包含：
- `metadata/`
- `subtitles_raw/`
- `asr/`
- `subtitles_clean/`
- `text_exports/`
- `llm_review/`
- `summaries/`
- `articles_wechat/`
- `articles_xiaohongshu/`
- `highlights/`
- `source_attribution/`
- `logs/`
- `README.md`
