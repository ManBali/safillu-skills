#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gem_vision.py — GEM 3.5 flash 视频分析 / 多模态问答（api.lk888.ai · Pix studio · Gemini 原生协议）

用途：
  1) 视频分析识别：小视频整段内联上传（含音轨，可识别语音口播），大视频自动 ffmpeg 均匀抽帧；
  2) 图片理解 / 纯文本 LLM 问答；--chat 进入交互式多轮对话；--system 设定角色。

用法示例：
  python gem_vision.py --login sk-xxxxxxxx
  python gem_vision.py "这个视频里发生了什么？按时间线总结并列出出现的物体" --video clip.mp4
  python gem_vision.py "识别视频里的产品型号和口播要点" --video big.mp4 --frames 20
  python gem_vision.py "描述这张图片的内容" --image photo.jpg
  python gem_vision.py "用一句话解释最速降线" --system "你是物理老师，回答精炼"
  python gem_vision.py "总结这个视频" --video clip.mp4 --chat   # 带素材进入交互式多轮对话

密钥：环境变量 GEM_VISION_API_KEY → ~/.gem-vision/key → 脚本同目录 gem_vision.key。
仅依赖 Python 标准库；ffmpeg/ffprobe 仅在"大视频抽帧"时需要。
"""

import argparse
import base64
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL = os.environ.get("GEM_VISION_BASE_URL", "https://api.lk888.ai").rstrip("/")
DEFAULT_MODEL = "gem-3.5-flash"

KEY_FILE = os.path.join(os.path.expanduser("~"), ".gem-vision", "key")
LOCAL_KEY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gem_vision.key")

# 可整段内联上传的视频 MIME（Gemini 官方支持集）
INLINE_VIDEO_MIME = {
    ".mp4": "video/mp4", ".m4v": "video/mp4", ".webm": "video/webm",
    ".mov": "video/quicktime", ".mkv": "video/x-matroska",
    ".mpeg": "video/mpeg", ".mpg": "video/mpeg", ".ts": "video/mp2t",
}
IMAGE_MIME = {
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


def api_key():
    key = (
        os.environ.get("GEM_VISION_API_KEY", "").strip()
        or read_key_file(KEY_FILE)
        or read_key_file(LOCAL_KEY_FILE)
    )
    if not key:
        die(
            "未找到 API key。先运行：\n"
            "  python %s --login sk-xxxxxxxx\n"
            "或设置环境变量 GEM_VISION_API_KEY。" % os.path.basename(__file__)
        )
    return key


def save_key(key):
    key = (key or "").strip()
    if not key:
        die("请提供 key，例如：python gem_vision.py --login sk-xxxxxxxx")
    os.makedirs(os.path.dirname(KEY_FILE), exist_ok=True)
    with open(KEY_FILE, "w", encoding="utf-8") as f:
        f.write(key + "\n")
    try:
        os.chmod(KEY_FILE, 0o600)
    except OSError:
        pass
    out("key 已保存到 %s（尾号 %s）" % (KEY_FILE, key[-4:]))


def http_json(method, url, api_key, payload=None, timeout=300, retries=2):
    headers = {"Authorization": "Bearer %s" % api_key, "Content-Type": "application/json"}
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            if e.code in (429, 500, 502, 503) and attempt < retries:
                out("  HTTP %s，4s 后重试 (%d/%d)..." % (e.code, attempt + 1, retries))
                time.sleep(4)
                continue
            die("HTTP %s 请求失败: %s\n响应: %s" % (e.code, url, body[:800]))
        except urllib.error.URLError as e:
            die("网络请求失败: %s（检查网络/代理后重试）" % getattr(e, "reason", e))
    die("请求失败（重试耗尽）")


def inline_part(path, mime_map):
    p = Path(path)
    mime = mime_map.get(p.suffix.lower()) or mimetypes.guess_type(str(p))[0]
    if not mime:
        die("无法识别文件类型: %s" % p)
    b64 = base64.b64encode(p.read_bytes()).decode("ascii")
    return {"inlineData": {"mimeType": mime, "data": b64}}


def media_duration(path):
    """读视频时长（秒）。ffprobe 优先，失败则解析 ffmpeg stderr 的 Duration。"""
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", str(path)],
            capture_output=True, timeout=30)
        val = (r.stdout or b"").decode("utf-8", "replace").strip()
        if val:
            return float(val.splitlines()[0])
    except Exception:
        pass
    try:
        r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path)],
                           capture_output=True, timeout=60)
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)",
                      (r.stderr or b"").decode("utf-8", "replace"))
        if m:
            return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    except Exception:
        pass
    return 0.0


def require_ffmpeg(max_inline_mb):
    for tool in ("ffmpeg", "ffprobe"):
        if shutil.which(tool) is None:
            die("视频过大需要 ffmpeg 抽帧，但未找到 %s。请安装 ffmpeg 后重试，"
                "或改用 <= %d MB 的视频文件（可整段上传）。" % (tool, max_inline_mb))


def extract_frames(video, n, out_dir):
    """按时长均匀抽 n 帧（720p JPG），返回 (时长秒, [(时间, 帧路径), ...])"""
    duration = media_duration(video)
    if duration <= 0:
        die("无法读取视频时长（%s），请确认文件能被 ffmpeg 解析。" % video)
    n = max(1, n)
    stamps = []
    for i in range(n):
        t = duration * (i + 0.5) / n
        fp = out_dir / ("frame_%03d.jpg" % (i + 1))
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error",
               "-ss", "%.2f" % t, "-i", str(video),
               "-frames:v", "1", "-q:v", "3", "-vf", "scale=-2:720", str(fp)]
        try:
            subprocess.run(cmd, capture_output=True, timeout=120)
        except subprocess.TimeoutExpired:
            out("  第 %d 帧抽帧超时，跳过" % (i + 1))
            continue
        if fp.exists() and fp.stat().st_size > 0:
            stamps.append((t, fp))
        else:
            out("  第 %d 帧（%.1fs）抽取失败，跳过" % (i + 1, t))
    if not stamps:
        die("所有帧抽取失败，请检查视频文件是否损坏。")
    return duration, stamps


def video_parts(path, max_inline_mb, frames_n, force_frames, tmp_root):
    """视频 -> contents parts。小且格式支持则整段内联（含音轨），否则 ffmpeg 抽帧。"""
    p = Path(path)
    if not p.is_file():
        die("视频不存在: %s" % p)
    size_mb = p.stat().st_size / 1024.0 / 1024.0
    mime = INLINE_VIDEO_MIME.get(p.suffix.lower())
    if not force_frames and mime and size_mb <= max_inline_mb:
        out("  视频 %.1f MB <= %d MB，整段内联上传（含音轨）" % (size_mb, max_inline_mb))
        return [inline_part(p, INLINE_VIDEO_MIME)]
    require_ffmpeg(max_inline_mb)
    sub = re.sub(r"[^\w-]", "_", p.stem)[:40] or "video"
    frame_dir = tmp_root / ("frames-%s" % sub)
    frame_dir.mkdir(exist_ok=True)
    duration, stamps = extract_frames(p, frames_n, frame_dir)
    ts_txt = "、".join("%.1fs" % t for t, _ in stamps)
    meta = ("[视频信息] 文件: %s；时长: %.1f 秒；模式: ffmpeg 均匀抽帧（无音轨）。"
            "下方共 %d 帧 JPG，按时间顺序排列，对应时间点: %s。"
            "帧与帧之间的画面未展示；如需更精确的时间定位，请提高 --frames 或分段提问。"
            % (p.name, duration, len(stamps), ts_txt))
    out("  视频 %.1f MB 过大/格式受限，ffmpeg 抽帧 %d 张（时长 %.1fs）" % (size_mb, len(stamps), duration))
    return [{"text": meta}] + [inline_part(fp, IMAGE_MIME) for _, fp in stamps]


def build_contents(prompt, videos, images, max_inline_mb, frames, force_frames, tmp_root):
    parts = []
    if prompt:
        parts.append({"text": prompt})
    for img in images:
        ip = Path(img)
        if not ip.is_file():
            die("图片不存在: %s" % ip)
        parts.append(inline_part(ip, IMAGE_MIME))
    for v in videos:
        parts.extend(video_parts(v, max_inline_mb, frames, force_frames, tmp_root))
    if not parts:
        die("没有可发送的内容：需要 提示词 / --video / --image 至少其一。")
    return [{"role": "user", "parts": parts}]


def parse_response(resp):
    cands = resp.get("candidates") or []
    if not cands:
        pf = resp.get("promptFeedback") or {}
        die("请求被拒或无结果: %s" % (pf.get("blockReason") or json.dumps(resp, ensure_ascii=False)[:500]))
    cand = cands[0]
    parts = (cand.get("content") or {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts if isinstance(p, dict))
    return text, cand.get("finishReason"), resp.get("usageMetadata") or {}


def ask(key, model, contents, args):
    payload = {"contents": contents}
    if args.system:
        payload["systemInstruction"] = {"parts": [{"text": args.system}]}
    cfg = {}
    if args.temp is not None:
        cfg["temperature"] = args.temp
    if args.max_tokens:
        cfg["maxOutputTokens"] = args.max_tokens
    if cfg:
        payload["generationConfig"] = cfg
    if args.search:
        payload["tools"] = [{"google_search": {}}]
    url = "%s/v1beta/models/%s:generateContent" % (BASE_URL, model)
    resp = http_json("POST", url, api_key, payload, timeout=args.timeout)
    if args.json:
        out(json.dumps(resp, ensure_ascii=False, indent=2))
        sys.exit(0)
    return parse_response(resp)


def print_answer(text, finish, usage):
    if not text:
        die("模型未返回文本（finishReason=%s）" % (finish or "未知"))
    out(text)
    out("")
    out("[用量] 输入 %s / 输出 %s / 总计 %s tokens；finish=%s"
        % (usage.get("promptTokenCount", "?"), usage.get("candidatesTokenCount", "?"),
           usage.get("totalTokenCount", "?"), finish))


def main():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    ap = argparse.ArgumentParser(
        description="GEM 3.5 flash 视频分析 / 多模态问答（Gemini 原生协议）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例：\n"
               '  python gem_vision.py "按时间线总结这个视频" --video clip.mp4\n'
               '  python gem_vision.py "识别口播要点" --video big.mp4 --frames 20\n'
               '  python gem_vision.py "描述这张图" --image photo.jpg\n'
               '  python gem_vision.py "总结视频" --video clip.mp4 --chat')
    ap.add_argument("prompt", nargs="?", help="问题/指令；--chat 模式下可省略")
    ap.add_argument("--login", metavar="KEY", help="保存 API key 到 ~/.gem-vision/key 后退出")
    ap.add_argument("-v", "--video", action="append", default=[], metavar="FILE",
                    help="视频文件路径，可重复（最多 4 个）")
    ap.add_argument("-i", "--image", action="append", default=[], metavar="FILE",
                    help="图片文件路径，可重复（最多 14 张）")
    ap.add_argument("--model", default=DEFAULT_MODEL, help="模型名（默认 %s）" % DEFAULT_MODEL)
    ap.add_argument("--system", help="system instruction（角色/风格/规则）")
    ap.add_argument("--frames", type=int, default=16, help="大视频抽帧数量（默认 16）")
    ap.add_argument("--max-inline-mb", type=int, default=14,
                    help="整段内联上传的大小阈值 MB（默认 14）")
    ap.add_argument("--force-frames", action="store_true",
                    help="即使视频够小也强制抽帧（更快更省，但无音轨）")
    ap.add_argument("--search", action="store_true",
                    help="启用联网搜索工具 google_search（网关不支持时去掉本参数）")
    ap.add_argument("--temp", type=float, default=None, help="temperature")
    ap.add_argument("--max-tokens", type=int, default=None, help="maxOutputTokens")
    ap.add_argument("--timeout", type=int, default=300, help="请求超时秒数（默认 300）")
    ap.add_argument("--chat", action="store_true", help="交互式多轮对话（首次运行时可带素材作首轮）")
    ap.add_argument("-o", "--out", help="把回答保存到该文件（chat 模式下逐轮追加）")
    ap.add_argument("--json", action="store_true", help="输出原始 JSON 响应（调试用）")
    args = ap.parse_args()

    if args.login:
        save_key(args.login)
        return

    key = api_key()
    if len(args.video) > 4:
        die("视频最多 4 个")
    if len(args.image) > 14:
        die("图片最多 14 张")

    tmp_root = Path(tempfile.mkdtemp(prefix="gem-vision-"))
    try:
        contents = build_contents(args.prompt, args.video, args.image,
                                  args.max_inline_mb, args.frames, args.force_frames, tmp_root)

        if args.chat:
            history = contents
            text, finish, usage = ask(key, args.model, history, args)
            out("[回答]")
            print_answer(text, finish, usage)
            if args.out:
                _append_transcript(args.out, args.prompt, text)
            history.append({"role": "model", "parts": [{"text": text}]})
            while True:
                try:
                    line = input("\n你> ").strip()
                except (EOFError, KeyboardInterrupt):
                    out("")
                    break
                if line in ("exit", "quit", "q", "退出"):
                    break
                if not line:
                    continue
                history.append({"role": "user", "parts": [{"text": line}]})
                text, finish, usage = ask(key, args.model, history, args)
                out("[回答]")
                print_answer(text, finish, usage)
                if args.out:
                    _append_transcript(args.out, line, text)
                history.append({"role": "model", "parts": [{"text": text}]})
        else:
            text, finish, usage = ask(key, args.model, contents, args)
            print_answer(text, finish, usage)
            if args.out:
                Path(args.out).parent.mkdir(parents=True, exist_ok=True)
                Path(args.out).write_text(text, encoding="utf-8")
                out("[已保存] %s" % args.out)
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)


def _append_transcript(path, question, answer):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write("## 你\n\n%s\n\n## 模型\n\n%s\n\n" % (question, answer))


if __name__ == "__main__":
    main()
