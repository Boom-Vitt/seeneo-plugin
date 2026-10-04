"""Optional speech subprocess; dependencies are loaded only when transcription is requested."""
import json
import os
from pathlib import Path
import sys
import wave


def main():
    path, language, quality = sys.argv[1:]
    # One per-user download cache for every project; model files only, never recordings/transcripts.
    cache = Path(os.environ.get("SEENEO_MODEL_DIR") or Path.home() / ".cache" / "seeneo" / "speech")
    cache.mkdir(parents=True, exist_ok=True)
    os.environ["HF_HOME"] = str(cache)
    os.environ["HF_HUB_CACHE"] = str(cache / "hub")
    os.environ["HF_XET_CACHE"] = str(cache / "xet")
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    os.environ["DO_NOT_TRACK"] = "1"
    import numpy
    from faster_whisper import WhisperModel
    # The server already wrote 16 kHz mono s16 WAV; decode it here so the library's PyAV path (version-fragile) is never used.
    with wave.open(path) as w:
        audio = numpy.frombuffer(w.readframes(w.getnframes()), numpy.int16).astype(numpy.float32) / 32768
    recognizer = WhisperModel("large-v3-turbo" if quality == "fast" else "large-v3", device="auto", compute_type="default", download_root=str(cache))
    segments, info = recognizer.transcribe(audio, language=None if language == "auto" else language,
                                          word_timestamps=True, vad_filter=True)
    cues = []
    for segment in segments:
        text = segment.text.strip()
        if text:
            cues.append({"start_s": segment.start, "end_s": segment.end, "text": text,
                         "words": [{"start_s": w.start, "end_s": w.end, "text": w.word.strip()} for w in segment.words or [] if w.end > w.start]})
    print(json.dumps({"language": info.language, "cues": cues}, ensure_ascii=False))


if __name__ == "__main__":
    main()
