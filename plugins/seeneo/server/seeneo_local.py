# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp>=1.10,<2"]
# ///
"""Local-only footage tools. Run with uv run --script seeneo_local.py."""
import contextlib
import functools
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading

from mcp.server.fastmcp import FastMCP, Image
from mcp.types import TextContent


class LocalMCP(FastMCP):
    """Translate SDK argument-validation failures at the protocol boundary, too."""
    async def call_tool(self, name, arguments):
        try:
            return await super().call_tool(name, arguments)
        except Exception:
            return [TextContent(type="text", text=json.dumps({"ok": False, "error": "invalid_argument", "message":
                    "Check the tool name and arguments, then retry. / ตรวจสอบชื่อเครื่องมือและค่าที่ส่งแล้วลองใหม่"}, ensure_ascii=False))]


mcp = LocalMCP("seeneo-local")
# ponytail: one process-wide lock; split only if parallel heavy jobs become a requirement.
WORK_LOCK = threading.Lock()


class ToolError(Exception):
    def __init__(self, code, en, th, details=None):
        self.result = {"ok": False, "error": code, "message": f"{en} / {th}"}
        if details:
            self.result["details"] = details


def invalid(en="Check the tool arguments and try again.", th="ตรวจสอบค่าที่ส่งให้เครื่องมือแล้วลองใหม่"):
    raise ToolError("invalid_argument", en, th)


def safe(function):
    @functools.wraps(function)
    def wrapped(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except ToolError as error:
            return error.result
        except (ValueError, TypeError, KeyError, OverflowError):
            return {"ok": False, "error": "invalid_argument", "message":
                    "Check the tool arguments and try again. / ตรวจสอบค่าที่ส่งให้เครื่องมือแล้วลองใหม่"}
        except Exception:
            return {"ok": False, "error": "local_error", "message":
                    "Check file permissions, free disk space and local tools, then retry. / ตรวจสอบสิทธิ์ไฟล์ พื้นที่ว่าง และเครื่องมือในเครื่อง แล้วลองใหม่"}
    return wrapped


def serial(function):
    @functools.wraps(function)
    def wrapped(*args, **kwargs):
        if not WORK_LOCK.acquire(blocking=False):
            raise ToolError("busy", "A render or transcription is running; retry after it finishes.",
                            "กำลังเรนเดอร์หรือถอดเสียง รอให้เสร็จแล้วลองใหม่")
        try:
            return function(*args, **kwargs)
        finally:
            WORK_LOCK.release()
    return wrapped


def number(value, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        invalid()
    return float(value)


def command(argv, cwd=None, require_glyphs=False):
    """No shell, no inherited stdin, bounded stderr, no network protocols for media."""
    with tempfile.TemporaryFile() as errors:
        try:
            # Own process group, so a timeout or shutdown also stops grandchildren (the speech helper under uv).
            result = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=errors, cwd=cwd,
                                      start_new_session=True)
        except FileNotFoundError:
            raise ToolError("tool_missing", "Install ffmpeg, ffprobe and uv on PATH, then retry.",
                            "ติดตั้ง ffmpeg, ffprobe และ uv ให้เรียกได้จาก PATH แล้วลองใหม่") from None
        try:
            stdout = result.communicate(timeout=7200)[0]
        except BaseException as error:
            # ponytail: Windows has no process groups; there only the direct child is stopped.
            with contextlib.suppress(ProcessLookupError):
                os.killpg(result.pid, signal.SIGKILL) if hasattr(os, "killpg") else result.kill()
            result.wait()
            if isinstance(error, subprocess.TimeoutExpired):
                raise ToolError("timeout", "The local operation timed out; try a shorter clip.",
                                "งานในเครื่องใช้เวลานานเกินกำหนด ลองใช้คลิปที่สั้นลง") from None
            raise
        errors.seek(0, os.SEEK_END)
        errors.seek(max(0, errors.tell() - 8192))
        tail = errors.read().decode("utf-8", errors="replace").splitlines()[-20:]
        if require_glyphs:
            errors.seek(0)
            if any(b"failed to find any fallback" in line or b"no font could be found" in line for line in errors):
                raise ToolError("caption_font_missing", "Install Thai and Chinese fonts, then retry the caption render.",
                                "ติดตั้งฟอนต์ภาษาไทยและจีน แล้วลองเรนเดอร์ซับไตเติลใหม่")
    if result.returncode:
        # Speech helper diagnostics can contain implementation names; do not expose them.
        details = "\n".join(tail) if Path(argv[0]).name.startswith(("ffmpeg", "ffprobe")) else None
        raise ToolError("media_error", "The local operation failed; check the file and tool installation, then retry.",
                        "งานในเครื่องไม่สำเร็จ ตรวจสอบไฟล์และการติดตั้งเครื่องมือแล้วลองใหม่", details)
    return stdout


# Codex starts plugin servers inside the plugin folder and names no workspace (no MCP roots), so there relative
# paths and ./seeneo-out would point into the plugin cache: require absolute inputs and write next to them.
IN_PLUGIN = Path.cwd().resolve().is_relative_to(Path(__file__).resolve().parent.parent)


def user_path(path):
    file = Path(path).expanduser()
    if IN_PLUGIN and not file.is_absolute():
        invalid("Use an absolute file path.", "ใช้เส้นทางไฟล์แบบเต็ม (absolute path)")
    return file.resolve()


def inspect_media(path):
    if not isinstance(path, str) or not path or "\x00" in path:
        invalid("Supply a local media file path.", "ระบุเส้นทางไฟล์สื่อในเครื่อง")
    file = user_path(path)
    if not file.is_file():
        raise ToolError("file_missing", "Choose an existing regular local file.", "เลือกไฟล์ปกติที่มีอยู่ในเครื่อง")
    data = json.loads(command(["ffprobe", "-v", "error", "-protocol_whitelist", "file,pipe",
                               "-show_format", "-show_streams", "-of", "json", str(file)]))
    if not data.get("streams"):
        raise ToolError("invalid_media", "Choose a media file accepted by ffprobe.", "เลือกไฟล์สื่อที่ ffprobe อ่านได้")
    return file, data


def media_info(path, kind=None):
    file, data = inspect_media(path)
    streams = data["streams"]
    video = next((s for s in streams if s["codec_type"] == "video"), {})
    audio = any(s["codec_type"] == "audio" for s in streams)
    if (kind == "video" and not video) or (kind == "audio" and not audio):
        invalid("Choose a file with the required video/audio stream.", "เลือกไฟล์ที่มีภาพหรือเสียงตามที่ต้องใช้")
    duration = float(data.get("format", {}).get("duration") or max(float(s.get("duration") or 0) for s in streams))
    video_duration = min(duration, float(video.get("duration") or duration))
    if not math.isfinite(duration) or duration <= 0:
        invalid("Choose media with a finite positive duration.", "เลือกสื่อที่มีระยะเวลามากกว่าศูนย์และอ่านได้")
    rotation = int(float(video.get("tags", {}).get("rotate", 0)))
    for side in video.get("side_data_list", []):
        if "rotation" in side:
            rotation = int(float(side["rotation"]))
    rate = video.get("avg_frame_rate", "0/1").split("/")
    fps = float(rate[0]) / float(rate[1]) if len(rate) == 2 and float(rate[1]) else 0.0
    return {"path": str(file), "duration_s": duration, "width": int(video.get("width", 0)),
            "height": int(video.get("height", 0)), "fps": fps, "rotation": rotation,
            "has_audio": audio, "size_bytes": file.stat().st_size, "video_duration_s": video_duration}


def output_dir(inputs=()):
    default = Path(inputs[0]).parent / "seeneo-out" if IN_PLUGIN and inputs else "seeneo-out"
    directory = Path(os.environ.get("SEENEO_OUT_DIR", default)).expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True)
    return directory


UNSAFE_NAME = re.compile(r'[\x00-\x1f\x7f\\/:*?"<>|%]')


def fmt(value):
    """Plain decimal for FFmpeg arguments; str() gives exponents such as 1e-05 that FFmpeg rejects."""
    return f"{float(value):.6f}"


def derived_name(path, suffix=""):
    """Output name from an input file name: unsafe characters replaced, cut to fit file-name limits."""
    stem = UNSAFE_NAME.sub("-", Path(path).stem).encode()[:150].decode(errors="ignore").strip(" .-")
    return (stem or "media") + suffix


def output_name(name, inputs=(), extension=".mp4"):
    if not isinstance(name, str) or not name or len(name.encode()) > 200 or "/" in name or "\\" in name or ":" in name or name in (".", ".."):
        invalid("Use a bare output name, without directories or traversal.", "ใช้ชื่อไฟล์ผลลัพธ์เท่านั้น ห้ามระบุโฟลเดอร์หรือเส้นทางย้อนกลับ")
    name = UNSAFE_NAME.sub("-", name).strip(" .-")
    if name.lower().endswith(extension):
        name = name[:-len(extension)]
    if not name:
        invalid()
    if (output_dir(inputs) / (name + extension)).resolve() in {Path(p).resolve() for p in inputs}:
        invalid("Choose an output name different from every input file.", "เลือกชื่อผลลัพธ์ที่ไม่ตรงกับไฟล์ต้นฉบับทุกไฟล์")
    return name


def publish(files, name, inputs=()):
    """Reserve all names exclusively; suffix collisions, including dangling symlinks."""
    directory = output_dir(inputs)
    reserved, writers = [], []
    index = 1

    def release():
        for writer in writers:
            writer.close()
        for path in reserved:
            path.unlink()
        writers.clear()
        reserved.clear()

    while True:
        stem = name if index == 1 else f"{name}-{index}"
        paths = [directory / (stem + suffix) for suffix in files]
        if any(p.resolve() in {Path(i).resolve() for i in inputs} for p in paths):
            invalid("Choose an output name different from the input file.", "เลือกชื่อผลลัพธ์ที่ไม่ตรงกับไฟล์ต้นฉบับ")
        try:
            for path in paths:
                # Write through the exclusively created descriptor, never by reopening the name (no symlink swap).
                writers.append(os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb"))
                reserved.append(path)
            break
        except FileExistsError:
            release()
            index += 1
        except Exception:
            release()
            raise
    try:
        for writer, source in zip(writers, files.values()):
            with Path(source).open("rb") as reader:
                shutil.copyfileobj(reader, writer)
            writer.close()
    except Exception:
        release()
        raise
    return paths


@functools.lru_cache(maxsize=2)
def ffmpeg(subtitles=False):
    executable = shutil.which("ffmpeg") or "ffmpeg"
    if not subtitles:
        return executable
    candidates = [executable]
    if sys.platform == "darwin":
        candidates += ["/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg", "/usr/local/opt/ffmpeg-full/bin/ffmpeg"]
    for candidate in candidates:
        if Path(candidate).is_file() and re.search(rb"\bsubtitles\s+", command([candidate, "-hide_banner", "-filters"])):
            return candidate
    raise ToolError("captions_unavailable", "Install an FFmpeg build with subtitle support, then retry.",
                    "ติดตั้ง FFmpeg รุ่นที่รองรับซับไตเติลแล้วลองใหม่")


def input_args(path):
    return ["-protocol_whitelist", "file,pipe", "-i", str(path)]


@mcp.tool(structured_output=False)
@safe
def probe(path: str) -> dict:
    """Inspect local media: duration, dimensions, frame rate, rotation, audio and size."""
    return media_info(path)


@mcp.tool(structured_output=False)
@safe
def frames(path: str, count: int = 6, times_s: list[float] | None = None, width: int = 360) -> list:
    """View local footage as one JPEG contact sheet. Supply 1–16 frames or explicit times."""
    info = media_info(path, "video")
    if not isinstance(count, int) or isinstance(count, bool) or not 1 <= count <= 16:
        invalid()
    width = int(number(width, 32, 1920))
    if times_s is None:
        times_s = [info["duration_s"] * (i + .5) / count for i in range(count)]
    if not isinstance(times_s, list) or not 1 <= len(times_s) <= 16:
        invalid()
    # Times are valid against the file; frames come from the last decodable picture when audio outlasts video.
    last = max(0., info["video_duration_s"] - 1 / (info["fps"] or 30))
    times_s = [min(number(t, 0, info["duration_s"] - .001), last) for t in times_s]
    w, h = info["width"], info["height"]
    if abs(info["rotation"]) % 180 == 90:
        w, h = h, w
    height = max(2, math.ceil(width * h / w / 2) * 2)
    if height > 1920:  # very tall sources: bound the long side, not only the width
        width, height = max(2, math.ceil(width * 1920 / height / 2) * 2), 1920
    columns = math.ceil(math.sqrt(len(times_s)))
    name = output_name(derived_name(info["path"], "-frames"), [info["path"]], ".jpg")
    with tempfile.TemporaryDirectory(prefix="seeneo-frames-") as temp:
        for i, at in enumerate(times_s):
            command([ffmpeg(), "-v", "error", "-nostdin", "-ss", fmt(at), *input_args(info["path"]),
                     "-vf", f"scale={width}:{height},setsar=1", "-frames:v", "1", str(Path(temp) / f"frame-{i:02d}.jpg")])
        sheet = Path(temp) / "sheet.jpg"
        command([ffmpeg(), "-v", "error", "-nostdin", "-framerate", "1", "-i", str(Path(temp) / "frame-%02d.jpg"),
                 "-vf", f"tile={columns}x{math.ceil(len(times_s) / columns)}:nb_frames={len(times_s)}",
                 "-frames:v", "1", str(sheet)])
        data = sheet.read_bytes()
        destination = publish({".jpg": sheet}, name, [info["path"]])[0]
    return [Image(data=data, format="jpeg"), json.dumps({"times_s": times_s, "sheet_path": str(destination)})]


@mcp.tool(structured_output=False)
@safe
def find_silence(path: str, min_silence_s: float = .6, noise_db: float = -35, pad_s: float = .12) -> dict:
    """Find silent intervals and their padded speech complement in local footage."""
    info = media_info(path)
    minimum = number(min_silence_s, .01, 3600)
    noise = number(noise_db, -100, 0)
    pad = number(pad_s, 0, 60)
    duration = info["duration_s"]
    if not info["has_audio"]:
        return {"silences": [{"start_s": 0., "end_s": duration}], "speech": []}
    data = command([ffmpeg(), "-v", "error", "-nostdin", *input_args(info["path"]), "-vn", "-af",
                    f"silencedetect=noise={fmt(noise)}dB:d={fmt(minimum)},ametadata=print:file=-", "-f", "null", "-"]).decode()
    silences, start = [], None
    for kind, value in re.findall(r"lavfi\.silence_(start|end)(?:\.\d+)?=([\d.eE+-]+)", data):
        value = max(0., min(duration, float(value)))
        if kind == "start":
            start = value
        elif start is not None:
            silences.append({"start_s": start, "end_s": value})
            start = None
    if start is not None:
        silences.append({"start_s": start, "end_s": duration})
    speech, cursor = [], 0.
    for gap in silences:
        if gap["start_s"] > cursor:
            speech.append({"start_s": max(0., cursor - pad), "end_s": min(duration, gap["start_s"] + pad)})
        cursor = gap["end_s"]
    if cursor < duration:
        speech.append({"start_s": max(0., cursor - pad), "end_s": duration})
    merged = []
    for segment in speech:
        if merged and segment["start_s"] <= merged[-1]["end_s"]:
            merged[-1]["end_s"] = segment["end_s"]
        else:
            merged.append(segment)
    return {"silences": silences, "speech": merged}


def validate_cues(cues, duration):
    if not isinstance(cues, list) or len(cues) > 2000:
        invalid("Use at most 2000 caption cues.", "ใช้ซับไตเติลไม่เกิน 2000 ช่วง")
    validated = []
    for cue in cues:
        if not isinstance(cue, dict) or not isinstance(cue.get("text"), str) or len(cue["text"]) > 500:
            invalid("Use caption text of at most 500 characters per cue.", "ใช้ข้อความซับไตเติลไม่เกิน 500 ตัวอักษรต่อช่วง")
        start, end = number(cue["start_s"], 0, duration), number(cue["end_s"], 0, duration)
        if start >= end:
            invalid()
        words, previous = cue.get("words", []), start
        if not isinstance(words, list) or len(words) > 500:
            invalid()
        for word in words:
            ws, we = number(word["start_s"], start, end), number(word["end_s"], start, end)
            if ws < previous or we <= ws or not isinstance(word.get("text"), str) or len(word["text"]) > 500:
                invalid()
            previous = we
        if sum(len(w["text"]) for w in words) > 500:
            invalid()
        validated.append({"start_s": start, "end_s": end, "text": cue["text"], "words": words})
    return validated


def srt_cues(path):
    file, data = inspect_media(path)
    if not any(s["codec_type"] == "subtitle" for s in data["streams"]) or file.stat().st_size > 4_000_000:
        invalid("Choose a UTF-8 SRT subtitle file under 4 MB.", "เลือกไฟล์ซับ SRT แบบ UTF-8 ขนาดไม่เกิน 4 MB")
    cues = []
    for block in re.split(r"\n\s*\n", file.read_text(encoding="utf-8-sig").replace("\r\n", "\n").strip()):
        lines = block.splitlines()
        if lines and lines[0].strip().isdigit():
            lines.pop(0)
        if len(lines) < 2:
            invalid()
        match = re.fullmatch(r"(\d+):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d+):(\d{2}):(\d{2})[,.](\d{3})", lines[0].strip())
        if not match:
            invalid("Check SRT timestamps and retry.", "ตรวจสอบเวลาในไฟล์ SRT แล้วลองใหม่")
        values = [int(n) for n in match.groups()]
        start, end = [values[i] * 3600 + values[i+1] * 60 + values[i+2] + values[i+3] / 1000 for i in (0, 4)]
        cues.append({"start_s": start, "end_s": end, "text": "\n".join(lines[1:])})
    return cues


def ass_color(value):
    if not isinstance(value, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
        invalid("Use caption colors in #RRGGBB format.", "ระบุสีซับไตเติลในรูปแบบ #RRGGBB")
    return "&H00" + value[5:7] + value[3:5] + value[1:3]


def ass_text(text):
    # LLM text cannot introduce ASS override tags or drawing commands.
    return text.replace("\\", "＼").replace("{", "｛").replace("}", "｝").replace("\r", "").replace("\n", r"\N")


def timestamp(seconds):
    ticks = round(seconds * 100)
    return f"{ticks // 360000}:{ticks // 6000 % 60:02}:{ticks // 100 % 60:02}.{ticks % 100:02}"


def make_ass(captions, duration, width, height, file):
    if not isinstance(captions, dict) or ("cues" in captions) == ("srt_path" in captions):
        invalid("Supply either caption cues or an SRT path.", "ระบุช่วงซับไตเติลหรือเส้นทางไฟล์ SRT อย่างใดอย่างหนึ่ง")
    cues = validate_cues(captions.get("cues") if "cues" in captions else srt_cues(captions["srt_path"]), duration)
    style, position = captions.get("style", "clean"), captions.get("position", "bottom")
    if style not in ("clean", "bold", "glow", "box") or position not in ("bottom", "middle", "top"):
        invalid()
    config = captions.get("style_config", {})
    if not isinstance(config, dict):
        invalid()
    font = config.get("fontFamily") or ("Thonburi" if sys.platform == "darwin" else "Leelawadee UI" if os.name == "nt" else "Noto Sans Thai")
    # Prefer the channel font when installed; libass performs Chinese glyph fallback.
    if "fontFamily" not in config:
        roots = [Path.home() / "Library/Fonts", Path("/Library/Fonts"), Path("/usr/share/fonts"),
                 Path.home() / ".local/share/fonts", Path.home() / ".fonts", Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"]
        if any(root.is_dir() and any(root.rglob("*Kanit*")) for root in roots):
            font = "Kanit"
    if not isinstance(font, str) or not re.fullmatch(r"[^,\n\r\\{}]{1,100}", font):
        invalid()
    size = number(config.get("fontSizePx", 48), 8, 300) * height / 1080
    outline = number(config.get("strokeWidthPx", 3), 0, 30) * height / 1080
    primary = ass_color(config.get("fill", "#ffffff"))
    stroke = ass_color(config.get("stroke", "#111111"))
    glow = config.get("glowColor", "#00ffff" if style == "glow" else None)
    glow_size = number(config.get("glowSizePx", 6), 0, 40) * height / 1080
    limit = int(number(config.get("wordsPerScreen", 6), 1, 100))
    highlight = ass_color(config["highlight"]) if config.get("highlight") else None
    alignment = {"bottom": 2, "middle": 5, "top": 8}[position]
    border = 3 if style == "box" else 1
    lines = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {width}", f"PlayResY: {height}", "WrapStyle: 0",
             "[V4+ Styles]", "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
             f"Style: Default,{font},{size},{primary},{primary},{stroke},&H80000000,{-1 if style == 'bold' else 0},0,0,0,100,100,0,0,{border},{outline},0,{alignment},20,20,{max(10, round(height * .06))},1",
             "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]

    def dialogue(start, end, text, layer=1):
        lines.append(f"Dialogue: {layer},{timestamp(start)},{timestamp(end)},Default,,0,0,0,,{text}")

    def text(value):
        escaped = ass_text(value)
        # CoreText can select an inaccessible reserved font. Use the installed CJK font explicitly.
        if sys.platform == "darwin":
            escaped = re.sub(r"[\u3000-\u303f\u3400-\u9fff\uf900-\ufaff\uff00-\uffef]+",
                             lambda match: r"{\fnHiragino Sans GB}" + match[0] + "{\\fn" + font + "}", escaped)
        return escaped

    for cue in cues:
        words = cue["words"]
        groups = [words[i:i+limit] for i in range(0, len(words), limit)] if words else [None]
        for group_index, group in enumerate(groups):
            start = cue["start_s"] if group_index == 0 else group[0]["start_s"]
            end = groups[group_index + 1][0]["start_s"] if group_index + 1 < len(groups) else cue["end_s"]
            plain = " ".join(text(w["text"]) for w in group) if group else text(cue["text"])
            if glow:
                dialogue(start, end, "{\\1a&HFF&\\3c" + ass_color(glow) + f"\\bord{glow_size}\\blur{glow_size}" + "}" + plain, 0)
            if highlight and group:
                # ASS karaoke timing includes silence gaps; reset a completed word to the base color.
                parts, cursor = [], start
                for word in group:
                    gap = max(0, round((word["start_s"] - cursor) * 100))
                    length = max(1, round((word["end_s"] - word["start_s"]) * 100))
                    reset = round((word["end_s"] - start) * 1000)
                    parts.append(f"{{\\k{gap}}}{{\\1c{highlight}\\2c{primary}\\k{length}\\t({reset},{reset+1},\\1c{primary})}}" + text(word["text"]))
                    cursor = word["end_s"]
                dialogue(start, end, " ".join(parts))
            else:
                dialogue(start, end, plain)
    file.write_text("\n".join(lines) + "\n", encoding="utf-8")


@mcp.tool(structured_output=False)
@safe
@serial
def render(clips: list[dict], aspect: str = "source", fit: str = "crop", transition: str = "none",
           transition_s: float = .3, captions: dict | None = None, music: dict | None = None,
           loudnorm: bool = True, draft: bool = False, output: str = "name") -> dict:
    """Render local clips in one encode, with optional captions/music. Resolution follows the source; drafts cap the long side at 540 px."""
    if not isinstance(clips, list) or not 1 <= len(clips) <= 200:
        invalid("Supply 1–200 clips.", "ระบุคลิป 1–200 คลิป")
    if aspect not in ("source", "9:16", "1:1", "4:5", "16:9") or fit not in ("crop", "pad") or transition not in ("none", "fade"):
        invalid()
    if not isinstance(draft, bool) or not isinstance(loudnorm, bool):
        invalid()
    fade = number(transition_s, .01, 60) if transition == "fade" and len(clips) > 1 else 0.
    infos, spans, durations = [], [], []
    for clip in clips:
        info = media_info(clip["path"], "video")
        start = number(clip["start_s"], 0, info["duration_s"])
        end = number(clip["end_s"], 0, info["duration_s"])
        if start >= end:
            invalid("Use 0 ≤ start_s < end_s ≤ clip duration.", "ใช้เวลา 0 ≤ start_s < end_s ≤ ระยะเวลาคลิป")
        infos.append(info)
        spans.append((start, end))
        durations.append(end - start)
    if fade and any(length <= 2 * fade for length in durations):
        invalid("Shorten the fade to less than half the shortest clip.", "ลดเวลาทรานซิชันให้สั้นกว่าครึ่งหนึ่งของคลิปที่สั้นที่สุด")
    duration = sum(durations) - fade * (len(clips) - 1)
    if duration > 3600:
        invalid("Keep total output at or below 60 minutes.", "ใช้ระยะเวลาผลลัพธ์รวมไม่เกิน 60 นาที")
    inputs = [info["path"] for info in infos]
    music_info = None
    if music is not None:
        if not isinstance(music, dict) or not isinstance(music.get("duck", True), bool):
            invalid()
        music_info = media_info(music["path"], "audio")
        volume = number(music.get("volume_db", -18), -100, 12)
        inputs.append(music_info["path"])
    if captions and "srt_path" in captions:
        inputs.append(str(user_path(captions["srt_path"])))
    name = output_name(output, inputs)
    width, height = infos[0]["width"], infos[0]["height"]
    if abs(infos[0]["rotation"]) % 180 == 90:
        width, height = height, width
    long_side = min(max(width, height), 540) if draft else max(width, height)
    ratio = width / height if aspect == "source" else float(aspect.split(":")[0]) / float(aspect.split(":")[1])
    width = max(2, int((long_side if ratio >= 1 else long_side * ratio) / 2) * 2)
    height = max(2, int((long_side / ratio if ratio >= 1 else long_side) / 2) * 2)
    with tempfile.TemporaryDirectory(prefix="seeneo-render-") as temp:
        if captions is not None:
            fonts = Path(temp) / "fonts"
            fonts.mkdir()
            if sys.platform == "darwin":
                for i, source in enumerate((Path("/System/Library/Fonts/Supplemental/Thonburi.ttc"),
                                            Path("/System/Library/Fonts/Hiragino Sans GB.ttc"))):
                    if source.is_file():
                        (fonts / f"font-{i}.ttc").symlink_to(source)
            make_ass(captions, duration, width, height, Path(temp) / "captions.ass")
        argv = [ffmpeg(captions is not None), "-hide_banner", "-v", "info" if captions is not None else "error", "-nostdin", "-n", "-filter_complex_threads", "1"]
        filters = []
        for i, ((start, end), info, length) in enumerate(zip(spans, infos, durations)):
            argv += input_args(info["path"])
            scaling = f"scale={width}:{height}:force_original_aspect_ratio={'increase' if fit == 'crop' else 'decrease'}:force_divisible_by=2"
            sizing = f"crop={width}:{height}" if fit == "crop" else f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black"
            # Hold the last picture when a file's audio outlasts its video, so every clip is exactly its length.
            filters.append(f"[{i}:v:0]trim=start={fmt(start)}:end={fmt(end)},setpts=PTS-STARTPTS,fps=30,{scaling},{sizing},setsar=1,format=yuv420p,settb=AVTB,"
                           f"tpad=stop=-1:stop_mode=clone,trim=duration={fmt(length)}[v{i}]")
            if info["has_audio"]:
                filters.append(f"[{i}:a:0]atrim=start={fmt(start)}:end={fmt(end)},asetpts=PTS-STARTPTS,aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,apad,atrim=duration={fmt(length)}[a{i}]")
            else:
                filters.append(f"anullsrc=r=48000:cl=stereo,atrim=duration={fmt(length)},asetpts=PTS-STARTPTS[a{i}]")
        video, audio = "v0", "a0"
        if fade:
            elapsed = durations[0]
            for i in range(1, len(clips)):
                filters.append(f"[{video}][v{i}]xfade=transition=fade:duration={fmt(fade)}:offset={fmt(elapsed - fade)}[vx{i}]")
                filters.append(f"[{audio}][a{i}]acrossfade=d={fmt(fade)}:c1=tri:c2=tri[ax{i}]")
                video, audio = f"vx{i}", f"ax{i}"
                elapsed += durations[i] - fade
        elif len(clips) > 1:
            filters.append("".join(f"[v{i}][a{i}]" for i in range(len(clips))) + f"concat=n={len(clips)}:v=1:a=1[vc][ac]")
            video, audio = "vc", "ac"
        if captions is not None:
            filters.append(f"[{video}]subtitles=filename=captions.ass:fontsdir=fonts[vs]")
            video = "vs"
        if music_info:
            argv += ["-stream_loop", "-1", *input_args(music_info["path"])]
            filters.append(f"[{len(clips)}:a:0]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,atrim=duration={fmt(duration)},asetpts=PTS-STARTPTS,volume={fmt(volume)}dB[bg]")
            if music.get("duck", True):
                filters.append(f"[{audio}]asplit=2[voice][side]")
                filters.append("[bg][side]sidechaincompress=threshold=0.025:ratio=8:attack=20:release=250[ducked]")
                filters.append("[voice][ducked]amix=inputs=2:duration=first:normalize=0[am]")
            else:
                filters.append(f"[{audio}][bg]amix=inputs=2:duration=first:normalize=0[am]")
            audio = "am"
        if loudnorm:
            # Some FFmpeg builds produce NaN on digital silence; keep it silent for AAC.
            finite = "|".join(f"if(isnan(val({ch}))+isinf(val({ch})),0,val({ch}))" for ch in (0, 1))
            filters.append(f"[{audio}]loudnorm=I=-16:TP=-1.5:LRA=11,aeval='{finite}':c=stereo,aformat=channel_layouts=stereo[an]")
            audio = "an"
        encoded = Path(temp) / "render.mp4"
        command(argv + ["-filter_complex", ";".join(filters), "-map", f"[{video}]", "-map", f"[{audio}]",
                        "-t", fmt(duration), "-c:v", "libx264", "-preset", "ultrafast" if draft else "fast", "-crf", "26" if draft else "20",
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "48000", "-movflags", "+faststart", str(encoded)], cwd=temp,
                require_glyphs=captions is not None)
        result = media_info(str(encoded), "video")
        destination = publish({".mp4": encoded}, name, inputs)[0]
    return {"output_path": str(destination), **{key: result[key] for key in ("duration_s", "width", "height", "size_bytes")}}


def run_transcription(path, language, quality, temp):
    """Only this boundary starts the optional recognizer; never invoked during validation."""
    helper = Path(__file__).with_name("transcribe_helper.py").resolve()
    audio = Path(temp) / "speech.wav"
    command([ffmpeg(), "-v", "error", "-nostdin", *input_args(path), "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(audio)])
    try:
        return json.loads(command(["uv", "run", "--quiet", "--with", "faster-whisper", "--python", sys.executable, str(helper),
                                   str(audio), language, quality], cwd=temp))
    except ToolError as error:
        if error.result["error"] != "media_error":
            raise
        raise ToolError("speech_failed", "Local speech recognition failed. First use needs internet and about 4 GB free disk "
                        "for the speech model; check both, then retry.",
                        "ถอดเสียงในเครื่องไม่สำเร็จ การใช้ครั้งแรกต้องต่ออินเทอร์เน็ตและมีพื้นที่ว่างราว 4 GB สำหรับโมเดลเสียง "
                        "ตรวจสอบทั้งสองอย่างแล้วลองใหม่") from None


def srt_timestamp(seconds):
    ticks = round(seconds * 1000)
    return f"{ticks // 3600000:02}:{ticks // 60000 % 60:02}:{ticks // 1000 % 60:02},{ticks % 1000:03}"


@mcp.tool(structured_output=False)
@safe
@serial
def transcribe(path: str, language: str = "auto", quality: str = "fast") -> dict:
    """Transcribe local speech into SRT and timed words. First use downloads about 1.6 GB (fast) or 3 GB (best) once per computer; audio stays local."""
    if language not in ("auto", "th", "en", "zh") or quality not in ("fast", "best"):
        invalid("Choose language auto/th/en/zh and quality fast/best.", "เลือกภาษา auto/th/en/zh และคุณภาพ fast/best")
    info = media_info(path, "audio")
    if info["duration_s"] > 3600:
        invalid("Transcribe at most 60 minutes at once.", "ถอดเสียงครั้งละไม่เกิน 60 นาที")
    name = output_name(derived_name(info["path"]), [info["path"]], ".srt")
    with tempfile.TemporaryDirectory(prefix="seeneo-transcribe-") as temp:
        result = run_transcription(info["path"], language, quality, temp)
        cues = validate_cues(result["cues"], info["duration_s"])
        srt, words = Path(temp) / "transcript.srt", Path(temp) / "transcript.words.json"
        srt.write_text("\n\n".join(f"{i}\n{srt_timestamp(c['start_s'])} --> {srt_timestamp(c['end_s'])}\n{c['text']}" for i, c in enumerate(cues, 1)) + "\n", encoding="utf-8")
        words.write_text(json.dumps({"language": result["language"], "cues": cues}, ensure_ascii=False), encoding="utf-8")
        destinations = publish({".srt": srt, ".words.json": words}, name, [info["path"]])
    return {"srt_path": str(destinations[0]), "words_path": str(destinations[1]), "language": result["language"], "cues": cues,
            "note": "First use downloads approximately " + ("1.6 GB" if quality == "fast" else "3 GB") + "; speech processing and results stay on this machine."}


if __name__ == "__main__":
    # Exit through Python on termination so temp dirs are removed and running child groups are stopped.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    mcp.run(transport="stdio")
