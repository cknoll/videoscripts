import subprocess
import os


def get_audio_duration(audio_file):
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            audio_file,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return float(result.stdout)


def create_video(num_pairs):
    with open("input.txt", "w") as f:
        for i in range(1, num_pairs + 1):
            image = f"image{i}.jpg"
            audio = f"audio{i}.wav"

            duration = get_audio_duration(audio)

            temp_video = f"temp{i}.mp4"
            subprocess.run(
                [
                    "ffmpeg",
                    "-loop",
                    "1",
                    "-i",
                    image,
                    "-i",
                    audio,
                    "-c:v",
                    "libx264",
                    "-tune",
                    "stillimage",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    "-pix_fmt",
                    "yuv420p",
                    "-t",
                    str(duration),
                    temp_video,
                ]
            )

            f.write(f"file '{temp_video}'\n")

    subprocess.run(["ffmpeg", "-f", "concat", "-safe", "0", "-i", "input.txt", "-c", "copy", "output.mp4"])

    # Clean up temporary files
    for i in range(1, num_pairs + 1):
        os.remove(f"temp{i}.mp4")
    os.remove("input.txt")


# Usage
create_video(N)  # Replace N with the number of image-audio pairs
