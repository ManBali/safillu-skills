# GEM Vision — GEM 3.5 flash 视频分析 / 多模态问答

基于 **api.lk888.ai（Pix studio）** 的 `gem-3.5-flash` 模型，Gemini 原生协议（`v1beta/models/{model}:generateContent`）。

## 模型/站点信息

- BASE_URL：`https://api.lk888.ai`
- 端点：`POST /v1beta/models/gem-3.5-flash:generateContent`
- 鉴权：`Authorization: Bearer $API_KEY`
- 能力标签：多轮对话 · 多模态 · 长上下文 · 联网搜索 · 极速
- 密钥：环境变量 `GEM_VISION_API_KEY` → `~/.gem-vision/key` → 脚本同目录 `gem_vision.key`

## 配置 key

向技能提供方获取 API key。推荐在仓库目录运行 `python configure.py` 统一配置所有技能凭证（写入 `~/.claude-skills/keys.json`），也可以单独配置：

```bash
# 方式一：写入统一配置文件
python ~/.claude/skills/gem-vision/scripts/gem_vision.py --login sk-xxxxxxxx
```

```bash
# 方式二：环境变量（优先级最高）
export GEM_VISION_API_KEY=sk-xxxxxxxx
```

Windows PowerShell：

```powershell
$env:GEM_VISION_API_KEY = "sk-xxxxxxxx"
```

读取顺序：`GEM_VISION_API_KEY` → `~/.claude-skills/keys.json` 的 `gem_vision_api_key` → `~/.gem-vision/key` → 脚本同目录 `gem_vision.key`。

## 快速上手

```bash
# 0. 视频内容分析（最常用）
python gem_vision.py "这个视频讲了什么？按时间线总结，列出出现的物体" --video clip.mp4

# 1. 画面识别/文字提取（大视频提高帧数）
python gem_vision.py "提取视频里所有出现的文字（字幕、水印、口播提示）" --video long.mp4 --frames 24

# 2. 图片理解
python gem_vision.py "描述这张图，并翻译图中文字" --image photo.jpg

# 3. 纯文本 LLM
python gem_vision.py "解释一下什么是向量数据库，三句话" --system "你是技术布道师"

# 4. 带素材的多轮交互（终端里用）
python gem_vision.py "先看这个视频" --video clip.mp4 --chat
#   然后在「你>」提示符下继续追问；输入 exit / 退出 结束

# 5. 调试：看原始响应
python gem_vision.py "你好" --json
```

## 工作原理

| 场景 | 行为 |
|---|---|
| 视频 ≤ 14MB 且 mp4/mkv/mov/webm/mpeg/ts | 整段 base64 内联上传（`inlineData`），**含音轨**，可识别语音 |
| 视频更大或格式受限（avi/wmv 等） | ffmpeg/ffprobe 读取时长 → 按时长均匀抽 N 帧（默认 16，720p JPG）→ 帧图作为 `inlineData` 图片发送，并附时间点元信息 |
| 图片 | base64 内联（png/jpg/jpeg/webp/gif/bmp） |
| 纯文本 | 只发 text part |

抽帧模式下提示词自动包含：文件名、总时长、每帧对应时间点，模型据此可给出带时间位置的分析。

## 参数一览

```
prompt                    问题/指令（--chat 模式下可省略）
--login KEY               保存 API key 到 ~/.gem-vision/key
-v, --video FILE          视频路径，可重复（≤4 个），仅本地文件
-i, --image FILE          图片路径，可重复（≤14 张）
--model NAME              默认 gem-3.5-flash
--system TEXT             system instruction
--frames N                抽帧数量，默认 16
--max-inline-mb N         内联阈值 MB，默认 14
--force-frames            强制抽帧（无音轨）
--search                  启用 google_search 联网工具（视网关支持）
--temp F / --max-tokens N / --timeout S
--chat                    交互式多轮
-o, --out FILE            保存回答（chat 模式逐轮追加）
--json                    原始 JSON 输出
```

## 典型场景

- **短视频/带货视频审核**：`"检查这个视频是否含违规内容、虚假宣传话术，逐条列出"` + `--video`
- **课程/访谈总结**：`"总结主讲人的核心观点，按章节列要点"` + `--video`（≤14MB 含音轨效果好）
- **监控/风光/纪实类长视频**：`"找出出现行人的时间段"` + `--frames 30`（抽帧，无音轨）
- **字幕提取**：内联模式直接问"转写全部口播"；抽帧模式只能读画面内字幕
- **截图/漫画识读**：`"提取图中文字并翻译成中文"` + `--image`

## 故障排查

| 现象 | 处理 |
|---|---|
| `未找到 API key` | 运行 `--login` 保存 key，或设置 `GEM_VISION_API_KEY` |
| `HTTP 400 ... inlineData` | 视频超限或格式不支持，降低 `--max-inline-mb` 让它走抽帧，或压缩视频 |
| `未找到 ffmpeg` | 大视频抽帧需要 ffmpeg + ffprobe 在 PATH 中（https://ffmpeg.org 下载） |
| `无法读取视频时长` | 文件损坏或编码异常；用 ffmpeg 本地转一次码再试 |
| `HTTP 401` | key 无效或过期，重新 `--login` |
| `HTTP 429` | 脚本已自动重试；仍失败则稍后再试 |
| 回答被截断（finish=MAX_TOKENS） | 加大 `--max-tokens` |
| `--search` 报错 | 网关未透传 google_search 工具，去掉该参数 |
| 想要别的模型 | `--model gem-3.5-pro` 等（以 `GET /v1/models` 返回清单为准） |

## 已知限制

- 不支持视频 URL 直传，需本地文件（抖音/快手/B 站链接可先用 `video-download` 技能下载）。
- 抽帧模式丢失音频，无法识别语音。
- 单次内联请求约 20MB 上限，故默认阈值 14MB。
- 交互式 `--chat` 面向用户终端使用；AI 助手自动化场景直接多次单轮调用。

## 安全

- 仓库与脚本内不含任何 API key；key 保存在本机 `~/.claude-skills/keys.json`（权限 600）或环境变量中，旧的 `~/.gem-vision/key` 仍兼容读取。
- 若使用脚本同目录的 `gem_vision.key`，不要提交进任何仓库（`.gitignore` 已忽略 `*.key`）。
