---
name: tt-image
description: 用 TT Image 2 模型（api.lk888.ai）生成或编辑图片：文生图、图生图、多图参考合成、海报/配图/产品图/改背景/局部编辑。当用户要求"生成图片/画图/生图/画一张/做图/配图/改图/修图/P图/文生图/图生图/做海报/做banner"等图片创作需求时使用。
user-invocable: true
allowed-tools:
  - Bash(python *)
  - Bash(python3 *)
  - Read
  - Glob
---

# TT Image — AI 生图（TT Image 2）

参数：$ARGUMENTS

## 首次使用：配置 key

向技能提供方获取 API key，二选一：

```bash
# 方式一：保存到本地 key 文件（推荐）
python "<技能目录>/scripts/tt_generate.py" --login sk-xxxxxxxx

# 方式二：环境变量（优先级最高）
export TT_IMAGE_API_KEY=sk-xxxxxxxx          # Windows PowerShell: $env:TT_IMAGE_API_KEY="sk-xxxxxxxx"
```

key 读取顺序：`TT_IMAGE_API_KEY` → `~/.tt-image/key` → 脚本同目录 `tt_image.key`。

## 执行方式

核心脚本是本技能目录下的 `scripts/tt_generate.py`（纯标准库，无需 pip 安装）。安装到个人技能目录后路径通常是 `~/.claude/skills/tt-image/scripts/tt_generate.py`（Windows 为 `%USERPROFILE%\.claude\skills\tt-image\scripts\tt_generate.py`）。

流程：解析用户需求 → 构造提示词 → Bash 运行脚本 → Read 产出的图片自检 → 把文件路径（和远程 URL）告诉用户。

```bash
python "<技能目录>/scripts/tt_generate.py" "提示词" -o "输出路径.png" --ref "参考图.png" --size 1024x1024 --quality auto
```

## 参数速查

| 参数 | 说明 |
|---|---|
| 第 1 个位置参数 | 提示词，推荐《主体 + 场景 + 风格 + 光线 + 氛围》结构，中英文皆可 |
| `--login KEY` | 保存 API key 到 `~/.tt-image/key` 后退出 |
| `-o/--out` | 输出文件路径；不传则存到当前目录 `tt-image-output/` 下并按时间戳命名 |
| `-r/--ref` | 参考图（本地路径或公网 URL），可重复传最多 14 张；传了就是图生图/局部编辑/多图融合 |
| `--size` | `auto`（默认）或 `宽x高`（如 `1024x1024`、`1536x1024`、`1024x1536`、`2048x2048`）。⚠️ 只传"宽x高"，不能传 `16:9` 这类比例写法（会 400） |
| `--quality` | `auto`（默认）/ `high` / `medium` / `low` |
| `-n` | 生成张数（默认 1） |
| `--timeout` | 轮询超时秒数（默认 300；图片任务一般 20s~2min） |
| `--url-only` | 只打印远程结果 URL 不下载 |
| `--status TASK_ID` | 查询历史任务状态（轮询超时后追查用，不重复扣费） |

## 使用约定

1. **横版/竖版/方图**：用户说横版用 `1536x1024` 或 `1920x1088`，竖版用 `1024x1536` 或 `1088x1920`，方图 `1024x1024`，高清大图 `2048x2048` 等。
2. **自检**：生成后务必 Read 图片确认主体/文字正确；文字渲染错漏时改写提示词（把要求文字内容明确写进提示词）重试。
3. **输出位置**：用户没指定路径时，输出到当前工作目录的 `tt-image-output/`；在网站项目里做素材时，问清楚或放到项目合适的目录。
4. **给用户的交付信息**：本地文件路径 + 远程 URL（平台托管地址，可直接引用，但重要图以本地文件为准）。

## 已知限制（务必向用户如实说明）

- **不支持透明背景**：模型已停止支持透明通道输出，要求"透明底"结果不可控；需透明底要后处理抠图。
- **size 只稳比例**：部分渠道会降采样（如请求 1920x1088 实际返回 1280x720），以脚本报告的"实际像素"为准。
- **失败自动退款**：`state=failed` 时费用已退，调整提示词/参数直接重试即可。
- API key 不内置在脚本中：需通过 `--login` 或环境变量 `TT_IMAGE_API_KEY` 配置。

## 详细文档

完整使用文档（参数表、场景示例、提示词指南、故障排查）见本技能目录 `README.md`。
