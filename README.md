# Bilibili 280534030 视频转写

这个仓库用于逐个转写 Bilibili 空间 `https://space.bilibili.com/280534030/video` 中可访问的视频。

## 工作方式

- 发现阶段使用 `yt-dlp` 读取空间视频，并递归展开空间页返回的合集（包括隐藏合集）。
- 合集和空间直出视频按 BVID 去重，队列保存在 `state/queue.json`。
- 每次 GitHub Actions Run 只处理一个视频：下载音频、校验时长、使用 faster-whisper 转写，然后提交文本和状态。
- 成功后写入 `state/continue.flag`，工作流再触发下一次 Run；失败项写入 `state/failed.txt` 和 `state/errors/`，不会无限重试。
- 只提交转写文本和状态，不提交音频或 Cookie。

## 仓库级 Secret

可在本仓库配置 `BILIBILI_SOURCE_COOKIE_FILE_280534030`，值为 yt-dlp 可读取的 Netscape Cookie 文件内容。Cookie 只在 Actions 临时目录中使用。

没有配置 Cookie 时，工作流仍会尝试发现和转写公开可访问的视频；受登录限制的视频会记录为失败，之后可配置 Cookie 并从失败重试工作流重新处理。

## Actions

- `转写 Bilibili 280534030 空间`：可手动运行，也会按计划运行；每次只处理一个视频。
- `重试 Bilibili 280534030 失败字幕`：手动选择最多重试数量，只处理当前失败项。

## 目录

- `scripts/transcribe_bili.py`：发现、下载、转写和状态推进。
- `scripts/transcription_integrity.py`：音频完整性和转写覆盖率校验。
- `transcripts/`：每个 BVID 一个纯文本转写文件。
- `state/`：队列、完成/失败列表、进度和错误记录。
