"""Regenerate checked-in B machine corpora from the example DSL files."""

import argparse
import subprocess
import sys
from pathlib import Path


def parse_args():
    repo_root = Path(__file__).resolve().parents[1]
    examples_dir = repo_root / "examples"
    parser = argparse.ArgumentParser(
        description="Regenerate the example corpus from the DSL sources."
    )
    parser.add_argument(
        "--examples-dir",
        default=str(examples_dir),
        help=f"Directory containing source .dsl files (default: {examples_dir}).",
    )
    parser.add_argument(
        "--output-dir",
        help=(
            "Directory to write .mch files to. Defaults to examples/ for offensive style "
            "and examples/defensive/ for defensive style."
        ),
    )
    parser.add_argument(
        "--defensive",
        action="store_true",
        help="Generate the defensive-style corpus.",
    )
    return parser.parse_args()


def resolve_output_dir(repo_root, examples_dir, explicit_output_dir, defensive):
    if explicit_output_dir:
        return Path(explicit_output_dir).resolve()
    if defensive:
        return (repo_root / "examples" / "defensive").resolve()
    return examples_dir.resolve()


def regenerate_file(main_py, dsl_path, output_path, defensive):
    command = [sys.executable, str(main_py)]
    if defensive:
        command.append("--defensive")
    command.extend([str(dsl_path), str(output_path)])

    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    return completed


def main():
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    main_py = repo_root / "dsl" / "main.py"
    examples_dir = Path(args.examples_dir).resolve()
    output_dir = resolve_output_dir(repo_root, examples_dir, args.output_dir, args.defensive)

    dsl_files = sorted(path for path in examples_dir.glob("*.dsl") if path.is_file())
    if not dsl_files:
        print(f"No .dsl files found under {examples_dir}")
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)
    failures = []

    for dsl_path in dsl_files:
        output_path = output_dir / f"{dsl_path.stem}.mch"
        completed = regenerate_file(main_py, dsl_path, output_path, args.defensive)
        if completed.returncode == 0:
            print(f"OK {dsl_path.name} -> {output_path}")
            continue

        print(f"FAIL {dsl_path.name} -> {output_path}")
        if completed.stdout.strip():
            print(completed.stdout.strip())
        if completed.stderr.strip():
            print(completed.stderr.strip())
        failures.append(dsl_path.name)

    if failures:
        print("")
        print(f"Regeneration failed for {len(failures)} file(s): {', '.join(failures)}")
        return 1

    style = "defensive" if args.defensive else "offensive"
    print("")
    print(f"Regenerated {len(dsl_files)} {style}-style machine(s) in {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
