# safillu-skills

Claude Code 技能合集：一个仓库放多个技能，按需安装。

| 技能 | 用途 | 需要 key |
| --- | --- | --- |
| [`safillu`](skills/safillu/SKILL.md) | 调用 Safillu 生成 AI 媒体：Z-Image 文生图、Qwen3-TTS 语音、YuE2-BGM 纯音乐、MiniMax-H3-SelfLift 视频 | 是 |
| [`tt-image`](skills/tt-image/SKILL.md) | 用 TT Image 2 生成/编辑图片：文生图、图生图、多图参考合成、海报/产品图/局部编辑 | 是 |
| [`gem-vision`](skills/gem-vision/SKILL.md) | 用 GEM 3.5 flash 分析视频/图片：内容总结、时间线、口播字幕、视频问答，也可当多模态 LLM | 是 |
| [`video-download`](skills/video-download/SKILL.md) | 抖音/快手/视频号/小红书/B站分享链去水印下载，含图集、音乐、封面 | 是（UID） |
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

需要凭证的技能：`safillu`、`tt-image`、`gem-vision`、`video-download`（`minimax-h3-prompt-optimizer` 不需要）。所有凭证统一存放在一个文件里：

```
~/.claude-skills/keys.json
```

该文件由脚本自动创建，权限 600。`tt-image` 和 `gem-vision` 走同一个网关，通常共用同一把 key。

### 统一配置（推荐）

在仓库目录运行交互式配置，按提示逐项填入，直接回车跳过：

```bash
python configure.py
```

也可以一条命令写全部：

```bash
python configure.py --safillu sk-xxxx --lk888 sk-xxxx --video-uid <UID>
```

`--lk888` 会同时写入 TT Image 2 和 GEM Vision 的 key。查看当前配置（脱敏）：

```bash
python configure.py --show
```

### 单独配置某个技能

各技能自带的登录命令也写入同一个文件，只安装了其中一个技能时也能用：

```bash
# safillu
python ~/.claude/skills/safillu/scripts/safillu.py login --key sk-xxxxxxxx

# tt-image
python ~/.claude/skills/tt-image/scripts/tt_generate.py --login sk-xxxxxxxx

# gem-vision
python ~/.claude/skills/gem-vision/scripts/gem_vision.py --login sk-xxxxxxxx

# video-download
python ~/.claude/skills/video-download/scripts/video_fetch.py --login <UID>
```

### 环境变量（可选，优先级最高）

如果需要临时覆盖或不想落盘，可用环境变量：

```powershell
$env:SAFILLU_API_KEY = "sk-xxxxxxxx"
$env:TT_IMAGE_API_KEY = "sk-xxxxxxxx"
$env:GEM_VISION_API_KEY = "sk-xxxxxxxx"
$env:VIDEO_FETCH_UID = "<UID>"
```

优先级：环境变量 > `~/.claude-skills/keys.json` > 旧的单技能 key 文件（`~/.safillu/key`、`~/.tt-image/key`、`~/.gem-vision/key`、`~/.video-download/config.json`）。

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

- 仓库内不含任何 API key 或账号 UID，请勿把自己的凭证提交进来。
- 凭证统一保存在本机 `~/.claude-skills/keys.json`（权限 600）；兼容读取旧的 `~/.safillu/key`、`~/.tt-image/key`、`~/.gem-vision/key`、`~/.video-download/config.json`，也可用环境变量覆盖。
- `safillu` 回执中的参考素材 base64 会被替换为占位符，不会把整段媒体写进 json。
- `.gitignore` 已忽略 `*.key`、回执和生成的媒体文件。

## 目录结构

```
safillu-skills/
├── .claude-plugin/marketplace.json   # 插件市场定义
├── configure.py                      # 统一配置所有技能凭证
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
