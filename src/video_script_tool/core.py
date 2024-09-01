import subprocess
import os
import glob
import argparse

from ipydex import IPS


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


def get_data():
    image_files = glob.glob("images/*.png")
    image_files.sort()
    audio_files = glob.glob("audio/*.wav")
    audio_files.sort()

    assert len(audio_files) > 0
    assert len(audio_files) == len(image_files)

    return image_files, audio_files


def create_video():

    image_files, audio_files = get_data()

    file_list_entries = []
    for i, (image, audio) in enumerate(zip(image_files, audio_files), start=1):

        duration = get_audio_duration(audio)

        video_snippet_fname = f"temp{i:04d}.mp4"
        cmd_list = [
            "ffmpeg",
            "-loop",
            "1",
            "-i",
            image,
            "-i",
            audio,
            "-c:v",
            "libx264",
            '-vf "pad=ceil(iw/2)*2:ceil(ih/2)*2"',  # this deals with uneven image formats
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
            video_snippet_fname,
        ]

        os.system(" ".join(cmd_list))

        file_list_entries.append(f"file {video_snippet_fname}")

    if 1:
        with open("input.txt", "w") as fp:
            fp.write("\n".join(file_list_entries))
            fp.write("\n")

    cmd = " ".join(
        ["ffmpeg", "-f", "concat", "-safe", "0", "-i", "input.txt", "-c", "copy", "output.mp4"]
    )

    os.system(cmd)

    if 0:
        # Clean up temporary files
        for fname in file_list_entries:
            os.remove(fname)
        os.remove("input.txt")


def main(project_dir):
    pass
