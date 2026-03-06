# **给 Codex 的第三轮开发任务书**

### **0. 本轮定位**


项目名仍保持：VideoToAssets

  

当前前提：

- 现有视频处理流程已经可运行
    
- 已支持 metadata、字幕下载、ASR、清洗、LLM 审校、整理文稿、摘要/文章/高光等至少部分能力
    
- 本轮不是重写，而是做**增量式架构升级**
    

  

### **1. 本轮目标**

  

把系统从“视频输入专用”升级为“多输入内容处理系统”，新增两类输入：

1. raw text input
    
2. local file input
    

  

并保持现有 video input 正常工作。

  

### **2. 设计原则**

- 不要拆成多个独立项目
    
- 不要推翻现有视频流程
    
- 增加输入适配层
    
- 引入统一的 canonical content model
    
- 尽量复用后续 asset generation pipeline
    
- 采用渐进式重构，先兼容、再统一
    

  

### **3. 本轮支持的输入类型**

  

必须支持：

- video
    
- text
    
- file
    

  

其中 file 第一阶段只要求支持：

- .txt
    
- .md
    
- .srt
    
- .vtt
    
- .json
    

  

暂不要求：

- .docx
    
- .pdf
    
- .html
    
- 网页链接解析
    

  

### **4. 本轮核心任务**

  

#### **模块 T：输入类型路由**

新增 source routing layer，根据命令行参数判断输入类型，并转发到不同 adapter。

  

建议文件：

```
src/video_to_assets/pipeline/source_router.py
src/video_to_assets/models/source_input.py
```

要求：

- 支持 --input-type video
    
- 支持 --input-type text
    
- 支持 --input-type file
    

---

#### **模块 U：新增 adapters**

新增：

```
src/video_to_assets/adapters/base_adapter.py
src/video_to_assets/adapters/video_adapter.py
src/video_to_assets/adapters/text_adapter.py
src/video_to_assets/adapters/file_adapter.py
```

职责：

- video_adapter：复用现有视频接入流程
    
- text_adapter：接收一段文字或文字文件
    
- file_adapter：解析本地文件并提取正文
    

  

要求：

- 不要把后续摘要/文章逻辑写进 adapter
    
- adapter 的职责只到“把输入源转成标准内容对象”为止
    

---

#### **模块 V：统一内容模型**

引入 canonical content model，所有输入最终都要转成统一结构。

  

建议文件：

```
src/video_to_assets/canonical/canonical_content.py
src/video_to_assets/canonical/normalizer.py
src/video_to_assets/canonical/metadata_merger.py
```

建议字段至少包括：

- source_id
    
- source_type
    
- title
    
- raw_text
    
- clean_text
    
- language
    
- timestamps (optional)
    
- source_metadata
    
- attribution
    
- structure_hints
    
- processing_flags
    

  

输出文件建议新增：

```
data/outputs/{source_id}/normalized/canonical_content.json
data/outputs/{source_id}/normalized/clean_text.txt
data/outputs/{source_id}/normalized/structured_text.md
```

---

#### **模块 W：文本输入支持**

支持两种 text 输入方式：

```
python scripts/run_single.py --input-type text --text "..."
python scripts/run_single.py --input-type text --text-file "data/inbox/demo.txt"
```

可选附加参数：

- --title
    
- --source-name
    
- --source-url
    
- --author
    
- --publish-date
    
- --platform
    

  

如果未提供来源信息，也要能运行，但需要在 source attribution 中标注为“user-provided text / source metadata incomplete”。

---

#### **模块 X：文件输入支持**

支持：

```
python scripts/run_single.py --input-type file --file "data/inbox/demo.md"
```

本轮需支持解析：

- txt
    
- md
    
- srt
    
- vtt
    
- json
    

  

要求：

- 自动根据扩展名调用对应 parser
    
- srt/vtt 要保留时间戳信息
    
- txt/md 要尽量保留段落结构
    
- json 至少支持读取你系统自身的 canonical 或 transcript 类结构
    

---

#### **模块 Y：共享后处理接入**

现有下游模块应尽量复用，不要再复制一套 text/file 专用版本：

- llm review
    
- transcript/content polishing
    
- summary generation
    
- wechat article generation
    
- xiaohongshu generation
    
- highlight mining
    
- readme builder
    

  

要求：

- 下游处理面向 canonical content，而不是直接依赖 video-only fields
    
- 对 timestamps 做 optional 支持
    

---

#### **模块 Z：source-aware 高光输出**

高光模块需要按 source_type 区分输出形式：

- video：输出 start/end time 的 clip
    
- text：输出 paragraph-based highlights
    
- file：输出 paragraph / section-based highlights
    

  

要求：

- 保持统一结构字段
    
- 允许 video 有 start_time/end_time
    
- 允许 text/file 用 paragraph_id / section_id
    

---

#### **模块 AA：输出目录兼容升级**

当前每视频目录建议升级为“每 source 目录”。

  

新增建议结构：

```
data/outputs/{source_id}/
├── source/
│   ├── source_info.json
│   ├── source_info.md
│   └── source_snapshot.txt
├── normalized/
│   ├── canonical_content.json
│   ├── clean_text.txt
│   └── structured_text.md
├── llm_review/
├── summaries/
├── articles_wechat/
├── articles_xiaohongshu/
├── highlights/
└── README.md
```

兼容要求：

- video 输入仍然保留原 metadata / subtitles / asr 目录
    
- text/file 输入不强行生成这些无意义目录
    

---

#### **模块 AB：CLI 升级**

CLI 需支持以下形式：

```
python scripts/run_single.py --input-type video --url "VIDEO_URL" --tasks all
python scripts/run_single.py --input-type text --text "这里是一段文字" --tasks summary,wechat
python scripts/run_single.py --input-type text --text-file "data/inbox/demo.txt" --tasks all
python scripts/run_single.py --input-type file --file "data/inbox/demo.md" --tasks all
```

要求：

- 参数冲突要有明确报错
    
- 缺少必要参数要给出清晰提示
    
- task routing 继续沿用前一轮设计
    

---

#### **模块 AC：README 与来源说明升级**

README 需要清楚显示：

- source_type
    
- 输入方式
    
- 原始来源信息是否完整
    
- 本次生成了哪些资产
    
- 哪些资产使用了时间戳
    
- 推荐人工优先检查哪些文件
    

  

source attribution 需要兼容：

- 自动抓取来源（video）
    
- 用户补充来源（text/file）
    
- 无来源的本地文本说明
    

---

### **5. 本轮不要做的事**

- 不要重命名整个仓库
    
- 不要把 src/video_to_assets/ 一次性全部迁移成 src/content_to_assets/
    
- 不要先做 docx/pdf
    
- 不要开发 Web UI
    
- 不要重写所有 prompt
    
- 不要打断现有视频闭环
    

  

### **6. 本轮开发顺序**

  

#### **Phase 1**

- source router
    
- base adapter
    
- canonical content model
    

  

#### **Phase 2**

- text adapter
    
- file adapter
    
- txt/md/srt/vtt/json parsers
    

  

#### **Phase 3**

- 接入现有 shared pipeline
    
- source-aware highlight output
    
- CLI 升级
    

  

#### **Phase 4**

- README/source attribution 升级
    
- tests
    
- 回归验证 video input 不被破坏
    

  

### **7. 验收标准**

  

成功执行以下 4 类命令：

```
python scripts/run_single.py --input-type video --url "VIDEO_URL" --tasks all
python scripts/run_single.py --input-type text --text "这里是一段文字" --tasks summary
python scripts/run_single.py --input-type text --text-file "data/inbox/demo.txt" --tasks all
python scripts/run_single.py --input-type file --file "data/inbox/demo.srt" --tasks all
```

应满足：

- 都能生成标准输出目录
    
- 都能生成 canonical content
    
- 都能进入 shared downstream pipeline
    
- video 输入原能力不退化
    
- text/file 不要求 metadata/subtitles/asr，但能正常生成 summaries/articles/highlights
    

---

# **你现在最稳的执行方式**

  

你不要一次把“第三轮任务书”和“新指令”全扔给 Codex。

更稳的是分两步：

  

## **第一步先发**

- 新指令
    
- Phase 1 + Phase 2
    

  

让它先完成：

- source router
    
- adapters
    
- canonical content
    
- text/file ingest
    

  

## **第二步再发**

- Phase 3 + Phase 4
    

  

让它再接：

- downstream reuse
    
- source-aware highlights
    
- cli upgrade
    
- readme/tests
    

这更符合 Codex 官方建议的“小步、可验证、范围清晰”的工作方式。

