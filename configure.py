#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统一配置本仓库各技能的凭证（一个文件管全部）。

配置文件：~/.claude-skills/keys.json（权限 600），可用 --file 或
环境变量 SKILLS_CONFIG_FILE 指向别处。

用法：
  python configure.py                      # 交互式逐项配置（回车跳过，输入 - 清除）
  python configure.py --show               # 查看已配置项（脱敏）
  python configure.py --safillu sk-xxxx --lk888 sk-xxxx --video-uid <UID>
  python configure.py --video-base http://host:port

字段：
  safillu_api_key          Safillu 网关 key
  tt_image_api_key         TT Image 2 key
  gem_vision_api_key       GEM Vision key
  video_download_uid       video-download 账号 UID
  video_download_api_base  video-download 接口地址（可选，有内置默认值）

优先级（各技能脚本）：环境变量 > 本文件 > 各技能旧的本地 key 文件。
"""
import argparse
import getpass
import json
import os
import sys

DEFAULT_FILE = os.path.join(os.path.expanduser("~"), ".claude-skills", "keys.json")

# (字段, 说明, 是否敏感)
FIELDS = [
    ("safillu_api_key", "Safillu API key", True),
    ("tt_image_api_key", "TT Image 2 API key", True),
    ("gem_vision_api_key", "GEM Vision API key", True),
    ("video_download_uid", "video-download UID", False),
    ("video_download_api_base", "video-download 接口地址（可选，默认已内置，回车跳过）", False),
]


def load(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save(path, data):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def masked(value):
    value = str(value or "")
    if not value:
        return "未配置"
    return "已配置（尾号 %s）" % value[-4:]


def show(path, data):
    print("配置文件：%s" % path)
    print("（环境变量优先级更高，设置后会覆盖这里的值）")
    print()
    for field, label, _ in FIELDS:
        print("  %-24s %s" % (field, masked(data.get(field))))
    print()


def ask(prompt, secret):
    if secret:
        try:
            return getpass.getpass(prompt)
        except (EOFError, KeyboardInterrupt):
            raise
    try:
        return input(prompt)
    except EOFError:
        return ""


def can_prompt():
    """能否安全地交互输入：真实控制台或 Git Bash 等伪终端；NUL 重定向返回 False。"""
    if not sys.stdin.isatty():
        return False
    if os.name != "nt":
        return True
    try:
        import ctypes
        import msvcrt
        handle = msvcrt.get_osfhandle(sys.stdin.fileno())
        mode = ctypes.c_uint()
        if ctypes.windll.kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return True
        # Windows 的 NUL 设备会被 isatty 误判成终端；Git Bash 的伪终端是管道
        return ctypes.windll.kernel32.GetFileType(handle) == 3  # FILE_TYPE_PIPE
    except Exception:
        return True


def interactive(path, data):
    if not can_prompt():
        print("当前不是交互式终端，无法逐项输入。请改用参数方式，例如：")
        print("  python configure.py --safillu sk-xxxx --lk888 sk-xxxx --video-uid <UID>")
        sys.exit(1)
    print("统一配置技能凭证 → %s" % path)
    print("直接回车保留原值；输入 - 清除该项。\n")
    for field, label, secret in FIELDS:
        current = masked(data.get(field))
        value = ask("  %s [%s]: " % (label, current), secret).strip()
        if not value:
            continue
        if value == "-":
            data.pop(field, None)
        else:
            data[field] = value
    save(path, data)
    print("\n已保存。\n")
    show(path, data)


def main():
    ap = argparse.ArgumentParser(
        description="统一配置本仓库各技能的凭证（~/.claude-skills/keys.json）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例：\n"
               "  python configure.py\n"
               "  python configure.py --show\n"
               "  python configure.py --safillu sk-xxxx --lk888 sk-xxxx --video-uid <UID>")
    ap.add_argument("--show", action="store_true", help="只显示当前配置（脱敏），不修改")
    ap.add_argument("--file", default=os.environ.get("SKILLS_CONFIG_FILE") or DEFAULT_FILE,
                    help="配置文件路径（默认 ~/.claude-skills/keys.json）")
    ap.add_argument("--safillu", metavar="KEY", help="Safillu API key")
    ap.add_argument("--tt-image", dest="tt_image", metavar="KEY", help="TT Image 2 API key")
    ap.add_argument("--gem-vision", dest="gem_vision", metavar="KEY", help="GEM Vision API key")
    ap.add_argument("--lk888", metavar="KEY", help="同时设置 TT Image 2 和 GEM Vision 的 key（两者同网关）")
    ap.add_argument("--video-uid", dest="video_uid", metavar="UID", help="video-download 账号 UID")
    ap.add_argument("--video-base", dest="video_base", metavar="URL", help="video-download 接口地址（可选）")
    args = ap.parse_args()

    path = os.path.abspath(args.file)
    data = load(path)

    updates = {}
    if args.safillu:
        updates["safillu_api_key"] = args.safillu.strip()
    if args.lk888:
        updates["tt_image_api_key"] = args.lk888.strip()
        updates["gem_vision_api_key"] = args.lk888.strip()
    if args.tt_image:
        updates["tt_image_api_key"] = args.tt_image.strip()
    if args.gem_vision:
        updates["gem_vision_api_key"] = args.gem_vision.strip()
    if args.video_uid:
        updates["video_download_uid"] = args.video_uid.strip()
    if args.video_base:
        updates["video_download_api_base"] = args.video_base.strip().rstrip("/")

    if args.show:
        show(path, data)
        return
    if updates:
        data.update(updates)
        save(path, data)
        print("已保存。\n")
        show(path, data)
        return
    try:
        interactive(path, data)
    except (EOFError, KeyboardInterrupt):
        print("\n已取消，未修改。")
        sys.exit(1)


if __name__ == "__main__":
    main()
