#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Safillu API 客户端（仅标准库，Python 3.8+）。

子命令：
  login    保存 API key 到本地（~/.safillu/key）
  models   验证 key 并列出当前可用模型
  image    文生图（Z-Image-Base）
  voice    音色设计语音（Qwen3-TTS-VoiceDesign）
  bgm      纯音乐（YuE2-BGM）
  video    视频（MiniMax-H3-SelfLift；文生/首尾帧/多模态参考）
  wait     按回执继续等待并下载（中断/超时后恢复，幂等）
  query    按回执或任务 ID 查询当前状态（不下载、不产生新任务）

Key 读取顺序：环境变量 SAFILLU_API_KEY → ~/.safillu/key → 脚本同目录 safillu.key。
四个生成子命令均为 提交→轮询→下载 一条龙；回执 json 默认落在当前目录。
提交请求发出后网络异常时绝不自动重发（可能已计费），改用 query/wait 确认。
"""
import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE_URL = os.environ.get("SAFILLU_BASE_URL") or "https://api.safillu.com"

VIDEO_RESOLUTIONS = ("480p", "768p", "1080p", "2k")
IMAGE_RATIOS = ("1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3", "21:9")
VIDEO_RATIOS = ("adaptive", "16:9", "9:16", "1:1", "4:3", "3:4", "21:9")

MAX_FILE_BYTES = 30 * 1024 * 1024   # 单个素材解码后上限
MAX_TOTAL_BYTES = 64 * 1024 * 1024  # 素材合计上限
LIMITS = {"image": 5, "audio": 3, "video": 1, "total": 9}

MIME_BY_EXT = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp",
    ".mp3": "audio/mpeg", ".wav": "audio/wav", ".flac": "audio/flac",
    ".mp4": "video/mp4", ".mov": "video/quicktime", ".avi": "video/x-msvideo", ".mkv": "video/x-matroska",
}

EXT_BY_MIME = {
    "image/png": "png", "image/jpeg": "jpg", "image/webp": "webp",
    "audio/mpeg": "mp3", "audio/flac": "flac", "audio/wav": "wav", "audio/x-wav": "wav",
    "video/mp4": "mp4",
}

VIDEO_SUBMIT_PATH = "/h3-selflift/v1/video/generateVideo"
VIDEO_STATUS_PATH = "/h3-selflift/v1/video/getVideoStatus"
VIDEO_LEGACY_SUBMIT_PATH = "/tfrouter-frames/v1/video/generateVideo"
VIDEO_LEGACY_STATUS_PATH = "/tfrouter-frames/v1/video/getVideoStatus"

SUBMIT_PATH = {
    "video": VIDEO_SUBMIT_PATH,
    "image": "/v1/tasks/runninghub-image",
    "voice": "/v1/tasks/runninghub-audio",
    "bgm": "/v1/tasks/runninghub-audio",
}
# 图片/音频统一走通用任务入口提交（请求体同各模型原生格式），
# GET /v1/tasks/{id} 查询（状态大写 QUEUED/IN_PROGRESS/SUCCESS/FAILED），
# 成品从 /v1/tasks/{id}/artifacts 取（image_1..N / audio，均带 Bearer 下载）。
# 视频使用 H3 SelfLift 两段式提交/查询，成品 artifacts 键为 video。
# 旧 tfRouter 回执仍按其原查询入口恢复，避免升级后历史任务失联。
# (轮询间隔秒, 总等待上限秒)
POLL_CONFIG = {
    "video": (10, 1800),
    "image": (5, 900),
    "voice": (5, 900),
    "bgm": (5, 900),
}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
KEY_FILE = os.path.join(os.path.expanduser("~"), ".safillu", "key")
LOCAL_KEY_FILE = os.path.join(SCRIPT_DIR, "safillu.key")
UNIFIED_KEY_FILE = os.path.join(os.path.expanduser("~"), ".claude-skills", "keys.json")


class ApiError(Exception):
    def __init__(self, status, body):
        self.status = status
        self.body = body
        super().__init__("HTTP %s: %s" % (status, body[:300]))


class TaskFailed(Exception):
    pass


class TaskTimeout(Exception):
    pass


def die(message):
    print("错误: %s" % message, file=sys.stderr)
    sys.exit(1)


def readKeyFile(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def readUnified(field):
    try:
        with open(UNIFIED_KEY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return ""
    value = data.get(field, "") if isinstance(data, dict) else ""
    return str(value).strip() if value else ""


def saveUnified(field, value):
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


def apiKey():
    key = (
        os.environ.get("SAFILLU_API_KEY", "").strip()
        or readUnified("safillu_api_key")
        or readKeyFile(KEY_FILE)
        or readKeyFile(LOCAL_KEY_FILE)
    )
    if not key:
        die(
            "未找到 API key。先在仓库目录运行 python configure.py，或运行：\n"
            "  python %s login --key sk-xxxxxxxx\n"
            "或设置环境变量 SAFILLU_API_KEY。" % os.path.basename(__file__)
        )
    return key


# Windows 控制台默认 GBK，中文 help 与提示会乱码，统一强制 UTF-8
for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8")
    except AttributeError:
        pass


def httpJson(method, path, payload=None, auth=True, timeout=120):
    headers = {"Content-Type": "application/json"}
    if auth:
        headers["Authorization"] = "Bearer " + apiKey()
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(BASE_URL + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", "replace")
            try:
                return resp.status, (json.loads(body) if body else {})
            except ValueError:
                raise ApiError(resp.status, "非 JSON 响应: " + body[:300])
    except urllib.error.HTTPError as e:
        raise ApiError(e.code, e.read().decode("utf-8", "replace"))


def download(url, outPath, auth=False):
    path = os.path.abspath(outPath)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".part"
    headers = {"User-Agent": "safillu-skill/1.0"}
    if auth:
        headers["Authorization"] = "Bearer " + apiKey()
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=600) as resp, open(tmp, "wb") as f:
            while True:
                chunk = resp.read(1024 * 256)
                if not chunk:
                    break
                f.write(chunk)
        if not os.path.isfile(tmp) or os.path.getsize(tmp) == 0:
            raise RuntimeError("empty download")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp) and not os.path.exists(path):
            os.remove(tmp)


def toDataUrl(path):
    ext = os.path.splitext(path)[1].lower()
    mime = MIME_BY_EXT.get(ext)
    if not mime:
        die("不支持的素材类型 %s（%s）。支持: %s" % (ext, path, " ".join(sorted(MIME_BY_EXT))))
    size = os.path.getsize(path)
    if size > MAX_FILE_BYTES:
        die("素材 %s 为 %.1f MiB，超过单文件 30 MiB 上限" % (path, size / 1048576))
    with open(path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("ascii")
    return "data:%s;base64,%s" % (mime, encoded)


def redact(value):
    """回执落盘前把 base64 素材替换掉，避免把整段媒体写进 json。"""
    if isinstance(value, dict):
        return {k: redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, str) and value.startswith("data:") and ";base64," in value:
        head, b64 = value.split(";base64,", 1)
        return "%s;base64,<omitted %d chars>" % (head, len(b64))
    return value


def buildReferences(args):
    if bool(args.first) != bool(args.last):
        die("首尾帧模式必须 --first 与 --last 成对提供")
    if args.first and (args.image or args.audio or args.refVideo):
        die("首尾帧不能与参考素材（--image/--audio/--ref-video）混用")

    refs = []
    total = 0
    if args.first:
        for opt, role, field in (
            (args.first, "first_frame", "image_url"),
            (args.last, "last_frame", "image_url"),
        ):
            url, size = toDataUrl(opt), os.path.getsize(opt)
            refs.append({"role": role, "type": field, field: {"url": url}})
            total += size
        return refs, total

    specs = (
        ("image", "reference_image", "image_url"),
        ("audio", "reference_audio", "audio_url"),
        ("refVideo", "reference_video", "video_url"),
    )
    for optName, role, field in specs:
        paths = getattr(args, optName) or []
        limit = LIMITS["video" if optName == "refVideo" else optName]
        if len(paths) > limit:
            die("%s 最多 %d 个" % (optName, limit))
        for p in paths:
            url, size = toDataUrl(p), os.path.getsize(p)
            refs.append({"role": role, "type": field, field: {"url": url}})
            total += size
    if len(refs) > LIMITS["total"]:
        die("参考素材合计最多 %d 个" % LIMITS["total"])
    return refs, total


def extractTaskId(kind, body):
    taskId = body.get("data") if kind == "video" else body.get("task_id")
    if not taskId:
        die("提交响应中没有任务 ID: %s" % json.dumps(body, ensure_ascii=False)[:300])
    return taskId


def videoStatusPath(endpoint=None):
    if endpoint in (VIDEO_LEGACY_SUBMIT_PATH, VIDEO_LEGACY_STATUS_PATH):
        return VIDEO_LEGACY_STATUS_PATH
    return VIDEO_STATUS_PATH


def queryTask(kind, taskId, endpoint=None):
    """返回 (state, info)。state ∈ pending|success|failed。"""
    if kind == "video":
        _, body = httpJson("POST", videoStatusPath(endpoint), {"taskICode": taskId})
        status = body.get("status")
        data = body.get("data") or {}
        if status == "success":
            return "success", {}
        if status == "failed":
            return "failed", {"failReason": str(data.get("failReason", "未知"))}
        return "pending", {}
    # image / voice / bgm 走通用任务状态
    _, body = httpJson("GET", "/v1/tasks/" + taskId)
    status = body.get("status", "")
    if status == "SUCCESS":
        return "success", {}
    if status == "FAILED":
        return "failed", {"failReason": str(body.get("fail_reason", "未知"))}
    return "pending", {}


def listArtifacts(taskId):
    _, body = httpJson("GET", "/v1/tasks/%s/artifacts" % taskId)
    return body.get("artifacts") or []


def pollTask(kind, taskId, endpoint=None):
    interval, limit = POLL_CONFIG[kind]
    start = time.time()
    transientErrors = 0
    tick = 0
    while True:
        if time.time() - start > limit:
            raise TaskTimeout(
                "已等待超过 %d 秒。任务 %s 可能仍在执行：稍后用 wait --receipt <回执文件> 继续等待" % (limit, taskId)
            )
        try:
            state, info = queryTask(kind, taskId, endpoint)
            transientErrors = 0
        except ApiError as e:
            # 429 / 临时 5xx 退避重试；其他（401/403/404 等）直接失败
            if e.status == 429 or e.status >= 500:
                transientErrors += 1
                if transientErrors >= 6:
                    raise
                time.sleep(interval * 2)
                continue
            raise
        tick += 1
        if state == "success":
            return info
        if state == "failed":
            raise TaskFailed(info.get("failReason", "未知"))
        if tick == 1 or tick % 3 == 0:
            print("  [%s] 生成中（已等 %.0f 秒）..." % (taskId[:20], time.time() - start))
        time.sleep(interval)


def receiptPath(kind, explicit):
    return explicit or ("safillu-%s-receipt-%s.json" % (kind, time.strftime("%Y%m%d-%H%M%S")))


def saveReceipt(path, receipt):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(receipt, f, ensure_ascii=False, indent=2)


def loadReceipt(path):
    if not os.path.exists(path):
        die("回执文件不存在: %s" % path)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def outputPath(kind, explicit, ext, index=None, count=1):
    if explicit:
        if count > 1:
            root, e = os.path.splitext(explicit)
            return "%s_%d%s" % (root, index, e or ("." + ext))
        return explicit
    base = "safillu-%s-%s" % (kind, time.strftime("%Y%m%d-%H%M%S"))
    if count > 1:
        base += "_%d" % index
    return base + "." + ext


def submitAndRun(kind, payload, args):
    receiptFile = receiptPath(kind, args.receipt)
    print("提交 %s 任务..." % kind)
    try:
        _, body = httpJson("POST", SUBMIT_PATH[kind], payload)
    except urllib.error.URLError as e:
        die(
            "提交请求网络异常（%s）。任务可能已创建，禁止直接重发以免重复计费；"
            "请先用 query 查询确认。" % e
        )
    taskId = extractTaskId(kind, body)
    receipt = {
        "kind": kind,
        "task_id": taskId,
        "endpoint": SUBMIT_PATH[kind],
        "query_endpoint": videoStatusPath() if kind == "video" else None,
        "submitted_at": int(time.time()),
        "request": redact(payload),
        "status": "submitted",
        "urls": [],
        "local_files": [],
    }
    saveReceipt(receiptFile, receipt)
    print("task_id=%s  回执=%s" % (taskId, receiptFile))
    runWait(kind, taskId, receiptFile, receipt, args)


def runWait(kind, taskId, receiptFile, receipt, args):
    try:
        endpoint = receipt.get("query_endpoint") or receipt.get("endpoint")
        pollTask(kind, taskId, endpoint)
        artifacts = listArtifacts(taskId)
    except (TaskFailed, TaskTimeout, ApiError) as e:
        print("失败: %s" % e, file=sys.stderr)
        print("回执已保留: %s（可用 query / wait 继续）" % receiptFile, file=sys.stderr)
        sys.exit(2)

    if kind == "video":
        wanted = [a for a in artifacts if a.get("key") == "video"]
    elif kind == "image":
        wanted = [a for a in artifacts if str(a.get("key", "")).startswith("image_")]
    else:
        wanted = [a for a in artifacts if a.get("key") == "audio"]
    if not wanted:
        die("任务成功但没有可用成品 artifacts: %s" % json.dumps(artifacts, ensure_ascii=False)[:300])

    urls, files = [], []
    for i, artifact in enumerate(wanted, 1):
        ext = EXT_BY_MIME.get(artifact.get("mime_type", ""))
        if not ext:
            ext = {"video": "mp4", "image": "png"}.get(kind, "mp3")
        out = outputPath(kind, args.out, ext, i, len(wanted))
        url = artifact.get("content_url", "")
        if not url or "localhost" in url:
            url = BASE_URL + "/v1/tasks/%s/artifacts/%s/content" % (taskId, artifact.get("key"))
        download(url, out, auth=True)
        urls.append(url)
        files.append(out)

    receipt.update({"status": "success", "artifacts": artifacts, "urls": urls, "local_files": files})
    saveReceipt(receiptFile, receipt)
    print("完成:")
    for p in files:
        print("  %s" % os.path.abspath(p))


def cmdLogin(args):
    key = (args.key or "").strip()
    if not key:
        die("请提供 --key sk-xxxxxxxx")
    saveUnified("safillu_api_key", key)
    print("key 已保存到 %s（尾号 %s）" % (UNIFIED_KEY_FILE, key[-4:]))


def cmdModels(_):
    _, body = httpJson("GET", "/v1/models")
    for m in body.get("data", []):
        print(m.get("id", ""))


def cmdVideo(args):
    if not (4 <= args.duration <= 15):
        die("duration 必须 4~15 秒")
    resolution = args.resolution.lower()
    if resolution not in VIDEO_RESOLUTIONS:
        die("resolution 仅支持 %s" % "/".join(VIDEO_RESOLUTIONS))
    if args.ratio and args.ratio not in VIDEO_RATIOS:
        die("ratio 仅支持 %s" % "/".join(VIDEO_RATIOS))

    refs, totalBytes = buildReferences(args)
    if totalBytes > MAX_TOTAL_BYTES:
        die("素材合计 %.1f MiB，超过 64 MiB 上限" % (totalBytes / 1048576))

    payload = {"model": "MiniMax-H3-SelfLift", "prompt": args.prompt}
    if args.duration != 5:
        payload["duration"] = args.duration
    if args.resolution.lower() != "768p":
        payload["resolution"] = resolution
    metadata = {}
    if args.ratio:
        metadata["ratio"] = args.ratio
    if args.seed is not None:
        metadata["seed"] = args.seed
    if refs:
        metadata["references"] = refs
    if metadata:
        payload["metadata"] = metadata
    submitAndRun("video", payload, args)


def cmdImage(args):
    if args.n and not (1 <= args.n <= 4):
        die("n 必须 1~4")
    if args.ratio and args.ratio not in IMAGE_RATIOS:
        die("ratio 仅支持 %s" % "/".join(IMAGE_RATIOS))
    payload = {"model": "Z-Image-Base", "prompt": args.prompt}
    if args.negative:
        payload["negative_prompt"] = args.negative
    if args.ratio:
        payload["ratio"] = args.ratio
    if args.resolution:
        payload["resolution"] = args.resolution
    if args.n and args.n != 1:
        payload["n"] = args.n
    if args.seed is not None:
        payload["seed"] = args.seed
    submitAndRun("image", payload, args)


def cmdVoice(args):
    payload = {
        "model": "Qwen3-TTS-VoiceDesign",
        "text": args.text,
        "voice_prompt": args.voicePrompt,
    }
    if args.speed != 0.9:
        payload["speed"] = args.speed
    if args.seed is not None:
        payload["seed"] = args.seed
    submitAndRun("voice", payload, args)


def cmdBgm(args):
    if not (1 <= args.duration <= 120):
        die("duration 必须 1~120 秒")
    payload = {"model": "YuE2-BGM", "prompt": args.prompt}
    if args.duration != 10:
        payload["duration"] = args.duration
    if args.seed is not None:
        payload["seed"] = args.seed
    submitAndRun("bgm", payload, args)


def cmdWait(args):
    receipt = loadReceipt(args.receipt)
    kind, taskId = receipt["kind"], receipt["task_id"]
    runWait(kind, taskId, args.receipt, receipt, args)


def cmdQuery(args):
    if args.receipt:
        receipt = loadReceipt(args.receipt)
        kind, taskId = receipt["kind"], receipt["task_id"]
    elif args.kind and args.taskId:
        kind, taskId = args.kind, args.taskId
    else:
        die("query 需要 --receipt 或 --kind + --task-id")
    try:
        endpoint = (
            receipt.get("query_endpoint") or receipt.get("endpoint")
            if args.receipt
            else None
        )
        state, info = queryTask(kind, taskId, endpoint)
    except ApiError as e:
        die("查询失败 HTTP %s: %s" % (e.status, e.body[:300]))
    print(json.dumps({"kind": kind, "task_id": taskId, "state": state, **info}, ensure_ascii=False, indent=2))
    if kind == "video" and state == "success":
        print("下载: %s/v1/tasks/%s/artifacts/video/content（需 Bearer，用 wait --receipt 或 curl）" % (BASE_URL, taskId))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    pLogin = sub.add_parser("login", help="保存 API key 到 ~/.safillu/key")
    pLogin.add_argument("--key", required=True, help="服务商提供的 API key")
    pLogin.set_defaults(func=cmdLogin)

    pModels = sub.add_parser("models", help="验证 key 并列出可用模型")
    pModels.set_defaults(func=cmdModels)

    pVideo = sub.add_parser("video", help="MiniMax-H3-SelfLift 视频（文生/首尾帧/参考）")
    pVideo.add_argument("--prompt", required=True, help="提示词，最长 12000 字符，非空")
    pVideo.add_argument("--duration", type=int, default=5, help="4~15 秒，默认 5")
    pVideo.add_argument("--resolution", default="768p", help="480p/768p/1080p/2k，默认 768p，大小写不敏感")
    pVideo.add_argument("--ratio", help="adaptive/16:9/9:16/1:1/4:3/3:4/21:9；省略用服务端默认（文生/参考=16:9，首尾帧=adaptive）")
    pVideo.add_argument("--seed", type=int, help="0~9007199254740991")
    pVideo.add_argument("--first", help="首帧图片路径（须与 --last 成对）")
    pVideo.add_argument("--last", help="尾帧图片路径（须与 --first 成对）")
    pVideo.add_argument("--image", action="append", help="参考图片路径，可重复，最多 5 个")
    pVideo.add_argument("--audio", action="append", help="参考音频路径，可重复，最多 3 个")
    pVideo.add_argument("--ref-video", dest="refVideo", help="参考视频路径，最多 1 个")
    pVideo.add_argument("--out", help="输出文件名，默认自动命名 .mp4")
    pVideo.add_argument("--receipt", help="回执文件名，默认自动命名")
    pVideo.set_defaults(func=cmdVideo)

    pImage = sub.add_parser("image", help="Z-Image-Base 文生图")
    pImage.add_argument("--prompt", required=True, help="提示词，最长 12000 字符")
    pImage.add_argument("--negative", help="负面提示词，最长 12000 字符")
    pImage.add_argument("--ratio", help="1:1/16:9/9:16/4:3/3:4/3:2/2:3/21:9，默认 1:1")
    pImage.add_argument("--resolution", help="1K/2K，默认 1K（长边 1024/2048）")
    pImage.add_argument("--n", type=int, help="1~4 张，默认 1")
    pImage.add_argument("--seed", type=int)
    pImage.add_argument("--out", help="输出文件名（多张自动加 _1/_2 后缀）")
    pImage.add_argument("--receipt", help="回执文件名")
    pImage.set_defaults(func=cmdImage)

    pVoice = sub.add_parser("voice", help="Qwen3-TTS-VoiceDesign 音色设计语音")
    pVoice.add_argument("--text", required=True, help="要朗读的文本，最长 4000 字符")
    pVoice.add_argument("--voice-prompt", dest="voicePrompt", required=True, help="音色/语言/情绪描述，最长 4000 字符")
    pVoice.add_argument("--speed", type=float, default=0.9, help="0.5~2，默认 0.9")
    pVoice.add_argument("--seed", type=int)
    pVoice.add_argument("--out", help="输出文件名，默认自动命名 .mp3")
    pVoice.add_argument("--receipt", help="回执文件名")
    pVoice.set_defaults(func=cmdVoice)

    pBgm = sub.add_parser("bgm", help="YuE2-BGM 纯音乐")
    pBgm.add_argument("--prompt", required=True, help="风格描述（乐器/氛围/no vocals），最长 4000 字符")
    pBgm.add_argument("--duration", type=int, default=10, help="1~120 秒，默认 10（资源上限，非计费/成品保证）")
    pBgm.add_argument("--seed", type=int)
    pBgm.add_argument("--out", help="输出文件名，默认自动命名 .flac")
    pBgm.add_argument("--receipt", help="回执文件名")
    pBgm.set_defaults(func=cmdBgm)

    pWait = sub.add_parser("wait", help="按回执继续等待并下载（幂等）")
    pWait.add_argument("--receipt", required=True, help="回执文件名")
    pWait.add_argument("--out", help="输出文件名")
    pWait.set_defaults(func=cmdWait)

    pQuery = sub.add_parser("query", help="查询任务状态（不下载、不产生新任务）")
    pQuery.add_argument("--receipt", help="回执文件名")
    pQuery.add_argument("--kind", choices=("video", "image", "voice", "bgm"))
    pQuery.add_argument("--task-id", dest="taskId")
    pQuery.set_defaults(func=cmdQuery)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
