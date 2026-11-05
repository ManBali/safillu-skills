---
name: gem-vision
description: 用 GEM 3.5 flash（api.lk888.ai，Gemini 原生协议）分析识别视频：视频内容总结/时间线梳理/人物物体识别/口播字幕提取/视频问答/违规或敏感内容识别；也可当多模态 LLM 用（图片理解、纯文本对话）。当用户要求"分析视频/看视频/这个视频里有什么/视频识别/总结视频/视频问答/识别画面/视频里说的什么"等需求时使用。
user-invocable: true
allowed-tools:
  - Bash(python *)
  - Bash(python3 *)
  - Read
  - Glob
---

# GEM Vision — 视频分析 / 多模态问答（GEM 3.5 flash）

参数：$ARGUMENTS

## 首次使用：配置 key

向技能提供方获取 API key。推荐在仓库目录运行 `python configure.py` 统一配置所有技能凭证（写入 `~/.claude-skills/keys.json`）。也可以单独配置：

```bash
# 方式一：写入统一配置文件
python "<技能目录>/scripts/gem_vision.py" --login sk-xxxxxxxx

# 方式二：环境变量（优先级最高）
export GEM_VISION_API_KEY=sk-xxxxxxxx        # Windows PowerShell: $env:GEM_VISION_API_KEY="sk-xxxxxxxx"
```

key 读取顺序：`GEM_VISION_API_KEY` → `~/.claude-skills/keys.json` 的 `gem_vision_api_key` → `~/.gem-vision/key` → 脚本同目录 `gem_vision.key`。

## 执行方式

核心脚本是本技能目录下的 `scripts/gem_vision.py`（纯标准库，无需 pip；ffmpeg 仅在"大视频抽帧"时需要）。安装到个人技能目录后路径通常是 `~/.claude/skills/gem-vision/scripts/gem_vision.py`（Windows 为 `%USERPROFILE%\.claude\skills\gem-vision\scripts\gem_vision.py`）。

流程：确认视频/图片本地路径存在 → 构造具体的分析问题 → Bash 运行脚本 → 从 stdout 拿到模型回答 → 回答很长时加 `-o` 落盘再 Read → 把结论整理告诉用户。

```bash
python "<技能目录>/scripts/gem_vision.py" "这个视频里发生了什么？按时间线总结，并列出出现的物体和人" --video "视频.mp4"
```

## 常用命令

```bash
# 视频分析（核心用法）
python "<技能目录>/scripts/gem_vision.py" "总结视频内容，按时间线列出关键事件" --video clip.mp4

# 大视频：提高抽帧密度（默认 16 帧）
python "<技能目录>/scripts/gem_vision.py" "识别视频里出现的文字和产品型号" --video big.mp4 --frames 24

# 图片理解
python "<技能目录>/scripts/gem_vision.py" "描述这张图，提取所有文字" --image photo.jpg

# 纯文本 LLM（带角色设定）
python "<技能目录>/scripts/gem_vision.py" "三句话讲清楚 RAG 的原理" --system "你是技术讲师，回答精炼"

# 保存长回答后 Read
python "<技能目录>/scripts/gem_vision.py" "输出详细分析报告" --video v.mp4 -o report.md
```

## 参数速查

| 参数 | 说明 |
|---|---|
| 第 1 个位置参数 | 问题/指令，越具体越好（要时间线还是要物体清单要说明白） |
| `--login KEY` | 保存 API key 到 `~/.gem-vision/key` 后退出 |
| `-v/--video` | 视频文件路径，可重复最多 4 个；**只支持本地文件** |
| `-i/--image` | 图片文件路径，可重复最多 14 张 |
| `--model` | 默认 `gem-3.5-flash`，可切同站其他模型 |
| `--system` | system instruction（角色/风格/规则） |
| `--frames` | 大视频抽帧数量（默认 16，720p JPG） |
| `--max-inline-mb` | 整段内联上传的大小阈值（默认 14 MB） |
| `--force-frames` | 即使视频够小也强制抽帧（更快更省 token，但无音轨） |
| `--search` | 启用联网搜索 google_search（网关不支持时报错就去掉） |
| `--temp` / `--max-tokens` | temperature / maxOutputTokens |
| `--timeout` | 请求超时秒数（默认 300，长视频分析可调大） |
| `--chat` | 交互式多轮对话（这是给用户在终端用的；Claude 自己单轮调用即可） |
| `-o/--out` | 回答保存到文件（chat 模式逐轮追加成对话记录） |
| `--json` | 输出原始 JSON 响应（调试用） |

## 视频处理策略（脚本自动选择）

1. **≤14MB 且格式支持**（mp4/mkv/mov/webm/mpeg/ts）→ 整段 base64 内联上传，**含音轨**，能识别语音口播；
2. **更大或格式受限**（如 avi/wmv）→ 自动用 ffmpeg 按时长均匀抽 N 帧（默认 16，缩放到 720p），并在提示词里附上每帧对应的时间点，让模型能引用时间位置；
3. `--force-frames` 强制走抽帧路径（省 token、响应快，代价是丢音轨）。

## 使用约定

1. **先确认文件存在**：视频路径先 Glob/ls 确认；用户给的是分享链接时，先用 `video-download` 技能下载到本地再分析。
2. **提问要具体**：总结类给出结构（时间线/要点/物体清单/字幕转写），识别类说清楚要识别什么（人/物/文字/品牌/动作）。
3. **语音口播内容**必须走内联模式（≤14MB 或视频切片）；抽帧模式无音轨，听不到内容。视频太大时建议用户先截取相关片段。
4. **长回答落盘**：预计回答很长（报告、逐帧标注）时加 `-o xxx.md`，然后 Read 检查。
5. **失败排查**：stdout 会打印 HTTP 状态和响应体，参数错误/网关不支持某参数时按提示调整；429/5xx 脚本会自动重试。

## 已知限制（务必如实告知用户）

- **只支持本地文件**：不支持视频 URL 直传；网络视频先下载（可用 `video-download` 技能）。
- **抽帧无音轨**：需要听语音内容时必须内联模式；超过 14MB 请让用户压缩或截片段。
- **--search 依赖网关透传**：报错时去掉该参数。
- API key 不内置在脚本中：需通过 `--login` 或环境变量 `GEM_VISION_API_KEY` 配置。

## 详细文档

完整使用文档（场景示例、故障排查）见本技能目录 `README.md`。
