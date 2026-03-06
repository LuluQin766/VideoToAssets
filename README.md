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
并至少设置：
```bash
# Bailian（你给的 coding.dashscope 兼容端点）API Key
BAILIAN_API_KEY=你的key
```
说明：只需要配置一个 Key，取决于 `configs/app.yaml` 里的 `llm.provider`。
当前默认是 `bailian`，所以只配 `BAILIAN_API_KEY` 即可。
可选（通常无需改）：
```bash
# 若切换到 qwen provider，可用:
# DASHSCOPE_API_KEY=你的key
VIDEO_TO_ASSETS_LLM_BASE_URL=https://coding.dashscope.aliyuncs.com/v1
VIDEO_TO_ASSETS_USE_MOCK_LLM=false
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

## LLM 真实调用校验
- 质量报告文件 `data/outputs/{video_id}/llm_review/quality_report.md` 首行会显示 `mode`。
- `mode: bailian` / `mode: qwen` / `mode: openai` 代表已实际调用真实模型。
- `mode: mock` 代表仍在用本地兜底（通常是 Key 未配置或网络不可达）。

## 安全说明
`.env` 已在 `.gitignore` 中被忽略，不会被 Git 提交。不要把真实 Key 写进 `.env.example` 或代码里。
