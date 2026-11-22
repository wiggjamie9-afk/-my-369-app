"""Voice interface. voice(script, out)->audio path. Real TTS (e.g. ElevenLabs) is TODO(key needed)."""
import subprocess


class SilentVoice:
    def speak(self, script: str, out: str, seconds: float = 5.0) -> str:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                        "-t", str(seconds), out], check=True)
        return out


class TTSVoice:
    def speak(self, script: str, out: str, seconds: float = 0) -> str:
        raise NotImplementedError("TODO: call a TTS service (needs a key); write audio to `out`")


def mux(video: str, audio: str, out: str) -> str:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", video, "-i", audio, "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-shortest", out], check=True)
    return out
