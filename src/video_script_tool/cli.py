"""
Command line interface for autobrowser package
"""

import argparse
from ipydex import IPS, activate_ips_on_exception

activate_ips_on_exception()


def main():

    from . import core
    parser = argparse.ArgumentParser()
    parser.add_argument("project_dir", help="specify project dir (see README)")
    parser.add_argument("--only-audio-preprocessing", "-oapp", help="only audio preprocessing", action="store_true")
    parser.add_argument("--audio-preprocessing", "-app", help="audio preprocessing, then video creation", action="store_true")
    parser.add_argument("--omit-snippet-production", "-osp", help="do not produce new snippets, but use existing", action="store_true")
    parser.add_argument("--snippet-limit", "-sl", help="do not produce new snippets, but use existing", default=None, type=int)

    args = parser.parse_args()

    core.main(args)


def capture_slides():

    parser = argparse.ArgumentParser()
    parser.add_argument("project_dir", help="specify project dir (see README)")
    parser.add_argument("url", help="specify url of presentation")
    parser.add_argument("--first-slide-number", "-fsn", help="specify first slide number", type=int, default=1)
    args = parser.parse_args()

    from . import capture_slides
    capture_slides.main(args)

def record_audio_gui():

    parser = argparse.ArgumentParser()
    parser.add_argument("--suffix", help="set a path suffix like '_a'", default="")
    parser.add_argument("project_dir", help="specify project dir (see README)")
    args = parser.parse_args()

    from . import gui
    gui.main(args)


def extract_texts():

    parser = argparse.ArgumentParser()
    parser.add_argument("project_dir", help="specify project dir (see README)")
    parser.add_argument("url", help="specify url of markdown source code of presentation")

    cache_group = parser.add_mutually_exclusive_group()
    cache_group.add_argument("--force-reload", "-fr", help="force that a cached version is discarded", action="store_true")
    cache_group.add_argument("--force-cache", "-fc", help="force that a cached version is used", action="store_true")
    cache_group.add_argument("--force-source", "-fs", help="force that a specific file is used (no download)", default=None)

    parser.add_argument("--suffix", help="set a path suffix like '_a'", default="")

    args = parser.parse_args()

    from . import md_processor

    md_processor.extract_text(args)
