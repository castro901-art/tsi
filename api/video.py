import json
import math
import subprocess
from pathlib import Path
from api import config


class VideoError(Exception):
    pass


def probe(path: Path):
    try:
        response = subprocess.run(
            ["ffprobe", "-v", "error", "-protocol_whitelist", "file", "-show_format", "-show_streams", "-of", "json", str(path)],
            capture_output=True, timeout=20, check=True,
        )
        data = json.loads(response.stdout)
        format_name = data["format"]["format_name"].split(",")
        duration = float(data["format"]["duration"])
        video = [s for s in data["streams"] if s.get("codec_type") == "video"]
        if "mp4" not in format_name or not video:
            raise VideoError("unsupported_container")
        if not math.isfinite(duration) or not 0 < duration <= config.MAX_SECONDS:
            raise VideoError("duration_limit")
        if any(s.get("width", 0) > 3840 or s.get("height", 0) > 2160 for s in video):
            raise VideoError("resolution_limit")
        return duration
    except FileNotFoundError as exc:
        raise VideoError("ffprobe_unavailable") from exc
    except subprocess.TimeoutExpired as exc:
        raise VideoError("validation_timeout") from exc
    except (subprocess.CalledProcessError, KeyError, ValueError) as exc:
        raise VideoError("invalid_video") from exc
