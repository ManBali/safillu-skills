# TT Image 技能 · 使用文档

> 基于 Pix studio《TT Image 2 接入文档》制作
> 让 Claude 在对话里直接帮你生成/编辑图片，也可以在命令行独立使用。

---

## 1. 这是什么

一个接入了 **TT Image 2**（`tt-image-2`）模型的生图技能。TT Image 2 是新一代旗舰图像模型，文生图 + 图生图双能力：

- 语义理解、文字渲染、复杂排版强：图表、信息图、漫画、高文字密度海报一次成型
- 支持多图参考合成（最多 14 张）、提示词引导的局部编辑、自定义分辨率（最高 2K+）
- 人脸、Logo、产品细节在多轮编辑中稳定不走样

| 项目 | 值 |
|---|---|
| 平台 | Pix studio（`https://api.lk888.ai`） |
| 模型 | `tt-image-2` |
| 鉴权 | `Authorization: Bearer <API_KEY>` |
| 出图耗时 | 通常 20 秒 ~ 2 分钟（异步任务，脚本自动轮询） |
| 计费 | 按平台模型计费；任务失败（`failed`）自动退款 |

---

## 2. 安装与配置

### 2.1 安装

把本技能目录复制到 Claude Code 的技能目录（仓库安装脚本会自动完成）：

```
~/.claude/skills/tt-image/
├── SKILL.md              # 技能定义（给 AI 看的触发与执行说明）
├── README.md             # 本文档
└── scripts/
    └── tt_generate.py    # 核心脚本（纯 Python 标准库，无需 pip 安装）
```

Windows 下即 `%USERPROFILE%\.claude\skills\tt-image\`。

- **新开的 Claude 会话**会自动加载该技能，说"帮我生成一张图"即可触发，也可用 `/tt-image <描述>` 手动调用。
- **已经开着的会话**技能列表在会话启动时就固定了，需要新开会话（或重启会话）才能在技能列表里看到它；但在旧会话里直接让 Claude 运行脚本路径也完全可以。

### 2.2 配置 API key

向技能提供方获取 API key，二选一：

```bash
# 方式一：保存到本地（推荐）
python ~/.claude/skills/tt-image/scripts/tt_generate.py --login sk-xxxxxxxx
```

```bash
# 方式二：环境变量
export TT_IMAGE_API_KEY=sk-xxxxxxxx
```

Windows PowerShell：

```powershell
$env:TT_IMAGE_API_KEY = "sk-xxxxxxxx"
```

读取顺序：`TT_IMAGE_API_KEY` → `~/.tt-image/key` → 脚本同目录 `tt_image.key`。key 不会打印完整内容，保存后只显示尾号。

---

## 3. 三种用法

### 3.1 对话式（推荐，最常用）

直接用自然语言说需求，Claude 会自动调用技能：

> 帮我生成一张竖版海报：夏日连衣裙上新，大字标题"夏季新品 5 折"，清新奶油色系，电商风
>
> 把这张照片的背景换成黄昏的海边（拖一张参考图进对话）
>
> 画一只戴眼镜的橘猫坐在窗台上看书，吉卜力风格

Claude 的标准动作是：构造提示词 → 跑脚本生成 → **用 Read 自检图片** → 把文件路径和远程 URL 交付给你。

### 3.2 斜杠命令

```
/tt-image 一张横版 banner：8月女装大促，模特穿碎花裙，暖阳氛围，右侧留白放文案
```

`$ARGUMENTS` 就是后面的描述文字。

### 3.3 命令行直接跑（不经过 AI）

```bash
python ~/.claude/skills/tt-image/scripts/tt_generate.py "一只戴眼镜的橘猫坐在窗台上看书" -o cat.png
```

---

## 4. 参数总表

| 参数 | 默认 | 说明 |
|---|---|---|
| `prompt`（第 1 个位置参数） | 必填 | 提示词，中英文皆可 |
| `--login KEY` | - | 保存 API key 到 `~/.tt-image/key` 后退出 |
| `-o, --out` | `./tt-image-output/tt-image-<时间戳>.png` | 输出文件路径；多张时自动加 `-1` `-2` 序号 |
| `-r, --ref` | 无 | 参考图，**本地路径或公网 URL**，可重复传，最多 14 张。传了就变成图生图/局部编辑/多图融合 |
| `--size` | `auto` | 图片尺寸。`auto` 或 `宽x高`，如 `1024x1024`、`1536x1024`、`1024x1536`、`2048x2048`。⚠️ **不能传 `16:9` 这种比例写法**（接口会报 400） |
| `--quality` | `auto` | `auto` / `high` / `medium` / `low` |
| `-n` | 1 | 生成张数 |
| `--model` | `tt-image-2` | 模型名 |
| `--timeout` | 300 | 轮询超时秒数 |
| `--interval` | 4 | 轮询间隔秒数（官方建议 3~5 秒） |
| `--url-only` | 关 | 只打印远程结果 URL，不下载 |
| `--status TASK_ID` | - | 只查询历史任务状态，不新建任务（超时后追查用，不会重复扣费） |

**自定义尺寸规则**（不在枚举里时脚本会本地预检）：宽高均为 16 的倍数、宽高比 1:3~3:1、总像素 65 万 ~ 829 万、单边 ≤ 3840。例如 `1024x1360`、`1792x1024` 都可以。

---

## 5. 典型场景示例

### 文生图（电商产品图）

```bash
python ~/.claude/skills/tt-image/scripts/tt_generate.py \
  "An elegant floral summer maxi dress on a mannequin, bright minimalist studio, \
   soft natural window light, beige background, professional e-commerce product photo" \
  -o dress.png --size 1024x1024
```

### 图生图：换背景 / 改风格

把本地照片作为参考图传入（本地文件会自动转 base64 上传）：

```bash
python ~/.claude/skills/tt-image/scripts/tt_generate.py \
  "把背景换成黄昏的海边沙滩，保持人物和服装不变" \
  --ref model.jpg -o model-beach.png
```

### 多图参考合成

```bash
python ~/.claude/skills/tt-image/scripts/tt_generate.py \
  "参考图 1 的连衣裙穿在参考图 2 的模特身上，影棚白底产品图" \
  --ref dress.jpg --ref model.jpg -o combo.png
```

### 高文字密度海报（该模型强项）

文字内容要**明确写进提示词**，用引号标出要渲染的字样：

```bash
python ~/.claude/skills/tt-image/scripts/tt_generate.py \
  "竖版促销海报，奶油底色配水彩花卉边框，主标题文字：\"夏季新品 5 折\"，副标题：\"全场连衣裙\"，底部小字：\"活动时间 9.20-9.30\"" \
  --size 1024x1536 --quality high -o poster.png
```

### 局部编辑

```bash
python ~/.claude/skills/tt-image/scripts/tt_generate.py \
  "只把人物手中的包换成红色皮质手提包，其余部分保持原样" \
  --ref photo.jpg -o edited.png
```

---

## 6. 提示词写作指南

推荐官方结构：**《主体 + 场景 + 风格 + 光线 + 氛围》**

| 要素 | 说明 | 示例 |
|---|---|---|
| 主体 | 画什么，越具体越好 | "一位穿碎花连衣裙的年轻女性" |
| 场景 | 在哪 / 什么背景 | "咖啡店窗边，背景虚化" |
| 风格 | 摄影风/插画风/3D 等 | "日系胶片摄影风"、"扁平插画" |
| 光线 | 光的方向和质感 | "清晨柔和侧逆光" |
| 氛围 | 情绪基调 | "宁静治愈"、"高级感" |

**实用技巧**

- 要图里的**文字**：把文案原文写进提示词并用引号包住；文字越少越稳，标题类大字成功率最高
- 要**电商产品图**：加 "professional e-commerce product photography, clean background, soft studio lighting"
- 要**多轮改图**：每次编辑都传上一轮的输出图作为 `--ref`，模型对人脸/Logo/产品细节保持较好
- 中英文都可以，英文短语混合中文文案（渲染文字用）是常用组合

---

## 7. 已知限制（官方口径）

1. **size 只稳"比例档位"，不保证像素**：价格优先渠道可能降采样（如请求 `1920x1088` 实际返回 `1280x720`）。脚本会读出实际像素并打印"实际像素 WxH"，以下载到的文件为准。追求稳定高清选官方推荐的高质量参数或更高档位尺寸。
2. **不支持透明背景**：`background`/`output_format`/alpha 等透明通道参数已于 2026-07 停止支持。提示词要求"透明底"时可能把棋盘格直接栅格化成不透明像素，结果不可控 —— **需要透明底请拿到图后自行抠图**（Photoshop、remove.bg 等）。
3. 2K/4K 出图时分辨率、比例偶尔无法精准命中，属模型已知特性。
4. 图片任务一般 20 秒 ~ 2 分钟；超时后任务仍在跑，用 `--status <task_id>` 追查即可，**不会重复扣费**。

---

## 8. 故障排查

| 现象 | 原因与处理 |
|---|---|
| `HTTP 401` | API Key 无效/过期。检查环境变量 `TT_IMAGE_API_KEY` 或 `~/.tt-image/key`，可用 `--login` 重新保存 |
| `HTTP 403` | 渠道分组白名单问题：分组名带 `-1K` 的只支持 1K 档，提交 2K/4K 尺寸会被剔除；白名单只含 `-1K` 分组时会 403。换小尺寸（如 1024x1024）再试 |
| `HTTP 400 size 非法` | size 传了 `16:9` 这类比例写法，或自定义尺寸不满足第 4 节规则 |
| `生成失败` | 任务 `state=failed`，费用已自动退款；调整提示词/参数直接重试 |
| `轮询超时` | 任务还在跑，用 `python tt_generate.py --status <task_id>` 继续查询，成功后再下载 |
| 参考图报"不存在" | 检查本地路径；Windows 路径正斜杠/反斜杠都可以 |
| 中文乱码 | 脚本已强制 UTF-8 输出；如在旧终端仍乱码，执行 `chcp 65001` 后再跑 |

**更换密钥**：优先级为 环境变量 `TT_IMAGE_API_KEY` > `~/.tt-image/key` > 脚本同目录 `tt_image.key`。也可用 `TT_IMAGE_BASE_URL` 覆盖接口地址。

---

## 9. API 速查（本技能封装的接口）

```
POST https://api.lk888.ai/v1/media/generate          创建任务
     body: { model, prompt, params: { images?, n, quality, size } }
GET  https://api.lk888.ai/v1/media/status?task_id=X  查询任务
     判定: is_final===true 为终态; state: pending/running/success/failed
     成功后从 result_url 取结果（result_type=image）
```

判定规则：只用 `is_final` / `state` 写判断；`status`/`status_group` 是给人看的中文展示字段。模型清单可查 `GET /v1/models`。

另外本平台兼容 OpenAI 图片协议（`/v1/images/generations`、`/v1/images/edits`），可把 OpenAI SDK / ComfyUI 的 `base_url` 指向 `https://api.lk888.ai` 配合同一把 Key 使用 —— 本技能未用到，留作备选。

---

## 10. 安全提示

- 仓库与脚本内不含任何 API key；key 保存在本机 `~/.tt-image/key`（权限 600）或环境变量中。
- 若使用脚本同目录的 `tt_image.key`，不要把它提交进任何仓库（`.gitignore` 已忽略 `*.key`）。
- 平台托管的 `result_url` 建议只作中转引用，重要成图以本地文件为准。
