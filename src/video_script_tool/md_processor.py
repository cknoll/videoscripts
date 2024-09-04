import requests
import os
import re
import time
import glob

from . import util

from ipydex import IPS

pjoin = os.path.join

class TextExtractor:

    def __init__(self, args):
        self.project_dir = args.project_dir
        self.url = args.url
        self.force_reload = args.force_reload
        self.force_cache = args.force_cache
        self.force_source = args.force_source
        self.slides_full_source_fpath = pjoin(self.project_dir, "slides_full_source.md")
        self.target_fpath = pjoin(self.project_dir, "all_texts.md")

        self.slides_full_source = None
        self.slide_src_list = None

        self.image_files = None
        self.slide_fragment_numbers: dict = None
        self.slide_fragment_number_list: list = None

        self.fragment_texts: list[list] = None

    def perform_text_extraction(self):
        self.download_source()
        self.split_into_slides()
        self.extract_texts_from_special_comments()
        self.write_fragment_texts()

    def download_source(self) -> None:

        if self.force_source:
            self.slides_full_source_fpath = self.force_source

            print(f"using enforced version of {self.slides_full_source_fpath} (no download)")
            with open(self.slides_full_source_fpath, "r") as fp:
                self.slides_full_source = fp.read()
            return

        if os.path.isfile(self.slides_full_source_fpath):
            stat = os.stat(self.slides_full_source_fpath)

            # just load cached file
            if (time.time()- stat.st_mtime)/60 < 10 or self.force_cache:

                print(f"using cached version of {self.slides_full_source_fpath} (no download)")
                with open(self.slides_full_source_fpath, "r") as fp:
                    self.slides_full_source = fp.read()
                return

        if self.url.endswith("/download"):
            url = self.url
        else:
            url = f'{self.url.rstrip("/").rstrip("#")}/download'

        print(f"Downloading {url}")
        res = requests.get(url)
        if not res.status_code == 200:
            msg = f"unexpected status code for url {url}"
            raise requests.HTTPError(msg)

        print(f"Saving file: {self.slides_full_source_fpath}")
        with open(self.slides_full_source_fpath, "wb") as fp:
            fp.write(res.content)

        self.slides_full_source = res.content.decode("utf8")

    def split_into_slides(self):

        self.slide_src_list = self.slides_full_source.split("\n\n---\n\n")

        # ignore optional slideOptions
        if "\nslideOptions:\n" in self.slide_src_list[0]:
            self.slide_src_list.pop(0)

        # find out how much fragments each slide should have, based on the image filenames
        pattern_img = os.path.join(self.project_dir, "images", "*.png")
        self.image_files = glob.glob(pattern_img)
        self.image_files.sort()

        self.slide_fragment_numbers = util.get_image_fragment_numbers(self.image_files)

        # convert values to list (sorted by keys)
        self.slide_label_list, self.slide_fragment_number_list = list(
            zip(*sorted(self.slide_fragment_numbers.items()))
        )

    def extract_texts_from_special_comments(self):

        compiled_re = re.compile(r"\<!--f[0-9]*\s*(.*?)/--\>", re.DOTALL)
        self.fragment_texts = []

        for slide_idx, slide_src in enumerate(self.slide_src_list, start=0):
            slide_fragment_texts = compiled_re.findall(slide_src)
            slide_fragment_texts = [elt.strip() for elt in slide_fragment_texts]

            n1 = len(slide_fragment_texts)
            n2 = self.slide_fragment_number_list[slide_idx]

            if  n1 != n2:
                print(util.yellow(f"Slide {slide_idx + 1}: found {n1} fragment texts, but expected {n2}"))
            if  n1 < n2:
                print("  -> filling with placeholder texts")
                for j in range(n2 - n1):
                    slide_fragment_texts.append(f"slide {self.slide_label_list[slide_idx]} fragment {n1 + j + 1}")
            elif n1 > n2:
                print("  -> ignoring some of the texts")
                slide_fragment_texts = slide_fragment_texts[:n2]

            self.fragment_texts.append(slide_fragment_texts)



    def write_fragment_texts(self):

        # step 1: flatten the list
        texts = []
        for slide_fragments in self.fragment_texts:
            for fragment_text in slide_fragments:
                texts.append(fragment_text.strip())

        # step 2: write to file
        with open(self.target_fpath, "w") as fp:
            fp.write("\n\n---\n\n".join(texts))
            fp.write("\n")

        print(f"{len(texts)} fragment texts written to {self.target_fpath}")


def extract_text(args):

    te = TextExtractor(args)
    te.perform_text_extraction()
    # IPS(print_tb=False)
