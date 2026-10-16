"""The `tent-pack` command: run the pack file's checks and, if they pass and
the pack file names an output, write the zip."""

import argparse
import os
import pathlib
import sys

from .errors import PackError
from .loader import find_pack_file, load_pack
from .sizes import format_size

LABELS = {"pass": " OK ", "warn": "WARN", "fail": "FAIL"}
COLOURS = {"pass": "32", "warn": "33", "fail": "31"}


def _use_colour(stream, disabled):
    if disabled or os.environ.get("NO_COLOR") or not stream.isatty():
        return False
    if os.name == "nt":
        os.system("")  # switches on ANSI handling in the Windows console
    return True


def _label(status, colour):
    text = "[{}]".format(LABELS[status])
    return "\033[{}m{}\033[0m".format(COLOURS[status], text) if colour else text


def build_parser():
    p = argparse.ArgumentParser(
        prog="tent-pack",
        description="Check your coursework and pack it into a zip for upload.",
    )
    p.add_argument("-C", "--dir", default=".", help="coursework folder (default: here)")
    p.add_argument("-f", "--file", help="pack file to use (default: pack.toml or pack.py)")
    p.add_argument(
        "-n", "--verify", "--dry-run", dest="verify", action="store_true",
        help="run the checks but do not write the zip",
    )
    p.add_argument("--no-color", action="store_true", help="plain output")
    return p


def run(args, out):
    colour = _use_colour(out, args.no_color)
    root = pathlib.Path(args.dir).resolve()
    if not root.is_dir():
        raise PackError("{} is not a folder".format(args.dir))
    pack_file = find_pack_file(root, args.file)
    pack = load_pack(pack_file)

    print("tent-pack: {} ({}, format {})".format(
        pack.name or root.name, pack_file.name, pack.format), file=out)
    ctx = pack.context(root)
    results = pack.run_checks(ctx)
    for r in results:
        print("{} {}".format(_label(r.status, colour), r.name), file=out)
        if r.message:
            print("       {}".format(r.message), file=out)
        for line in r.detail.splitlines():
            print("         {}".format(line), file=out)

    counts = {s: sum(1 for r in results if r.status == s) for s in LABELS}
    print("\n{} passed, {} warning(s), {} failed".format(
        counts["pass"], counts["warn"], counts["fail"]), file=out)

    if counts["fail"]:
        print("Not packing: fix the failures above and run tent-pack again."
              if pack.output and not args.verify else "Checks failed.", file=out)
        return 1
    if args.verify:
        print("Verify only: nothing was packed.", file=out)
    elif pack.output:
        target, count = pack.pack(ctx)
        print("Packed {} file(s) into {} ({}).".format(
            count, target.name, format_size(target.stat().st_size)), file=out)
        print("Upload {} to Canvas.".format(target.name), file=out)
    else:
        print("All checks passed.", file=out)
    return 0


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return run(args, sys.stdout)
    except PackError as e:
        print("tent-pack: error: {}".format(e), file=sys.stderr)
        return 2
