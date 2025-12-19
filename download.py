import yt_dlp


def time_to_seconds(time_str):
    """
    Converts HH:MM:SS or MM:SS to total seconds.
    Example: '01:30' -> 90.0
    """
    parts = list(map(float, time_str.split(":")))
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    elif len(parts) == 2:
        return parts[0] * 60 + parts[1]
    else:
        return parts[0]


def download_clip(video_url, start_time, end_time, output_filename="clip.mp4"):
    """
    Downloads only the specific segment of the video.
    """
    # 1. Convert timestamps to seconds (yt-dlp library expects numbers)
    start_sec = time_to_seconds(start_time)
    end_sec = time_to_seconds(end_time)

    print(f"✂️ Cutting video from {start_sec}s to {end_sec}s...")

    # 2. Define options
    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": output_filename,
        # This is the magic part: it downloads ONLY the range
        "download_ranges": lambda info, ydl: [
            {"start_time": start_sec, "end_time": end_sec}
        ],
        # Force precise cuts (re-encodes the start/end keyframes so it's not black screen)
        "force_keyframes_at_cuts": True,
        "quiet": False,
        "overwrites": True,
    }

    # 3. Download
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        print(f"✅ Success! Saved to {output_filename}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


# --- USAGE EXAMPLE ---
if __name__ == "__main__":
    # Example: Downloading a 30-second clip (from 10:00 to 10:30)
    URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    START = "00:10"
    END = "00:40"

    download_clip(URL, START, END, "my_highlight.mp4")
