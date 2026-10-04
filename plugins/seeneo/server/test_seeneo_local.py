# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["mcp>=1.10,<2"]
# ///
"""Offline acceptance check: real synthetic media and real MCP stdio."""
import asyncio
import base64
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True


def run(*args):
    result = subprocess.run(list(args), capture_output=True, check=False)
    assert result.returncode == 0, result.stderr.decode(errors="replace")[-4000:]
    return result.stdout


def media(path, size, audio=False, duration=3):
    args = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-n",
            "-f", "lavfi", "-i", f"testsrc2=size={size}:rate=30:duration={duration}"]
    if audio:
        args += ["-f", "lavfi", "-i", f"sine=frequency=440:sample_rate=48000:duration={duration}",
                 "-af", "volume=enable='between(t,1,2)':volume=0", "-c:a", "aac"]
    run(*args, "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(path))


def dimensions(path):
    data = json.loads(run("ffprobe", "-v", "error", "-show_streams", "-of", "json", str(path)))
    return [(s["width"], s["height"]) for s in data["streams"] if s["codec_type"] == "video"][0]


def pixels(path, at):
    return run("ffmpeg", "-v", "error", "-ss", str(at), "-i", str(path), "-frames:v", "1",
               "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1")


def refused(result):
    assert isinstance(result, dict) and result.get("ok") is False, result
    assert result.get("error") and " / " in result.get("message", ""), result
    assert re.search("[ก-๙]", result["message"]), result
    assert "Traceback" not in json.dumps(result), result


async def protocol(video, out):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    env = dict(os.environ, UV_PYTHON=sys.executable, SEENEO_OUT_DIR=str(out))
    params = StdioServerParameters(command=shutil.which("uv"), args=["run", "--quiet", "--script",
                                  str(Path(__file__).with_name("seeneo_local.py"))], env=env)
    async with stdio_client(params) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            listing = await session.list_tools()
            assert {t.name for t in listing.tools} == {"probe", "frames", "find_silence", "transcribe", "render"}
            result = await session.call_tool("probe", {"path": str(video)})
            assert not result.isError, result
            assert json.loads(result.content[0].text)["width"] == 640
            result = await session.call_tool("frames", {"path": str(video), "count": 1, "width": 180})
            assert not result.isError, result
            assert result.content[0].type == "image" and result.content[0].mimeType == "image/jpeg"
            assert base64.b64decode(result.content[0].data).startswith(b"\xff\xd8")
            refused(json.loads((await session.call_tool("probe", {"path": str(out / "missing")})).content[0].text))
            for tool, args in (("probe", {}), ("probe", {"path": 42}), ("render", {"clips": "wrong"})):
                result = await session.call_tool(tool, args)
                refused(json.loads(result.content[0].text))


def main():
    server = Path(__file__).with_name("seeneo_local.py")
    assert server.is_file(), "Local MCP implementation is missing"
    import seeneo_local as local
    with tempfile.TemporaryDirectory(prefix="seeneo-acceptance-") as directory:
        root = Path(directory)
        out = root / "out"
        os.environ["SEENEO_OUT_DIR"] = str(out)
        landscape, silent, portrait = (root / n for n in ("landscape.mp4", "silent.mp4", "portrait.mp4"))
        media(landscape, "640x360", audio=True)
        media(silent, "640x360")
        media(portrait, "360x640", audio=True)
        music = root / "music.wav"
        run("ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=220:duration=2", str(music))
        info = local.probe(str(landscape))
        assert set(info) == {"path", "duration_s", "width", "height", "fps", "rotation", "has_audio", "size_bytes", "video_duration_s"}, info
        assert info["width"] == 640 and info["height"] == 360 and info["fps"] == 30 and info["has_audio"]
        assert abs(info["duration_s"] - 3) < .05 and info["size_bytes"] > 0
        assert not local.probe(str(silent))["has_audio"]
        sheet = local.frames(str(landscape), count=6, width=180)
        assert isinstance(sheet, list), sheet
        metadata = json.loads(sheet[1])
        assert len(metadata["times_s"]) == 6
        assert dimensions(metadata["sheet_path"]) == (540, 204)
        assert Path(metadata["sheet_path"]).read_bytes().startswith(b"\xff\xd8")
        assert len(json.loads(local.frames(str(portrait), times_s=[.1, 1.5], width=90)[1])["times_s"]) == 2
        gaps = local.find_silence(str(landscape))
        assert len(gaps["silences"]) == 1, gaps
        assert abs(gaps["silences"][0]["start_s"] - 1) <= .15 and abs(gaps["silences"][0]["end_s"] - 2) <= .15, gaps
        assert abs(gaps["speech"][0]["end_s"] - 1.12) <= .15 and abs(gaps["speech"][1]["start_s"] - 1.88) <= .15, gaps
        assert local.find_silence(str(silent))["speech"] == []
        print("PASS probe, JPEG contact sheets, silence gaps", flush=True)

        clips = [{"path": str(p), "start_s": .2, "end_s": 2.2} for p in (landscape, silent, portrait)]
        cues = [{"start_s": .2, "end_s": 1.7, "text": "สวัสดี 中文 Hello",
                 "words": [{"start_s": .2, "end_s": .7, "text": "สวัสดี"},
                           {"start_s": .8, "end_s": 1.2, "text": "中文"},
                           {"start_s": 1.3, "end_s": 1.7, "text": "Hello"}]}]
        for draft in (True, False):
            for fit in ("crop", "pad"):
                baseline = local.render(clips, aspect="9:16", fit=fit, transition="fade", draft=draft,
                                        music={"path": str(music), "duck": True}, output=f"plain-{fit}-{draft}")
                assert "output_path" in baseline, baseline
                assert abs(baseline["duration_s"] - 5.4) <= .1, baseline
                expected = (302, 540) if draft else (360, 640)
                assert (baseline["width"], baseline["height"]) == expected, baseline
                before = pixels(baseline["output_path"], .5)
                for style in ("clean", "bold", "glow", "box", "custom"):
                    captions = {"cues": cues, "style": style if style != "custom" else "clean"}
                    if style == "custom":
                        captions["style_config"] = {"fontSizePx": 42, "fill": "#ffffff", "highlight": "#ffff00",
                            "glowColor": "#00ffff", "glowSizePx": 5, "wordsPerScreen": 2, "unknown": "ignored"}
                    result = local.render(clips, aspect="9:16", fit=fit, transition="fade", draft=draft,
                                          captions=captions,
                                          music={"path": str(music), "duck": True}, output=f"{style}-{fit}-{draft}")
                    assert "output_path" in result, result
                    assert abs(result["duration_s"] - 5.4) <= .1 and result["size_bytes"] > 0, result
                    assert dimensions(result["output_path"]) == expected
                    assert pixels(result["output_path"], .5) != before, style
        srt = root / "captions.srt"
        srt.write_text("1\n00:00:00,200 --> 00:00:01,700\nสวัสดี 中文 Hello\n", encoding="utf-8")
        assert "output_path" in local.render(clips[:1], captions={"srt_path": str(srt), "position": "top"}, draft=True)
        assert "output_path" in local.render(clips[:1], aspect="1:1", fit="pad", loudnorm=False, draft=True)
        solid = root / "solid.mp4"
        run("ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=black:size=320x180:rate=30:duration=2",
            "-c:v", "libx264", "-preset", "ultrafast", str(solid))
        timed = local.render([{"path": str(solid), "start_s": 0, "end_s": 2}], draft=True,
                             captions={"cues": [{"start_s": .1, "end_s": 1.9, "text": "ONE TWO",
                                 "words": [{"start_s": .2, "end_s": .7, "text": "ONE"},
                                           {"start_s": .9, "end_s": 1.4, "text": "TWO"}]}],
                                       "style_config": {"fontSizePx": 120, "highlight": "#ff0000"}})
        assert "output_path" in timed, timed
        for at, side in ((.5, "left"), (.8, "none"), (1.1, "right"), (1.6, "none")):
            raw = pixels(timed["output_path"], at)
            red = [i // 3 % 320 for i in range(0, len(raw), 3) if raw[i] > 150 and raw[i+1] < 80 and raw[i+2] < 80]
            if side == "none":
                assert not red, (at, len(red))
            else:
                assert len(red) > 5, (at, len(red))
                assert (sum(red) / len(red) < 160) == (side == "left"), (at, sum(red) / len(red))
        print("PASS crop/pad, fades, silent clips, draft/final, all caption presets, custom karaoke/glow, SRT, ducking/loudnorm", flush=True)

        first = local.render(clips[:1], draft=True, output="duplicate")
        second = local.render(clips[:1], draft=True, output="duplicate")
        assert Path(first["output_path"]).name == "duplicate.mp4" and Path(second["output_path"]).name == "duplicate-2.mp4"
        saved = Path(first["output_path"]).read_bytes()
        refused(local.render([{"path": first["output_path"], "start_s": 0, "end_s": 1}], output="duplicate"))
        assert Path(first["output_path"]).read_bytes() == saved
        junk = root / "junk.txt"
        junk.write_text("not media")
        for name in ("../x", str(root / "x"), "..\\x"):
            refused(local.render(clips[:1], output=name))
        refused(local.probe(str(root / "missing")))
        refused(local.probe(str(junk)))
        refused(local.probe(str(root)))
        for start, end in ((1, 1), (2, 1), (-1, 1), (0, 4), (0, float("nan"))):
            refused(local.render([{"path": str(landscape), "start_s": start, "end_s": end}]))
        refused(local.render(clips[:1] * 201))
        refused(local.render([]))
        refused(local.render(clips[:1], captions={"cues": cues * 2001}))
        refused(local.render(clips[:1], captions={"cues": [{"start_s": 0, "end_s": 1, "text": "x" * 501}]}))
        long_clip = root / "long.mp4"
        run("ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=black:size=16x16:rate=1:duration=2",
            "-vf", "setpts=3700*PTS", "-fps_mode", "vfr", "-c:v", "libx264", str(long_clip))
        assert local.probe(str(long_clip))["duration_s"] > 3601
        too_long = local.render([{"path": str(long_clip), "start_s": 0, "end_s": 3601}])
        refused(too_long)
        assert "60" in too_long["message"]
        symlink = out / "linked.mp4"
        symlink.symlink_to(landscape)
        refused(local.render(clips[:1], output="linked"))
        assert symlink.is_symlink()
        refused(local.frames(str(landscape), count=17))
        refused(local.frames(str(landscape), times_s=[4]))
        tall = root / "tall.mp4"  # frames bounds the long side, not only the width
        media(tall, "16x1080", duration=1)
        assert max(dimensions(json.loads(local.frames(str(tall), count=1, width=1920)[1])["sheet_path"])) <= 1920
        refused(local.transcribe(str(landscape), language="xx"))
        refused(local.transcribe(str(landscape), quality="xx"))
        refused(local.transcribe(str(silent)))
        refused(local.transcribe(str(junk)))
        # Review regressions: audio outlasting video, exponent floats, Thai names, unsafe input names.
        short_video = root / "x:สวัสดีครับ.mp4"
        run("ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=320x240:rate=30:duration=2", "-f", "lavfi", "-i",
            "sine=duration=3", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", str(short_video))
        held = local.render([{"path": str(short_video), "start_s": 1e-05, "end_s": 3}, {"path": str(landscape), "start_s": 0, "end_s": 3}],
                            transition="fade", transition_s=.3, output="held", draft=True)
        assert abs(held["duration_s"] - 5.7) < .1, held
        streams = json.loads(run("ffprobe", "-v", "error", "-show_entries", "stream=codec_type,duration", "-of", "json", held["output_path"]))
        assert all(abs(float(s["duration"]) - 5.7) < .1 for s in streams["streams"]), streams
        late = local.frames(str(short_video), times_s=[2.9, 1e-05])
        assert isinstance(late, list) and Path(json.loads(late[1])["sheet_path"]).name == "x-สวัสดีครับ-frames.jpg", late
        assert local.output_name("สวัสดีครับ") == "สวัสดีครับ"
        assert local.derived_name(root / ("ก" * 300 + ".mp4")).encode().__len__() <= 150
        local.IN_PLUGIN, saved = True, os.environ.pop("SEENEO_OUT_DIR")  # Codex: server cwd is the plugin folder
        try:
            refused(local.probe("landscape.mp4"))
            assert local.output_dir([str(landscape.resolve())]) == (root / "seeneo-out").resolve()
        finally:
            local.IN_PLUGIN, os.environ["SEENEO_OUT_DIR"] = False, saved
        local.WORK_LOCK.acquire()
        try:
            refused(local.render(clips[:1]))
            refused(local.transcribe(str(landscape)))
        finally:
            local.WORK_LOCK.release()
        print("PASS bilingual safety errors, no overwrite, limits, transcription validation, process lock", flush=True)
        asyncio.run(protocol(landscape, out))
        print("PASS real MCP initialize, exactly five tools, probe, JPEG image content and error JSON", flush=True)
    print("PASS acceptance: no speech-model download; all fixtures removed", flush=True)


if __name__ == "__main__":
    main()
