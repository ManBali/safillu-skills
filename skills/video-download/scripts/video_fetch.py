#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""视频/图集去水印解析与下载（调用去水印 API）。

用法:
  python video_fetch.py --login <UID> --base <接口地址>   # 首次配置
  python video_fetch.py <分享链接或整段分享文本>            # 解析并下载到 ./video-download-output
  python video_fetch.py <链接> --out D:/下载               # 指定输出目录
  python video_fetch.py <链接> --no-download               # 只解析，输出直链不下载
  python video_fetch.py --quota                            # 查询账号额度

账号与接口地址：环境变量 VIDEO_FETCH_UID / VIDEO_FETCH_API_BASE →
  ~/.video-download/config.json。两者都由服务提供方分配，不要提交进仓库。
"""
import argparse
import json
import os
import re
import shutil
import sys
import time
import urllib.parse
import urllib.request

CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".video-download", "config.json")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0 Safari/537.36")


def die(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)


def load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_config(cfg):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
        f.write("\n")
    try:
        os.chmod(CONFIG_FILE, 0o600)
    except OSError:
        pass


def resolve_uid(cli_uid):
    uid = (
        (cli_uid or "").strip()
        or os.environ.get("VIDEO_FETCH_UID", "").strip()
        or str(load_config().get("uid", "")).strip()
    )
    if not uid:
        die("未配置 UID。先运行：\n  python video_fetch.py --login <UID> --base <接口地址>")
    return uid


def resolve_api_base():
    base = (
        os.environ.get("VIDEO_FETCH_API_BASE", "").strip()
        or str(load_config().get("base", "")).strip()
    )
    if not base:
        die("未配置接口地址。先运行：\n  python video_fetch.py --login <UID> --base <接口地址>")
    return base.rstrip("/")


def http_get(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read(), resp.headers.get("Content-Type", "")


def extract_url(text):
    m = re.search(r"https?://[^\s\"'<>，。]+", text or "")
    return m.group(0) if m else None


def sanitize(name):
    name = re.sub(r'[\\/:*?"<>|\r\n\t]', "_", name or "").strip(" ._")
    return name[:80] or "untitled"


def api_video(api_base, video_url, uid, type_filter=None):
    params = {"uid": uid, "url": video_url}
    if type_filter is not None:
        params["type"] = str(type_filter)
    raw, _ = http_get(api_base + "/video?" + urllib.parse.urlencode(params), timeout=90)
    return json.loads(raw.decode("utf-8", "replace").lstrip("\ufeff"))


def api_quota(api_base, uid):
    raw, _ = http_get(api_base + "/home/kaka/getUserinfo?" + urllib.parse.urlencode({"uid": uid}), timeout=30)
    return json.loads(raw.decode("utf-8", "replace").lstrip("\ufeff"))


def as_list(value):
    if not value:
        return []
    if isinstance(value, list):
        return [v for v in value if isinstance(v, str) and v.startswith("http")]
    return [p for p in re.split(r"[\s,;，；]+", str(value)) if p.startswith("http")]


def pick_ext(url, fallback):
    m = re.search(r"\.([a-zA-Z0-9]{2,5})(?:[?#].*)?$", url)
    return ("." + m.group(1).lower()) if m else fallback


def download(url, path):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=600) as resp, open(path, "wb") as f:
        shutil.copyfileobj(resp, f)
        return f.tell()


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(description="视频/图集去水印解析与下载")
    ap.add_argument("input", nargs="?", help="视频分享链接，或整段分享文本（自动提取链接）")
    ap.add_argument("--login", metavar="UID", help="保存服务方分配的 UID 到 ~/.video-download/config.json")
    ap.add_argument("--base", metavar="URL", help="接口地址；与 --login 一起保存，或单独更新")
    ap.add_argument("--out", default="./video-download-output", help="输出目录（默认 ./video-download-output）")
    ap.add_argument("--uid", default=None, help="临时覆盖 UID（默认读环境变量/配置文件）")
    ap.add_argument("--type", type=int, default=None, choices=(1, 2), help="强制 1=视频 2=图集（一般不用传）")
    ap.add_argument("--no-download", action="store_true", help="只解析，不下载")
    ap.add_argument("--no-music", action="store_true", help="跳过音乐下载")
    ap.add_argument("--no-cover", action="store_true", help="跳过封面下载")
    ap.add_argument("--quota", action="store_true", help="查询账号使用情况（不消耗次数）")
    args = ap.parse_args()

    if args.login or args.base:
        cfg = load_config()
        if args.login:
            cfg["uid"] = args.login.strip()
        if args.base:
            cfg["base"] = args.base.strip().rstrip("/")
        save_config(cfg)
        print("已保存到 %s" % CONFIG_FILE)
        if not cfg.get("base"):
            print("提示：还没有配置接口地址，请补上 --base <接口地址>")
        return 0

    uid = resolve_uid(args.uid)
    api_base = resolve_api_base()

    if args.quota:
        print(json.dumps(api_quota(api_base, uid), ensure_ascii=False, indent=2))
        return 0
    if not args.input:
        ap.error("需要提供视频链接，或使用 --quota 查询额度")

    url = extract_url(args.input)
    if not url:
        print("错误：输入中未找到 http(s) 链接", file=sys.stderr)
        return 1

    result = api_video(api_base, url, uid, args.type)
    code = str(result.get("code", ""))
    if code != "101" or not isinstance(result.get("data"), dict):
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    data = result["data"]
    pics = as_list(data.get("pics"))
    print("解析成功：%s" % data.get("title", ""))
    print(json.dumps({
        "type": data.get("type"),
        "title": data.get("title", ""),
        "url": data.get("url") or None,
        "pics": pics or None,
        "music": data.get("music") or None,
        "cover": data.get("cover") or None,
    }, ensure_ascii=False, indent=2))

    if args.no_download:
        return 0

    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)
    title = sanitize(data.get("title") or ("video_%s" % time.strftime("%Y%m%d_%H%M%S")))
    saved = []
    try:
        if pics:
            for i, p in enumerate(pics, 1):
                path = os.path.join(out, "%s_%02d%s" % (title, i, pick_ext(p, ".jpg")))
                download(p, path)
                saved.append(path)
        if data.get("url"):
            path = os.path.join(out, title + pick_ext(data["url"], ".mp4"))
            download(data["url"], path)
            saved.append(path)
        if data.get("music") and not args.no_music:
            path = os.path.join(out, title + "_audio" + pick_ext(data["music"], ".mp3"))
            download(data["music"], path)
            saved.append(path)
        if data.get("cover") and not args.no_cover:
            path = os.path.join(out, title + "_cover" + pick_ext(data["cover"], ".jpg"))
            download(data["cover"], path)
            saved.append(path)
    except Exception as e:
        print("下载出错：%s" % e, file=sys.stderr)
        for p in saved:
            print("  已保存 %s" % p, file=sys.stderr)
        return 3

    for p in saved:
        print("已保存 %s (%.1f MB)" % (p, os.path.getsize(p) / 1048576.0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
