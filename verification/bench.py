import argparse
import csv
import re
import subprocess
import time
from pathlib import Path
from typing import Iterable, List, Optional

from verify import DEFAULT_PROBCLI, _probcli_scope_args, output_is_expected_terminal_deadlock


DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_STATE_LIMITS = (100, 1000, 5000)
STATE_PATTERNS = (
    re.compile(r"visited states:\s*(\d+)", re.IGNORECASE),
    re.compile(r"states analysed:\s*(\d+)", re.IGNORECASE),
)
FAILURE_PATTERNS = (
    "*** counter example found ***",
    "*** deadlock state found ***",
    "deadlock found",
    "counterexample found",
    "invariant violation",
    "assertion violation",
    "properties are false",
    "*** error occurred ***",
    "*** serious error occurred ***",
    "abnormal termination of probcli",
    "total errors: 1",
)


def iter_mch_files(examples_dir: Path) -> Iterable[Path]:
    return sorted(path for path in examples_dir.rglob("*.mch") if path.is_file())


def parse_states_explored(output: str) -> Optional[int]:
    for pattern in STATE_PATTERNS:
        match = pattern.search(output)
        if match:
            return int(match.group(1))
    return None


def output_indicates_failure(output: str) -> bool:
    if output_is_expected_terminal_deadlock(output):
        return False

    lowered = output.lower()
    if "no deadlock found" in lowered:
        lowered = lowered.replace("no deadlock found", "")
    if "no counter example found" in lowered:
        lowered = lowered.replace("no counter example found", "")
    if "no counterexample found" in lowered:
        lowered = lowered.replace("no counterexample found", "")
    return any(pattern in lowered for pattern in FAILURE_PATTERNS)


def run_benchmark(mch_path: Path, state_limit: int, timeout: int, probcli: str) -> dict:
    command = [
        probcli,
        str(mch_path),
        *_probcli_scope_args(mch_path),
        "-mc",
        str(state_limit),
    ]
    start = time.perf_counter()
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        elapsed = time.perf_counter() - start
        output = "\n".join(
            part.strip() for part in (completed.stdout, completed.stderr) if part and part.strip()
        )
        return {
            "contract": mch_path.stem,
            "state_limit": state_limit,
            "time_seconds": f"{elapsed:.6f}",
            "passed": completed.returncode == 0 and not output_indicates_failure(output),
            "states_explored": parse_states_explored(output) or "",
        }
    except FileNotFoundError:
        elapsed = time.perf_counter() - start
        return {
            "contract": mch_path.stem,
            "state_limit": state_limit,
            "time_seconds": f"{elapsed:.6f}",
            "passed": False,
            "states_explored": "",
        }
    except subprocess.TimeoutExpired:
        elapsed = time.perf_counter() - start
        return {
            "contract": mch_path.stem,
            "state_limit": state_limit,
            "time_seconds": f"{elapsed:.6f}",
            "passed": False,
            "states_explored": "",
        }


def write_csv(rows: List[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=["contract", "state_limit", "time_seconds", "passed", "states_explored"],
        )
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Benchmark Classical B machines with ProB.")
    parser.add_argument(
        "--examples-dir",
        default=str(script_dir.parent / "examples"),
        help="Directory to scan for .mch files.",
    )
    parser.add_argument(
        "--output",
        default=str(script_dir / "benchmarks.csv"),
        help="Path to the CSV file to write.",
    )
    parser.add_argument(
        "--probcli",
        default=DEFAULT_PROBCLI,
        help=f"ProB CLI executable or path to use (default: {DEFAULT_PROBCLI}).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"Timeout in seconds for each probcli benchmark run (default: {DEFAULT_TIMEOUT_SECONDS}).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    examples_dir = Path(args.examples_dir).resolve()
    output_path = Path(args.output).resolve()
    rows: List[dict] = []

    mch_files = list(iter_mch_files(examples_dir))
    if not mch_files:
        print(f"No .mch files found under {examples_dir}")
        return 1

    for mch_path in mch_files:
        for state_limit in DEFAULT_STATE_LIMITS:
            row = run_benchmark(mch_path, state_limit, args.timeout, args.probcli)
            rows.append(row)
            print(
                f"{mch_path.name} @ {state_limit}: "
                f"passed={row['passed']} time={row['time_seconds']}s states={row['states_explored'] or 'n/a'}"
            )

    write_csv(rows, output_path)
    print(f"Benchmark CSV written to {output_path}")
    return 0 if all(row["passed"] for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
