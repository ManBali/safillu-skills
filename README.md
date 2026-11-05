# safillu-skills

Claude Code 技能合集：一个仓库放多个技能，按需安装。

| 技能 | 用途 | 需要 key |
| --- | --- | --- |
| [`safillu`](skills/safillu/SKILL.md) | 调用 Safillu 生成 AI 媒体：Z-Image 文生图、Qwen3-TTS 语音、YuE2-BGM 纯音乐、MiniMax-H3-SelfLift 视频 | 是 |
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

安装后两个技能都会启用，调用时带插件前缀，如 `/safillu-skills:safillu`。适合想用官方插件机制统一管理、自动更新的用户；只想装其中一个或想手工控制目录时，用下面的一键脚本或手动安装。

### 手动安装

把 `skills/` 下需要的技能目录整个复制到 Claude Code 的技能目录：

```
~/.claude/skills/safillu/
~/.claude/skills/minimax-h3-prompt-optimizer/
```

每个技能目录里必须有 `SKILL.md`。

## 配置 safillu 的 key

向仓库维护者获取 API key，二选一：

```bash
python ~/.claude/skills/safillu/scripts/safillu.py login --key sk-xxxxxxxx
```

或设置环境变量：

```bash
export SAFILLU_API_KEY=sk-xxxxxxxx
```

Windows PowerShell：

```powershell
$env:SAFILLU_API_KEY = "sk-xxxxxxxx"
```

验证：

```bash
python ~/.claude/skills/safillu/scripts/safillu.py models
```

`minimax-h3-prompt-optimizer` 不需要 key，装好即可用。

## 使用

安装后直接对 Claude 说需求即可，技能会被自动匹配；`safillu` 也可以显式用 `/safillu` 调用。

`safillu` 的命令行用法（不经过 Claude 也能跑）：

```bash
python skills/safillu/scripts/safillu.py image --prompt "海边灯塔，温暖夕阳" --ratio 16:9
python skills/safillu/scripts/safillu.py video --prompt "日落海岸，镜头缓慢推进"
```

完整参数、限制与注意事项见各技能自己的 `SKILL.md`。

## 更新

```bash
cd safillu-skills
git pull
./install.sh
```

安装脚本会保留你放在技能目录里的 `safillu.key`（如果你用过这种本地 key 文件）。

## 安全

- 仓库内不含任何 API key，请勿把自己的 key 提交进来。
- key 保存在本机 `~/.safillu/key`（权限 600）或环境变量中。
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
│   └── minimax-h3-prompt-optimizer/
│       ├── SKILL.md
│       └── references/*.md
└── README.md
```

新增技能时，在 `skills/` 下建一个包含 `SKILL.md` 的目录，安装脚本会自动识别。
