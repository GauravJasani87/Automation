import os
import math
import platform
import shutil
from yt_dlp import YoutubeDL
from moviepy import VideoFileClip, TextClip, CompositeVideoClip


def configure_ffmpeg():
    """
    On Termux, imageio-ffmpeg's bundled binary isn't built for Android,
    so we point moviepy/imageio at Termux's native system ffmpeg instead.
    On other platforms (Windows/Mac/Linux desktop), fall back to the
    bundled binary from imageio_ffmpeg as before.
    """
    is_termux = "com.termux" in os.environ.get("PREFIX", "")

    if is_termux:
        system_ffmpeg = shutil.which("ffmpeg")
        if not system_ffmpeg:
            raise RuntimeError(
                "ffmpeg not found. On Termux, run: pkg install ffmpeg"
            )
        os.environ["IMAGEIO_FFMPEG_EXE"] = system_ffmpeg
    else:
        import imageio_ffmpeg
        os.environ["IMAGEIO_FFMPEG_EXE"] = imageio_ffmpeg.get_ffmpeg_exe()


configure_ffmpeg()


def download_video(url, output_folder="downloads"):
    """Download the YouTube video using yt-dlp, saving with a unique filename."""
    os.makedirs(output_folder, exist_ok=True)
    ydl_opts = {
        "format": "best[ext=mp4]",
        "outtmpl": os.path.join(output_folder, "%(title)s.%(ext)s"),
        "extractor_args": {"youtube": {"player_client": ["android"]}},
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
    return filename


def get_font_path():
    """
    Return a valid .ttf font path depending on the platform, so the same
    script works unmodified on Windows, macOS, Linux, and Android (Termux).
    """
    candidates = []

    # Termux sets a $PREFIX env var pointing inside com.termux -- most
    # reliable way to detect we're running on an Android/Termux device.
    is_termux = "com.termux" in os.environ.get("PREFIX", "")
    system = platform.system()  # 'Windows', 'Darwin', or 'Linux'

    if is_termux:
        candidates += [
            "/data/data/com.termux/files/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
            "/data/data/com.termux/files/usr/share/fonts/TTF/DejaVuSans.ttf",
        ]
    elif system == "Windows":
        candidates.append("C:\\Windows\\Fonts\\arial.ttf")
    elif system == "Darwin":  # macOS
        candidates.append("/System/Library/Fonts/Supplemental/Arial.ttf")
    else:  # generic Linux desktop
        candidates += [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ]

    for path in candidates:
        if os.path.exists(path):
            return path

    hint = (
        "On Termux, run: pkg install ttf-dejavu"
        if is_termux
        else "Please install a TTF font or update get_font_path() with a valid path."
    )
    raise FileNotFoundError(f"No usable font found for watermark text. {hint}")


def split_into_shorts(video_path, chunk_length=60, output_folder="shorts"):
    """Split a video into chunks of chunk_length seconds each, with a 'Part X' watermark."""
    os.makedirs(output_folder, exist_ok=True)

    clip = VideoFileClip(video_path)
    total_duration = clip.duration
    num_chunks = math.ceil(total_duration / chunk_length)

    print(f"Video duration: {total_duration:.1f}s -> {num_chunks} chunks")

    font_path = get_font_path()

    for i in range(num_chunks):
        start = i * chunk_length
        end = min((i + 1) * chunk_length, total_duration)
        chunk = clip.subclipped(start, end)

        watermark_text = f"Part {i+1}"
        watermark = (
            TextClip(
                text=watermark_text,
                font=font_path,
                font_size=50,
                color="white",
                stroke_color="black",
                stroke_width=2,
            )
            .with_duration(chunk.duration)
            .with_position(("center", "top"))
        )

        final_chunk = CompositeVideoClip([chunk, watermark])

        output_file = os.path.join(output_folder, f"short_{i+1}.mp4")
        final_chunk.write_videofile(output_file, codec="libx264", audio_codec="aac")
        print(f"Saved: {output_file}")

    clip.close()


if __name__ == "__main__":
    user_input = input("Paste a YouTube link OR a local video file path: ").strip()

    if user_input.lower().startswith("http"):
        print("Detected a YouTube link. Downloading...")
        video_file = download_video(user_input)
    else:
        # Remove accidental quotes if user copy-pasted path with quotes
        video_file = user_input.strip('"')
        if not os.path.exists(video_file):
            print(f"Error: File not found at '{video_file}'")
            exit(1)
        print(f"Detected a local file: {video_file}")

    split_into_shorts(video_file, chunk_length=60)