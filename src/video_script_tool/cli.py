"""
Command line interface for autobrowser package
"""

import argparse
from ipydex import IPS, activate_ips_on_exception
from . import core

activate_ips_on_exception()


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("project_dir", help="specify project dir (see README)")

    args = parser.parse_args()

    core.main(args.project_dir)
