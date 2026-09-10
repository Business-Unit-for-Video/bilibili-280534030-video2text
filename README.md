# Bilibili 280534030 视频转写

这个仓库用于逐个转写 Bilibili 空间 `https://space.bilibili.com/280534030/video` 中可访问的视频。

## 工作方式

- 发现阶段使用 `yt-dlp` 读取空间视频，并递归展开空间页返回的合集（包括隐藏合集）。
- 合集和空间直出视频按 BVID 去重，队列保存在 `state/queue.json`。
- 每次 GitHub Actions Run 只处理一个视频：下载音频、校验时长、使用 faster-whisper 转写，然后提交文本和状态。
- 成功后写入 `state/continue.flag`，工作流再触发下一次 Run；失败项写入 `state/failed.txt` 和 `state/errors/`，不会无限重试。
- 只提交转写文本和状态，不提交音频或 Cookie。

## 仓库级 Secret

可在本仓库配置 `BILIBILI_SOURCE_COOKIE_FILE_280534030`，值可以是 yt-dlp 的 Netscape Cookie 文件内容，也可以是 Bilibili 导出的 `cookies.json` 原文。Actions 会在临时目录中校验并转换 JSON；Cookie 值不会写入仓库或日志。

没有配置 Cookie 时，工作流仍会尝试发现和转写公开可访问的视频；受登录限制的视频会记录为失败，之后可配置 Cookie 并从失败重试工作流重新处理。

## Actions

- `转写 Bilibili 280534030 空间`：可手动运行，也会按计划运行；每次只处理一个视频。
- `重试 Bilibili 280534030 失败字幕`：手动选择最多重试数量，只处理当前失败项。

## 目录

- `scripts/transcribe_bili.py`：发现、下载、转写和状态推进。
- `scripts/transcription_integrity.py`：音频完整性和转写覆盖率校验。
- `transcripts/`：每个 BVID 一个纯文本转写文件。
- `state/`：队列、完成/失败列表、进度和错误记录。

## 主题分类

标题取自 Bilibili 视频详情接口，缓存在 `state/video-titles.json`。
运行 `python scripts/refresh_titles.py` 可补齐标题并同步队列、转录标题行及分类 CSV/JSON；正文和分类保持不变。
查询失败项记录于 `classification/title-refresh-report.json`，分类标题留空，不再用 BVID 冒充视频名称。

运行 `scripts/classify_transcripts.py` 可根据标题和转录正文生成主题分类，并读取已有 CSV 中的人工 `remark`：

- `classification/video-classification.csv`：逐视频分类清单，适合 Excel 查看和人工修订。
- `classification/video-classification.json`：包含主题分类、内容类型、命中关键词、置信度和人工 remark。
- `classification/video-classification.md`：主题分类和内容类型数量汇总。

分类是多标签的：每个视频有一个主题主分类，同时保留相关主题；`content_type` 优先采用人工 `remark`（如技术、访谈、理论、课程/实操、无意义），未标注视频才做保守推断。标题命中权重高于正文，泛化词权重较低，不沿用 B 站原合集分集。重新生成时会保留已有 `remark`，不会修改原始转录文本。
