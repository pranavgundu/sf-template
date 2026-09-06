"""Create and inspect runnable research projects."""

import argparse
import csv
import json
import re
from pathlib import Path
import shutil
import sys
import tomllib

from . import __version__
from .analysis import analyze, read_measurements
from .presets import ADDONS, FRAMEWORKS, dependencies
from .setup import configure

ROOT = Path(__file__).resolve().parent.parent
ASSETS = Path(__file__).resolve().parent / "assets"
if not ASSETS.is_dir():
    ASSETS = ROOT
TRACKS = {
    "science": "Controlled experiments",
    "engineering": "Prototypes and design tests",
    "computational": "Models and simulations",
    "data-analysis": "Studying an existing dataset",
    "observational": "Field observations and associations",
    "literature-review": "Comparing and synthesizing published research",
    "replication": "Repeating a published study",
    "general": "Open-ended research",
    "ml": "Machine learning (sklearn, torch, or jax)",
    "computer-vision": "PyTorch, Torchvision, and image tools",
    "data-analytics": "Dataframes, statistics, and visualization",
    "nlp": "PyTorch and Hugging Face text tools",
}
REQUIRED = (
    "pyproject.toml", "configs/experiment.toml", "project/main.py",
    "project/analysis.py", "project/__init__.py", "tests/test_project.py",
    "data/raw/measurements.csv", "references/sources.csv",
)


def init_project(destination, title, track, framework=None, addons=()):
    destination = Path(destination)
    if destination.exists():
        raise ValueError(f"Destination already exists: {destination}. Choose a new folder.")
    if not title.strip() or "\n" in title or "\r" in title:
        raise ValueError("Project title must be a nonempty single line.")
    if track not in TRACKS:
        raise ValueError(f"Unknown starter: {track}")
    packages, selected_framework = dependencies(track, framework, addons)
    shutil.copytree(ASSETS / "template", destination)
    # Bundle the analysis code so the generated project has no dependency on this tool.
    shutil.copyfile(Path(__file__).with_name("analysis.py"), destination / "project/analysis.py")
    shutil.copyfile(Path(__file__).with_name("__init__.py"), destination / "project/__init__.py")
    shutil.copyfile(ASSETS / "tracks" / f"{track}.toml", destination / "configs/experiment.toml")
    metadata = destination / "pyproject.toml"
    package_name = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "research-project"
    metadata.write_text(
        metadata.read_text(encoding="utf-8")
        .replace('name = "research-project"', f'name = {json.dumps(package_name)}')
        .replace("dependencies = []", "dependencies = " + json.dumps(packages, indent=2)),
        encoding="utf-8",
    )
    ignore = destination / ".gitignore"
    ignore.write_text(
        ignore.read_text(encoding="utf-8").replace("!data/raw/measurements.csv\n", ""),
        encoding="utf-8",
    )
    (destination / "project.json").write_text(json.dumps({
        "title": title, "track": track, "template_version": __version__,
        "framework": selected_framework, "addons": sorted(set(addons)),
    }, indent=2) + "\n", encoding="utf-8")


def check_project(directory):
    directory = Path(directory)
    if not directory.is_dir():
        raise ValueError(f"Project directory not found: {directory}")
    issues = [f"Missing: {name}" for name in REQUIRED if not (directory / name).is_file()]
    for name in ("pyproject.toml", "configs/experiment.toml"):
        path = directory / name
        if path.is_file():
            try:
                tomllib.loads(path.read_text(encoding="utf-8"))
            except tomllib.TOMLDecodeError as error:
                issues.append(f"Invalid TOML: {name}: {error}")
    return issues


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        argv = ["init"]
    parser = argparse.ArgumentParser(description="Science Fair Template: create, check, and analyze research projects.")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("starters", help="List available project starters")
    init = commands.add_parser("init", help="Create a project in a new folder")
    init.add_argument("destination", type=Path, nargs="?")
    init.add_argument("--title")
    init.add_argument("--track", "--starter", dest="track", choices=TRACKS)
    init.add_argument("--framework", choices=FRAMEWORKS, help="ML framework (ml starter only; default: sklearn)")
    init.add_argument("--add", choices=ADDONS, action="append", help="Add a package set; repeat for multiple sets")
    mode = init.add_mutually_exclusive_group()
    mode.add_argument("--interactive", action="store_true", help="Prompt for options not supplied as flags")
    mode.add_argument("--no-input", action="store_true", help="Use defaults for omitted options without prompting")
    check = commands.add_parser("check", help="Check project files and TOML syntax")
    check.add_argument("directory", type=Path)
    analysis = commands.add_parser("analyze", help="Summarize independent units in a CSV")
    analysis.add_argument("source", type=Path)
    analysis.add_argument("--output", type=Path, required=True)
    analysis.add_argument("--replicates", choices=("error", "mean"), default="error")
    args = parser.parse_args(argv)
    try:
        if args.command == "starters":
            for name, description in TRACKS.items():
                packages, _ = dependencies(name)
                print(f"{name:18} {description}")
                print("  " + (", ".join(packages) or "No research packages"))
        elif args.command == "init":
            if not args.no_input and (args.interactive or args.destination is None or args.title is None or args.track is None):
                args = configure(args, TRACKS)
            args.destination = args.destination or Path("my-research")
            args.title = args.title or args.destination.name
            args.track = args.track or "science"
            args.add = args.add or []
            init_project(args.destination, args.title, args.track, args.framework, args.add)
            print(f"Created {args.destination}. Run: cd {args.destination}")
            print("Then: uv sync && uv run python -m project.main")
        elif args.command == "check":
            issues = check_project(args.directory)
            for issue in issues:
                print(issue)
            print(f"{len(issues)} issue(s). Checks files and syntax only.")
            return 1 if issues else 0
        else:
            summary = analyze(args.source, args.output, args.replicates)
            print(f"Analyzed {len(summary)} group(s). Results: {args.output}")
    except (EOFError, KeyboardInterrupt):
        print("\nSetup cancelled.", file=sys.stderr)
        return 130
    except (ValueError, OSError, UnicodeError, csv.Error, OverflowError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    return 0
