#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tt_generate.py — TT Image 2 生图脚本（api.lk888.ai / Pix studio）

支持：文生图、图生图（参考图改风格/换背景/局部编辑）、多图参考合成。
流程：POST /v1/media/generate 创建任务 -> 轮询 GET /v1/media/status -> 下载 result_url。
仅依赖 Python 标准库，无需 pip 安装。

用法示例：
  python tt_generate.py --login sk-xxxxxxxx
  python tt_generate.py "一只戴眼镜的橘猫坐在窗台上看书"
  python tt_generate.py "把背景换成黄昏的海边" --ref photo.jpg --out beach.png
  python tt_generate.py "电商海报，大字标题：夏季新品五折" --size 1024x1536 --quality high -n 2
  python tt_generate.py --status 123456        # 查询历史任务状态

密钥：环境变量 TT_IMAGE_API_KEY → ~/.tt-image/key → 脚本同目录 tt_image.key。
"""

import argparse
import base64
import json
import mimetypes
import os
import re
import struct
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

BASE_URL = os.environ.get("TT_IMAGE_BASE_URL", "https://api.lk888.ai").rstrip("/")
DEFAULT_MODEL = "tt-image-2"

KEY_FILE = os.path.join(os.path.expanduser("~"), ".tt-image", "key")
LOCAL_KEY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tt_image.key")
UNIFIED_KEY_FILE = os.path.join(os.path.expanduser("~"), ".claude-skills", "keys.json")

# 官方常用尺寸枚举。注意：size 只传"宽x高"，不能传 "16:9" 这类比例写法（会 400）
SIZE_ENUM = {
    "auto", "1024x1024", "1024x1536", "1536x1024", "960x1280", "1280x960",
    "1088x1920", "1920x1088", "1024x1280", "1280x1024", "960x1920", "1920x960",
    "2048x2048", "2048x3072", "3072x2048", "1920x2560", "2560x1920",
    "1440x2560", "2560x1440", "2048x2560", "2560x2048", "1280x2560", "2560x1280",
    "2880x2880", "2304x3456", "3456x2304", "2400x3200", "3200x2400",
    "2160x3840", "3840x2160", "2560x3200", "3200x2560", "1920x3840", "3840x1920",
}

MIME_MAP = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".webp": "image/webp", ".gif": "image/gif", ".bmp": "image/bmp",
}


def out(msg):
    print(msg, flush=True)


def die(msg):
    out("[失败] %s" % msg)
    sys.exit(1)


def read_key_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def read_unified(field):
    try:
        with open(UNIFIED_KEY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return ""
    value = data.get(field, "") if isinstance(data, dict) else ""
    return str(value).strip() if value else ""


def save_unified(field, value):
    data = {}
    try:
        with open(UNIFIED_KEY_FILE, "r", encoding="utf-8") as f:
            loaded = json.load(f)
            if isinstance(loaded, dict):
                data = loaded
    except (OSError, ValueError):
        pass
    data[field] = value
    os.makedirs(os.path.dirname(UNIFIED_KEY_FILE), exist_ok=True)
    with open(UNIFIED_KEY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    try:
        os.chmod(UNIFIED_KEY_FILE, 0o600)
    except OSError:
        pass


def api_key():
    key = (
        os.environ.get("TT_IMAGE_API_KEY", "").strip()
        or read_unified("tt_image_api_key")
        or read_key_file(KEY_FILE)
        or read_key_file(LOCAL_KEY_FILE)
    )
    if not key:
        die(
            "未找到 API key。先运行：\n"
            "  python %s --login sk-xxxxxxxx\n"
            "或设置环境变量 TT_IMAGE_API_KEY。" % os.path.basename(__file__)
        )
    return key


def save_key(key):
    key = (key or "").strip()
    if not key:
        die("请提供 key，例如：python tt_generate.py --login sk-xxxxxxxx")
    save_unified("tt_image_api_key", key)
    out("key 已保存到 %s（尾号 %s）" % (UNIFIED_KEY_FILE, key[-4:]))


def http_json(method, url, api_key, payload=None, timeout=60):
    headers = {"Authorization": "Bearer %s" % api_key}
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        die("HTTP %s 请求失败: %s\n响应内容: %s" % (e.code, url, body[:800]))
    except urllib.error.URLError as e:
        die("网络请求失败: %s（检查网络/代理后重试）" % getattr(e, "reason", e))


def unwrap(resp):
    """兼容两种返回结构：{code, data, msg} 包裹 或 平铺字段。"""
    if isinstance(resp, dict):
        data = resp.get("data")
        if isinstance(data, dict) and any(k in data for k in ("task_id", "state", "is_final")):
            return data
    return resp


def to_ref(value):
    """参考图归一：http(s) URL 直接用；本地文件转 data:<mime>;base64 内联。"""
    if re.match(r"^https?://", value, re.I):
        return value
    p = Path(value)
    if not p.is_file():
        die("参考图不存在: %s" % p)
    mime = MIME_MAP.get(p.suffix.lower()) or mimetypes.guess_type(str(p))[0] or "image/png"
    b64 = base64.b64encode(p.read_bytes()).decode("ascii")
    return "data:%s;base64,%s" % (mime, b64)


def validate_size(size):
    if size in SIZE_ENUM:
        return
    m = re.fullmatch(r"(\d+)x(\d+)", size)
    if not m:
        die("size 非法: %s。须为 auto 或 '宽x高'（如 1024x1024），不能传 '16:9' 这类比例写法。" % size)
    w, h = int(m.group(1)), int(m.group(2))
    problems = []
    if w % 16 or h % 16:
        problems.append("宽和高必须是 16 的倍数")
    if max(w, h) > 3840:
        problems.append("单边不能超过 3840")
    total = w * h
    if not (655360 <= total <= 8294400):
        problems.append("总像素需在 655360~8294400 之间（当前 %d）" % total)
    if max(w, h) / min(w, h) > 3:
        problems.append("宽高比需在 1:3 ~ 3:1 之间")
    if problems:
        die("自定义尺寸 %s 不符合官方规则：%s。可改用常用枚举值，如 1024x1024 / 1024x1536 / 1536x1024 / 2048x2048。"
            % (size, "；".join(problems)))


def download(url, out_path, auto_ext):
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part")
    last_err = None
    for attempt in range(1, 4):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                                       "Chrome/120.0.0.0 Safari/537.36"},
            )
            with urllib.request.urlopen(req, timeout=300) as resp, open(tmp, "wb") as f:
                while True:
                    chunk = resp.read(1024 * 256)
                    if not chunk:
                        break
                    f.write(chunk)
            if not tmp.is_file() or tmp.stat().st_size == 0:
                raise RuntimeError("empty download")
            if auto_ext:
                head = tmp.read_bytes()[:12]
                ext = (".png" if head.startswith(b"\x89PNG")
                       else ".jpg" if head.startswith(b"\xff\xd8")
                       else ".webp" if head[:4] == b"RIFF" and head[8:12] == b"WEBP"
                       else None)
                if ext and path.suffix.lower() != ext:
                    path = path.with_suffix(ext)
            tmp.replace(path)
            return path, path.stat().st_size
        except Exception as e:
            last_err = e
            if tmp.is_file():
                tmp.unlink()
            if attempt < 3:
                out("  下载第 %d 次失败（%s），5s 后重试..." % (attempt, e))
                time.sleep(5)
    die("下载失败（已重试 3 次）: %s\n请手动从远程地址下载: %s" % (last_err, url))


def image_dims(path):
    """尽力读取 PNG/JPEG/WEBP 实际像素。size 实际只稳比例档位，像素可能与请求值不同。"""
    try:
        data = Path(path).read_bytes()
        if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= 24:
            w, h = struct.unpack(">II", data[16:24])
            return w, h
        if data[:2] == b"\xff\xd8":  # JPEG
            sof = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                   0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
            i = 2
            while i + 9 < len(data):
                if data[i] != 0xFF:
                    i += 1
                    continue
                marker = data[i + 1]
                if marker in sof:
                    h, w = struct.unpack(">HH", data[i + 5:i + 9])
                    return w, h
                if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                    i += 2
                    continue
                seglen = struct.unpack(">H", data[i + 2:i + 4])[0]
                i += 2 + seglen
        if data[:4] == b"RIFF" and data[8:12] == b"WEBP" and data[12:16] == b"VP8X" and len(data) >= 30:
            w = int.from_bytes(data[24:27], "little") + 1
            h = int.from_bytes(data[27:30], "little") + 1
            return w, h
    except Exception:
        pass
    return None


def main():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    ap = argparse.ArgumentParser(
        description="TT Image 2 生图（文生图 / 图生图 / 多图参考合成）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例：\n"
               '  python tt_generate.py --login sk-xxxxxxxx   # 保存 API key\n'
               '  python tt_generate.py "一只戴眼镜的橘猫坐在窗台上看书"\n'
               '  python tt_generate.py "把背景换成黄昏海边" --ref photo.jpg -o beach.png\n'
               '  python tt_generate.py "海报，大字：夏季新品5折" --size 1024x1536 --quality high -n 2\n'
               "  python tt_generate.py --status 123456   # 查询历史任务")
    ap.add_argument("prompt", nargs="?", help="生成提示词，推荐《主体+场景+风格+光线+氛围》结构")
    ap.add_argument("--login", metavar="KEY", help="保存 API key 到 ~/.tt-image/key 后退出")
    ap.add_argument("-o", "--out", help="输出文件路径（默认 ./tt-image-output/tt-image-<时间戳>.png）")
    ap.add_argument("-r", "--ref", action="append", default=[],
                    help="参考图：本地路径或公网 URL，可重复传，最多 14 张（图生图/局部编辑/多图融合）")
    ap.add_argument("--size", default="auto",
                    help="图片尺寸：auto（默认）或 宽x高，如 1024x1024 / 1536x1024 / 2048x2048")
    ap.add_argument("--quality", default="auto", choices=["auto", "high", "medium", "low"],
                    help="图片质量（默认 auto）")
    ap.add_argument("-n", type=int, default=1, help="生成张数（默认 1）")
    ap.add_argument("--model", default=DEFAULT_MODEL, help="模型名（默认 %s）" % DEFAULT_MODEL)
    ap.add_argument("--timeout", type=int, default=300, help="轮询超时秒数（默认 300）")
    ap.add_argument("--interval", type=int, default=4, help="轮询间隔秒数（默认 4）")
    ap.add_argument("--url-only", action="store_true", help="只输出远程结果 URL，不下载到本地")
    ap.add_argument("--status", metavar="TASK_ID", help="只查询指定任务状态，不创建新任务")
    args = ap.parse_args()

    if args.login:
        save_key(args.login)
        return

    api_key_value = api_key()

    # 只查状态模式（用于超时后追查历史任务）
    if args.status:
        st = unwrap(http_json("GET", "%s/v1/media/status?task_id=%s" % (BASE_URL, args.status), api_key_value))
        out(json.dumps(st, ensure_ascii=False, indent=2))
        return

    if not args.prompt:
        die('缺少提示词。用法: python tt_generate.py "提示词" [选项]（-h 查看全部参数）')
    if len(args.ref) > 14:
        die("参考图最多 14 张")
    validate_size(args.size)

    refs = [to_ref(r) for r in args.ref]
    payload = {
        "model": args.model,
        "prompt": args.prompt,
        "params": {"size": args.size, "quality": args.quality, "n": max(1, args.n)},
    }
    if refs:
        payload["params"]["images"] = refs

    t0 = time.time()
    mode = "图生图" if refs else "文生图"
    out("[任务提交] %s | model=%s size=%s quality=%s 参考图=%d张 n=%d"
        % (mode, args.model, args.size, args.quality, len(refs), max(1, args.n)))
    resp = unwrap(http_json("POST", "%s/v1/media/generate" % BASE_URL, api_key_value, payload))
    task_id = resp.get("task_id")
    if not task_id:
        die("创建任务失败: %s" % json.dumps(resp, ensure_ascii=False)[:600])
    out("[任务已创建] task_id=%s  开始轮询（每 %ds，最长 %ds）" % (task_id, args.interval, args.timeout))

    deadline = t0 + args.timeout
    last_line = ""
    while True:
        time.sleep(args.interval)
        st = unwrap(http_json("GET", "%s/v1/media/status?task_id=%s" % (BASE_URL, task_id), api_key_value))
        state = st.get("state") or ""
        progress = st.get("progress") or ""
        if state == "success":
            break
        if state == "failed":
            die("生成失败: %s（费用已自动退款，可调整提示词/参数后重试）"
                % (st.get("error") or st.get("status") or "未知原因"))
        if time.time() > deadline:
            die("轮询超时（%ds），任务仍在 %s。可稍后用 --status %s 继续查询（不重复扣费）。"
                % (args.timeout, state or "未知状态", task_id))
        line = ("%s %s" % (state, progress)).strip()
        if line != last_line:
            out("  ... %s  已等待 %ds" % (line or state, int(time.time() - t0)))
            last_line = line

    urls = st.get("result_url")
    if isinstance(urls, str):
        urls = [urls] if urls else []
    if not urls:
        die("任务成功但未返回结果地址: %s" % json.dumps(st, ensure_ascii=False)[:600])

    out("[生成完成] 耗时 %ds，共 %d 张" % (int(time.time() - t0), len(urls)))
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    for i, u in enumerate(urls, 1):
        if args.url_only:
            out("[URL] %s" % u)
            continue
        if args.out:
            base, ext = os.path.splitext(args.out)
            target = args.out if len(urls) == 1 else "%s-%d%s" % (base, i, ext or ".png")
        else:
            name = "tt-image-%s%s.png" % (stamp, "-%d" % i if len(urls) > 1 else "")
            target = str(Path("tt-image-output") / name)
        out("[远程地址] %s" % u)
        path, nbytes = download(u, target, auto_ext=not bool(args.out))
        dims = image_dims(path)
        dim_txt = "，实际像素 %dx%d" % dims if dims else ""
        out("[已保存] %s  (%.0f KB%s)" % (path, nbytes / 1024.0, dim_txt))
    out("[提示] size 主要决定宽高比档位，输出像素以下载文件为准；模型不支持透明底，需透明请后处理抠图。")


if __name__ == "__main__":
    main()
