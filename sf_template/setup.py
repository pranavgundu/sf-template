"""Terminal setup prompts. Enter accepts the displayed default."""

from pathlib import Path
import re

from .presets import ADDONS, dependencies


def ask_text(label, default):
    return input(f"{label} [{default}]: ").strip() or default


def ask_choice(label, choices, default):
    names = list(choices)
    print(f"\n{label}")
    for index, name in enumerate(names, 1):
        marker = " (default)" if name == default else ""
        print(f"  {index}. {name}: {choices[name]}{marker}")
    while True:
        answer = input(f"Choose a number or name [{default}]: ").strip() or default
        if answer.isdigit() and 1 <= int(answer) <= len(names):
            return names[int(answer) - 1]
        if answer in choices:
            return answer
        print("Choose one of the listed numbers or names.")


def ask_addons():
    names = list(ADDONS)
    print("\nOptional packages (choose several, or press Enter for none)")
    for index, name in enumerate(names, 1):
        print(f"  {index}. {name}: {', '.join(ADDONS[name])}")
    while True:
        answer = input("Numbers or names, separated by commas [none]: ").strip()
        if not answer or answer.lower() == "none":
            return []
        selected = []
        for token in answer.split(","):
            token = token.strip()
            if token.isdigit() and 1 <= int(token) <= len(names):
                token = names[int(token) - 1]
            if token not in ADDONS:
                print("Choose listed numbers or names, or enter none.")
                break
            if token not in selected:
                selected.append(token)
        else:
            return selected


def configure(args, tracks):
    print("\nScience Fair Template")
    print("Your research type and framework determine the packages included.")
    print("Press Enter for defaults. Ctrl+C cancels setup.\n")
    if args.title is None:
        args.title = ask_text("Project name", "My research")
    if args.destination is None:
        default = re.sub(r"[^a-z0-9]+", "-", args.title.lower()).strip("-") or "my-research"
        args.destination = Path(ask_text("Project folder", default)).expanduser()
    if args.destination.exists():
        raise ValueError(f"Destination already exists: {args.destination}. Choose a new folder.")
    if args.track is None:
        options = {
            name: description + "\n     Packages: " + ", ".join(dependencies(name)[0])
            for name, description in tracks.items()
        }
        args.track = ask_choice("What kind of research?", options, "science")
    if args.track == "ml" and args.framework is None:
        args.framework = ask_choice("ML framework", {
            "sklearn": "scikit-learn",
            "torch": "PyTorch + Lightning",
            "jax": "JAX + Flax + Optax",
        }, "sklearn")
    selected, _ = dependencies(args.track, args.framework)
    print(f"\nPackages for {args.track}: " + ", ".join(selected))
    if args.add is None:
        args.add = ask_addons()
    packages, _ = dependencies(args.track, args.framework, args.add)
    print(f"\nCreating {args.title} in {args.destination}")
    print("Selected packages: " + ", ".join(packages))
    return args
