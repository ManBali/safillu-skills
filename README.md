# safillu-skills

Claude Code 技能合集：一个仓库放多个技能，按需安装。

| 技能 | 用途 | 需要 key |
| --- | --- | --- |
| [`safillu`](skills/safillu/SKILL.md) | 调用 Safillu 生成 AI 媒体：Z-Image 文生图、Qwen3-TTS 语音、YuE2-BGM 纯音乐、MiniMax-H3-SelfLift 视频 | 是 |
| [`tt-image`](skills/tt-image/SKILL.md) | 用 TT Image 2 生成/编辑图片：文生图、图生图、多图参考合成、海报/产品图/局部编辑 | 是 |
| [`gem-vision`](skills/gem-vision/SKILL.md) | 用 GEM 3.5 flash 分析视频/图片：内容总结、时间线、口播字幕、视频问答，也可当多模态 LLM | 是 |
| [`video-download`](skills/video-download/SKILL.md) | 抖音/快手/视频号/小红书/B站分享链去水印下载，含图集、音乐、封面 | 是（UID+接口地址） |
| [`minimax-h3-prompt-optimizer`](skills/minimax-h3-prompt-optimizer/SKILL.md) | MiniMax H3 / Hailuo 3.0 视频提示词的写作、优化与质检（格式规范、运镜、口型对准、失败诊断） | 否 |

## 安装

### 一键脚本（推荐）

```bash
git clone https://github.com/ManBali/safillu-skills.git
cd safillu-skills
./install.sh
```

Windows PowerShell：

```powershell
git clone https://github.com/ManBali/safillu-skills.git
cd safillu-skills
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

只安装其中一个：

```bash
./install.sh safillu
```

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1 safillu
```

默认安装到个人技能目录 `~/.claude/skills/`（Windows 为 `%USERPROFILE%\.claude\skills\`）；想装到某个项目，用 `-Target <项目>\.claude\skills` 或环境变量 `CLAUDE_SKILLS_DIR` 指定。安装完成后重启 Claude Code 即可生效。

### 插件市场（Claude Code 内安装）

在 Claude Code 里直接执行：

```
/plugin marketplace add ManBali/safillu-skills
/plugin install safillu-skills@safillu-skills
```

安装后全部技能都会启用，调用时带插件前缀，如 `/safillu-skills:safillu`。适合想用官方插件机制统一管理、自动更新的用户；只想装其中一个或想手工控制目录时，用下面的一键脚本或手动安装。

### 手动安装

把 `skills/` 下需要的技能目录整个复制到 Claude Code 的技能目录：

```
~/.claude/skills/safillu/
~/.claude/skills/tt-image/
~/.claude/skills/gem-vision/
~/.claude/skills/video-download/
~/.claude/skills/minimax-h3-prompt-optimizer/
```

每个技能目录里必须有 `SKILL.md`。

## 配置 key

`tt-image`、`gem-vision`、`video-download`、`safillu` 需要向仓库维护者获取凭证后配置；`minimax-h3-prompt-optimizer` 不需要 key。`tt-image` 和 `gem-vision` 走同一个网关，通常共用同一把 key。

### safillu

```bash
python ~/.claude/skills/safillu/scripts/safillu.py login --key sk-xxxxxxxx
```

或设置环境变量 `SAFILLU_API_KEY`，验证：

```bash
python ~/.claude/skills/safillu/scripts/safillu.py models
```

### tt-image

```bash
python ~/.claude/skills/tt-image/scripts/tt_generate.py --login sk-xxxxxxxx
```

或设置环境变量 `TT_IMAGE_API_KEY`。

### gem-vision

```bash
python ~/.claude/skills/gem-vision/scripts/gem_vision.py --login sk-xxxxxxxx
```

或设置环境变量 `GEM_VISION_API_KEY`。

### video-download

需要服务方分配的 UID 和接口地址：

```bash
python ~/.claude/skills/video-download/scripts/video_fetch.py --login <UID> --base <接口地址>
```

也可用环境变量 `VIDEO_FETCH_UID`、`VIDEO_FETCH_API_BASE`。

Windows PowerShell 设置环境变量：

```powershell
$env:SAFILLU_API_KEY = "sk-xxxxxxxx"
$env:TT_IMAGE_API_KEY = "sk-xxxxxxxx"
$env:GEM_VISION_API_KEY = "sk-xxxxxxxx"
$env:VIDEO_FETCH_UID = "<UID>"
$env:VIDEO_FETCH_API_BASE = "<接口地址>"
```

## 使用

安装后直接对 Claude 说需求即可，技能会被自动匹配；也可以显式调用 `/safillu`、`/tt-image`、`/gem-vision`、`/video-download`、`/minimax-h3-prompt-optimizer`。

命令行用法（不经过 Claude 也能跑）：

```bash
python skills/safillu/scripts/safillu.py image --prompt "海边灯塔，温暖夕阳" --ratio 16:9
python skills/tt-image/scripts/tt_generate.py "一只戴眼镜的橘猫坐在窗台上看书" -o cat.png
python skills/gem-vision/scripts/gem_vision.py "总结这个视频，按时间线列关键事件" --video clip.mp4
python skills/video-download/scripts/video_fetch.py "https://v.douyin.com/xxxx"
```

完整参数、限制与注意事项见各技能自己的 `SKILL.md`。

## 更新

```bash
cd safillu-skills
git pull
./install.sh
```

安装脚本会保留你放在技能目录里的本地 key 文件（`*.key`）。

## 安全

- 仓库内不含任何 API key、账号 UID 或服务地址，请勿把自己的凭证提交进来。
- key 保存在本机 `~/.safillu/key`、`~/.tt-image/key`、`~/.gem-vision/key`；video-download 的账号与接口地址保存在 `~/.video-download/config.json`（均为权限 600），也可用环境变量。
- `safillu` 回执中的参考素材 base64 会被替换为占位符，不会把整段媒体写进 json。
- `.gitignore` 已忽略 `*.key`、回执和生成的媒体文件。

## 目录结构

```
safillu-skills/
├── .claude-plugin/marketplace.json   # 插件市场定义
├── install.sh / install.ps1          # 安装脚本
├── skills/
│   ├── safillu/
│   │   ├── SKILL.md
│   │   └── scripts/safillu.py
│   ├── tt-image/
│   │   ├── SKILL.md
│   │   ├── README.md
│   │   └── scripts/tt_generate.py
│   ├── gem-vision/
│   │   ├── SKILL.md
│   │   ├── README.md
│   │   └── scripts/gem_vision.py
│   ├── video-download/
│   │   ├── SKILL.md
│   │   └── scripts/video_fetch.py
│   └── minimax-h3-prompt-optimizer/
│       ├── SKILL.md
│       └── references/*.md
└── README.md
```

新增技能时，在 `skills/` 下建一个包含 `SKILL.md` 的目录，安装脚本会自动识别。
