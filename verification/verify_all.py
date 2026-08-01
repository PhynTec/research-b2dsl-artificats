import argparse
import sys
from pathlib import Path
from typing import Iterable, List

from verify import (
    DEFAULT_MODEL_CHECK_STATE_LIMIT,
    DEFAULT_PROBCLI,
    DEFAULT_TIMEOUT_SECONDS,
    VerificationResult,
    verify_single,
)


STATUS_SYMBOLS = {
    "pass": "\u2705",
    "fail": "\u274c",
    "timeout": "\u23f1\ufe0f",
}


def iter_mch_files(examples_dir: Path) -> Iterable[Path]:
    return sorted(path for path in examples_dir.rglob("*.mch") if path.is_file())


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def print_summary(results: List[VerificationResult]) -> None:
    print("Status Contract Time(s) Details")
    for result in results:
        symbol = STATUS_SYMBOLS[result.status]
        details = result.error_description or "ok"
        print(
            f"{symbol} {_display_path(result.mch_path):<30} "
            f"{result.elapsed_seconds:>7.3f} {details}"
        )

    passed = sum(1 for result in results if result.status == "pass")
    failed = sum(1 for result in results if result.status == "fail")
    timed_out = sum(1 for result in results if result.status == "timeout")
    print("")
    print(
        f"Total: {len(results)} | Passed: {passed} | Failed: {failed} | Timeouts: {timed_out}"
    )


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    default_examples_dir = script_dir.parent / "examples"
    parser = argparse.ArgumentParser(description="Verify all Classical B machines under examples/.")
    parser.add_argument(
        "--examples-dir",
        default=str(default_examples_dir),
        help=f"Directory to scan for .mch files (default: {default_examples_dir}).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"Timeout in seconds for each probcli command (default: {DEFAULT_TIMEOUT_SECONDS}).",
    )
    parser.add_argument(
        "--probcli",
        default=DEFAULT_PROBCLI,
        help=f"ProB CLI executable or path to use (default: {DEFAULT_PROBCLI}).",
    )
    parser.add_argument(
        "--state-limit",
        type=int,
        default=DEFAULT_MODEL_CHECK_STATE_LIMIT,
        help=(
            "State limit for the bounded ProB -mc run "
            f"(default: {DEFAULT_MODEL_CHECK_STATE_LIMIT})."
        ),
    )
    return parser.parse_args()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    args = parse_args()
    examples_dir = Path(args.examples_dir).resolve()
    mch_files = list(iter_mch_files(examples_dir))

    if not mch_files:
        print(f"No .mch files found under {examples_dir}")
        return 1

    results = [
        verify_single(
            mch_path,
            timeout=args.timeout,
            probcli=args.probcli,
            state_limit=args.state_limit,
        )
        for mch_path in mch_files
    ]
    print_summary(results)
    return 0 if all(result.status == "pass" for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
