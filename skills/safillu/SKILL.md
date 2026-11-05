---
name: safillu
description: 调用 Safillu 生成 AI 媒体：Z-Image 文生图、Qwen3-TTS 音色设计语音、YuE2-BGM 纯音乐、MiniMax-H3-SelfLift 视频（文生/首尾帧/多模态参考）。客户端脚本覆盖 提交→轮询→下载 全流程，仅依赖 Python 标准库。用户要求"生成图片/配图/语音/配音/BGM/背景音乐/生成视频/文生视频/首尾帧"等媒体制作时使用。
user-invocable: true
allowed-tools:
  - Bash(python *)
  - Read
  - Write
---

# safillu — AI 媒体生成（图片 / 语音 / BGM / 视频）

服务：`https://api.safillu.com`。脚本 `scripts/safillu.py`（下文记作 `$SF`），仅标准库，Python 3.8+；Windows 上用 `python`，macOS/Linux 上 `python3` 均可。

## 首次使用：配置 key

向服务提供方获取 API key。推荐在仓库目录运行 `python configure.py` 统一配置所有技能凭证（写入 `~/.claude-skills/keys.json`）。也可以单独配置：

```bash
# 方式一：写入统一配置文件
python "$SF" login --key sk-xxxxxxxx

# 方式二：环境变量（优先级最高）
export SAFILLU_API_KEY=sk-xxxxxxxx            # Windows PowerShell: $env:SAFILLU_API_KEY="sk-xxxxxxxx"
```

key 读取顺序：`SAFILLU_API_KEY` → `~/.claude-skills/keys.json` 的 `safillu_api_key` → `~/.safillu/key` → 脚本同目录 `safillu.key`。验证：

```bash
python "$SF" models
```

## 模型与耗时速查

| 用途 | model | 耗时参考 |
| --- | --- | --- |
| 文生图 | Z-Image-Base | 1~3 min |
| 音色语音 | Qwen3-TTS-VoiceDesign | ~2 min |
| 纯音乐 | YuE2-BGM | 1~2 min |
| 视频 | MiniMax-H3-SelfLift | 5~15 min |

提交即预扣额度，失败退款；查询状态不产生新任务。具体计费以服务端返回为准。

## 调用 demo

```bash
SF="<skill目录>/scripts/safillu.py"

# 1. 文生图：1K 16:9 两张 → safillu-image-*.png
python "$SF" image --prompt "海边灯塔，温暖夕阳，电影摄影" --ratio 16:9 --n 2

# 2. 音色设计语音 → safillu-voice-*.mp3
python "$SF" voice --text "你好，欢迎来到影幻。" --voice-prompt "温柔自然的成年女声，标准普通话，语气亲切放松"

# 3. BGM 纯音乐 → safillu-bgm-*.flac
python "$SF" bgm --prompt "Instrumental chill pop, warm electric piano, no vocals." --duration 10

# 4. 文生视频 768p 5s → safillu-video-*.mp4
python "$SF" video --prompt "日落海岸，镜头缓慢推进，海浪自然翻涌，无字幕"

# 5. 首尾帧视频：--first/--last 必须成对，不能再传参考素材
python "$SF" video --prompt "自然过渡" --first first.png --last last.png

# 6. 多模态参考：图≤5 + 音频≤3 + 视频≤1，合计≤9
python "$SF" video --prompt "参考场景和运动生成连贯镜头" --image scene.png --audio voice.mp3 --ref-video motion.mp4

# 7. 中断/超时后恢复：用回执继续等待并下载（幂等，不会重新提交）
python "$SF" wait --receipt safillu-video-receipt-20261027-153000.json

# 8. 只查状态不下载（提交结果不明时先用它确认，防重复计费）
python "$SF" query --receipt safillu-video-receipt-20261027-153000.json
python "$SF" query --kind image --task-id task_xxx
```

四个生成命令共用 `--out`（输出文件名）与 `--receipt`（回执 json，默认 `safillu-<类型>-receipt-<时间戳>.json` 落在当前目录）。成功输出本地绝对路径；失败退出码 2，回执保留可继续 `wait`。

## 参数边界

**Z-Image 文生图**：ratio 8 种（1:1/16:9/9:16/4:3/3:4/3:2/2:3/21:9）；resolution 1K/2K（长边 1024/2048，短边按比例取 16 倍数）；n 1~4；负面词非空时 CFG=2。纯文生，无参考图。

**Qwen3-TTS 语音**：text 与 voice_prompt 均非空且 ≤4000 字符；speed 0.5~2（默认 0.9）。**没有 voice_id**——音色一致性只能靠固定 voice_prompt 描述 + seed；长文本按完整句子拆分多次生成（单次有 2048 token 上限）。

**YuE2-BGM**：prompt 描述乐器/速度/氛围并写明 no vocals；duration 1~120s 是资源上限，实际时长以成品为准。

**MiniMax-H3-SelfLift 视频**：
- duration 4~15s 默认 5；resolution 480p/768p/1080p/2k（默认 768p，大小写不敏感）
- ratio：文生/参考默认 16:9 且拒收 adaptive；首尾帧默认 adaptive（省略 `--ratio` 即可）
- 素材通过 Base64 上传：图片 png/jpeg/webp、音频 mp3/wav/flac、视频 mp4/mov/avi/mkv；单文件 ≤30MiB、合计 ≤64MiB
- 参考视频只用画面，需要声音参考另传 `--audio`
- 生成音轨恒为开启，不支持关闭

## 坑位与纪律

1. **绝不重发提交**：提交请求网络超时后任务可能已创建并计费。结果不明时先 `query` 确认，再决定 `wait` 还是重新提交。脚本已内置此保护。
2. **HTTP 200 ≠ 成功**：网关异常时可能返回 HTML 页面。终态看业务字段：通用任务大写 `SUCCESS/FAILED` + `fail_reason`；视频小写 `success/failed` + `data.failReason`。脚本已处理。
3. **成品一律走 artifacts**：`GET /v1/tasks/{id}/artifacts` 列出成品（图片键 `image_1..N`、音频键 `audio`、视频键 `video`），下载 `/artifacts/{key}/content` 带 Bearer。不要依赖响应里的直链。
4. **任务 ID 与查询入口必须匹配**：SelfLift 视频用 `/h3-selflift/v1/video/getVideoStatus`；旧 tfRouter 回执用旧入口；`/v1/tasks/*` 提交的任务用 `GET /v1/tasks/{task_id}`。拿错入口会 404/500。脚本按回执自动选择。
5. **轮询节奏**：视频 10s/上限 30min，图片音频 5s/上限 15min；429/5xx 自动退避。超过上限用 `wait` 恢复，不要重新提交。
6. **URL 输入不支持**：视频端点只收 Base64 Data URL，脚本只收本地文件路径；HTTP 素材需先下载到本地。
7. 回执与生成文件都会落在当前目录，注意别把回执或 key 文件提交进任何仓库。

## 安全

- key 只存在本机 `~/.safillu/key` 或环境变量中；脚本不会打印完整 key，上传/下载均通过 HTTPS。
- 回执中的参考素材 base64 会被替换为占位符，不会把整段媒体写进 json。
