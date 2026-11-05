# safillu-skills

面向 Claude Code / 命令行的 [Safillu](https://api.safillu.com) 媒体生成技能：一个零依赖 Python 脚本，覆盖「提交 → 轮询 → 下载」全流程。

支持：

| 能力 | 模型 | 产物 |
| --- | --- | --- |
| 文生图 | Z-Image-Base | png（1K / 2K，1~4 张） |
| 音色设计语音 | Qwen3-TTS-VoiceDesign | mp3 |
| 纯音乐 / BGM | YuE2-BGM | flac |
| 视频（文生 / 首尾帧 / 多模态参考） | MiniMax-H3-SelfLift | mp4（480p~2k，4~15s） |

## 安装

### 作为 Claude Code 技能（推荐）

克隆到个人技能目录（所有项目可用）：

```bash
git clone https://github.com/ManBali/safillu-skills.git ~/.claude/skills/safillu
```

Windows PowerShell：

```powershell
git clone https://github.com/ManBali/safillu-skills.git "$env:USERPROFILE\.claude\skills\safillu"
```

也可以只装到某个项目：把仓库克隆到该项目的 `.claude/skills/safillu`。

装好后重启 Claude Code，技能会自动被发现；提到「生成图片 / 配音 / BGM / 视频」时会自动调用，也可以直接 `/safillu`。

更新：

```bash
git -C ~/.claude/skills/safillu pull
```

### 作为普通命令行工具

不需要 Claude，直接用 Python 跑：

```bash
git clone https://github.com/ManBali/safillu-skills.git
python safillu-skills/scripts/safillu.py --help
```

要求 Python 3.8+，无需 `pip install`。

## 配置 key

向仓库维护者获取 API key，然后二选一：

```bash
python scripts/safillu.py login --key sk-xxxxxxxx
```

或设置环境变量：

```bash
export SAFILLU_API_KEY=sk-xxxxxxxx
```

Windows PowerShell：

```powershell
$env:SAFILLU_API_KEY = "sk-xxxxxxxx"
```

key 读取顺序：`SAFILLU_API_KEY` → `~/.safillu/key` → 脚本同目录 `safillu.key`。验证：

```bash
python scripts/safillu.py models
```

## 快速上手

```bash
SF=scripts/safillu.py

python "$SF" image --prompt "海边灯塔，温暖夕阳，电影摄影" --ratio 16:9 --n 2
python "$SF" voice --text "你好，欢迎回来。" --voice-prompt "温柔自然的成年女声，标准普通话"
python "$SF" bgm  --prompt "Instrumental chill pop, warm electric piano, no vocals." --duration 10
python "$SF" video --prompt "日落海岸，镜头缓慢推进，海浪自然翻涌，无字幕"
python "$SF" video --prompt "自然过渡" --first first.png --last last.png
```

每个生成命令都会写一份回执 `safillu-<类型>-receipt-<时间戳>.json`；中断后用 `wait --receipt` 恢复，用 `query` 只查状态，不会重复提交或重复计费。

完整参数、限制与注意事项见 [SKILL.md](SKILL.md)。

## 安全

- 仓库内不含任何 API key，请勿把自己的 key 提交进来。
- key 保存在本机 `~/.safillu/key`（权限 600）或环境变量中。
- 回执中的参考素材 base64 会被替换为占位符，不会把整段媒体写进 json。
- `.gitignore` 已忽略 `*.key`、回执和生成的媒体文件。

## 目录结构

```
safillu-skills/
├── SKILL.md              # Claude Code 技能定义与完整用法
├── README.md
├── .gitignore
└── scripts/
    └── safillu.py        # 唯一脚本，仅标准库
```
