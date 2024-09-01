import subprocess
import os
import glob
import argparse

from scipy.io import wavfile
import noisereduce as nr

from . import util

from ipydex import IPS, Container


class MainManager:
    def __init__(self, args):
        self.project_dir = args.project_dir
        self.produce_snippets_flag = not (args.omit_snippet_production == True)
        self.only_audio_preprocessing_flag = args.only_audio_preprocessing
        self.audio_preprocessing_flag = args.audio_preprocessing or args.only_audio_preprocessing

        self.file_list_fpath = os.path.join(self.project_dir, "filelist.txt")

        self.audio_files = None
        self.image_files = None
        self.noise_fpath = None
        self.use_preprocessed_audio = False

        self.audio_dir_name = "audio"
        self.audio_pp_dir_name = "audio_pp"
        self.audio_pp_dirpath = os.path.join(self.project_dir, self.audio_pp_dir_name)

        self.data_loaded = False

    def main(self):
        if not self.produce_snippets_flag and self.only_audio_preprocessing_flag:
            msg = "Inconsistent arguments (preprocessing audio only possible during snippet production, but this is omitted)"
            raise ValueError(msg)

        if self.audio_preprocessing_flag:
            self.do_audio_preprocessing()
            if self.only_audio_preprocessing_flag:
                exit()
        if self.produce_snippets_flag:
            self.produce_snippets()
        self.create_video()

    def load_data(self):

        # prevent double loading
        if self.data_loaded:
            return

        assert self.project_dir is not None
        pattern_audio = os.path.join(self.project_dir, "audio", "*.wav")
        self.audio_files = glob.glob(pattern_audio)
        self.audio_files.sort()

        self.noise_fpath = os.path.join(self.project_dir, "audio", "noise", "noise.wav")
        if not os.path.isfile(self.noise_fpath):
            self.noise_fpath = None
        else:
            _, self.noise_data = wavfile.read(self.noise_fpath)

        pattern_img = os.path.join(self.project_dir, "images", "*.png")
        self.image_files = glob.glob(pattern_img)
        self.image_files.sort()

        assert len(self.audio_files) > 0
        assert len(self.audio_files) == len(self.image_files)

        self.data_loaded = True

    def do_audio_preprocessing(self):
        print("perform audio preprocessing")
        self.load_data()

        os.makedirs(self.audio_pp_dirpath, exist_ok=True)

        for audio_fpath in self.audio_files:

            rate, audio_data = wavfile.read(audio_fpath)

            assert self.noise_data is not None
            _, noise = wavfile.read(self.noise_fpath)

            reduced_noise_audio = nr.reduce_noise(y=audio_data[:, 0], sr=rate, stationary=True, prop_decrease=0.75)

            target_fpath = self.get_adapted_audio_fpath(audio_fpath, force_adapted_path=True)

            wavfile.write(target_fpath, rate, reduced_noise_audio)
            print(f"File written: {target_fpath}")

        self.use_preprocessed_audio = True

    def get_adapted_audio_fpath(self, audio_fpath, force_adapted_path=False):
        if self.use_preprocessed_audio or force_adapted_path:
            return audio_fpath.replace(os.path.join(self.project_dir, self.audio_dir_name), self.audio_pp_dirpath)
        else:
            return audio_fpath


    def create_video(self, produce_snippets=True):

        output_path = os.path.join(self.project_dir, "combined-video.mp4")
        cmd = " ".join(
            ["ffmpeg", "-f", "concat", "-safe", "0", "-i", self.file_list_fpath, "-c", "copy", output_path]
        )

        os.system(cmd)

    def produce_snippets(self):

        self.load_data()
        SNIPPET_DIR = "snippets"  # relative to project_dir
        SNIPPET_DIR_FULL = os.path.join(self.project_dir, SNIPPET_DIR)

        os.makedirs(SNIPPET_DIR_FULL, exist_ok=True)

        file_list_entries = []
        for i, (image_fpath, audio_fpath) in enumerate(zip(self.image_files, self.audio_files), start=1):
            duration = util.get_audio_duration(audio_fpath)

            audio_fpath = self.get_adapted_audio_fpath(audio_fpath)
            video_snippet_fpath_full = os.path.join(SNIPPET_DIR_FULL, f"temp{i:04d}.mp4")

            # delete existing snippet file (prevent ffmpeg from askinig)
            if os.path.isfile(video_snippet_fpath_full):
                os.remove(video_snippet_fpath_full)

            cmd_list = [
                "ffmpeg",
                "-loop",
                "1",
                "-i",
                image_fpath,
                "-i",
                audio_fpath,
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
                video_snippet_fpath_full,
            ]

            cmd = " ".join(cmd_list)
            os.system(cmd)

            # ffmpeg expects the paths in the filelist relative to the path of the filelist
            video_snippet_fpath_rel = os.path.join(SNIPPET_DIR, f"temp{i:04d}.mp4")
            file_list_entries.append(f"file {video_snippet_fpath_rel}")

        if 1:
            with open(self.file_list_fpath, "w") as fp:
                fp.write("\n".join(file_list_entries))
                fp.write("\n")


def main(project_dir):
    mm = MainManager(project_dir)
    mm.main()
