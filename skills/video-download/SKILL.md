---
name: video-download
description: 视频/图集去水印下载。输入抖音、快手、微信视频号、小红书、B站等平台的分享链接，解析出无水印视频/图集图片并保存到本地，附带音乐与封面。当用户要求"下载视频/去水印/无水印下载/保存这个视频/提取视频链接/下载图集"时使用。
user-invocable: true
allowed-tools:
  - Bash(python *)
  - Bash(python3 *)
  - Read
  - Glob
---

# 视频去水印下载

参数：$ARGUMENTS

## 首次使用：配置账号

本技能调用服务方提供的解析接口，需要向技能提供方索取 UID。推荐在仓库目录运行 `python configure.py` 统一配置（写入 `~/.claude-skills/keys.json`），也可以单独配置：

```bash
python "<技能目录>/scripts/video_fetch.py" --login <UID>
```

接口地址已内置，一般无需配置。读取顺序：`VIDEO_FETCH_UID` → `~/.claude-skills/keys.json` 的 `video_download_uid` → 旧的 `~/.video-download/config.json`。需要切换接口地址时，用 `--base <地址>` 或 `VIDEO_FETCH_API_BASE`。

## 执行方式

核心脚本是本技能目录下的 `scripts/video_fetch.py`（纯标准库，无需 pip 安装）。安装到个人技能目录后路径通常是 `~/.claude/skills/video-download/scripts/video_fetch.py`。

流程：从用户输入提取分享链接（整段分享文本可直接传入）→ Bash 运行脚本 → 检查输出 → 把保存的文件路径告诉用户。

```bash
# 解析并下载（视频或图集，含音乐、封面）
python "<技能目录>/scripts/video_fetch.py" "https://v.douyin.com/xxxx"

# 指定输出目录
python "<技能目录>/scripts/video_fetch.py" "分享链接" --out "<输出目录>"

# 只解析不下载（拿无水印直链）
python "<技能目录>/scripts/video_fetch.py" "分享链接" --no-download

# 查询账号额度（不消耗次数）
python "<技能目录>/scripts/video_fetch.py" --quota
```

## 参数速查

| 参数 | 说明 |
|---|---|
| `input`（位置参数） | 分享链接或整段分享文本，自动提取其中的 http(s) 链接 |
| `--login <UID>` | 保存服务方分配的 UID |
| `--base <URL>` | 覆盖接口地址（一般不用，默认已内置） |
| `--out <目录>` | 输出目录，默认 `./video-download-output` |
| `--uid <UID>` | 临时覆盖 UID（一般不用传，默认读配置） |
| `--type 1\|2` | 强制按视频(1)/图集(2)解析，一般不用传 |
| `--no-download` | 只解析，输出直链不下载 |
| `--no-music` / `--no-cover` | 跳过音乐 / 封面下载 |
| `--quota` | 查询账号：累计/今日/每分钟使用、剩余次数、到期时间 |

## API 要点

- 请求：`GET <接口地址>/video?uid=<UID>&url=<urlencode后的视频链接>`
- 成功返回 `code=101`，`data` 含：`title` 标题、`cover` 封面、`pics` 图集、`url` 无水印视频、`music` 音乐、`type`（1=视频，2=图集）
- 账号详情：`GET <接口地址>/home/kaka/getUserinfo?uid=<UID>`

## 注意事项

- `code != 101` 时直接把 API 的 `msg` 转告用户（常见：次数用完、链接不支持、频率限制）；频率限制可提示约 1 分钟后重试。
- 图集（type=2）时脚本按 `pics` 逐张下载，命名为 `标题_01.jpg` 等；视频为 `标题.mp4`，文件名已做非法字符清洗。
- 下载较大视频可能需要 1~2 分钟，属正常现象。
- 输出目录不存在时脚本会自动创建。
- UID 是账号凭证，不要提交进任何仓库、不要发给无关的人。
