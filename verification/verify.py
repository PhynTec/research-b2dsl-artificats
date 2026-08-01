import argparse
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


def _default_probcli() -> str:
    env_value = os.environ.get("PROBCLI")
    if env_value:
        return env_value

    discovered = shutil.which("probcli")
    if discovered:
        return discovered

    windows_fallback = Path(r"C:\ProB\probcli.exe")
    if os.name == "nt" and windows_fallback.exists():
        return str(windows_fallback)

    return "probcli"


DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_PROBCLI = _default_probcli()
DEFAULT_MODEL_CHECK_STATE_LIMIT = 5000
DEFAULT_ADDRESS_CARDINALITY = 10
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


@dataclass
class CommandResult:
    name: str
    command: List[str]
    elapsed_seconds: float
    returncode: Optional[int]
    output: str
    passed: bool
    timed_out: bool
    error_message: Optional[str]


@dataclass
class VerificationResult:
    mch_path: Path
    status: str
    exit_code: int
    elapsed_seconds: float
    command_results: List[CommandResult]
    error_description: Optional[str]
    counterexample_path: Optional[Path]


def _combine_output(stdout: Optional[str], stderr: Optional[str]) -> str:
    parts = []
    if stdout:
        parts.append(stdout.strip())
    if stderr:
        parts.append(stderr.strip())
    return "\n\n".join(part for part in parts if part).strip()


def _probcli_scope_args(mch_path: Path) -> List[str]:
    try:
        content = mch_path.read_text(encoding="utf-8")
    except OSError:
        return []

    if "ADDRESS" in content:
        return ["-card", "ADDRESS", str(DEFAULT_ADDRESS_CARDINALITY)]
    return []


def _output_indicates_failure(output: str) -> bool:
    lowered = output.lower()
    if "no deadlock found" in lowered:
        lowered = lowered.replace("no deadlock found", "")
    return any(pattern in lowered for pattern in FAILURE_PATTERNS)


def _output_is_deadlock_only(output: str) -> bool:
    lowered = output.lower()
    if "deadlock" not in lowered:
        return False

    disqualifying_markers = (
        "invariant violation",
        "assertion violation",
        "properties are false",
        "abnormal termination of probcli",
        "*** serious error occurred ***",
        "initialisation fails",
        "initialisation_fails",
    )
    return not any(marker in lowered for marker in disqualifying_markers)


def _extract_initial_animation_budget(output: str) -> Optional[int]:
    match = re.search(r"INITIALISATION\((?:[^)]*?)anim_steps_left\s*=\s*(\d+)", output)
    if match:
        return int(match.group(1))
    return None


def _extract_trace_length(output: str) -> Optional[int]:
    match = re.search(r"TRACE \(length=(\d+)\)", output)
    if match:
        return int(match.group(1))
    return None


def output_is_expected_budget_deadlock(output: str) -> bool:
    if not _output_is_deadlock_only(output):
        return False

    if re.search(r"anim_steps_left\s*=\s*0", output):
        return True

    initial_budget = _extract_initial_animation_budget(output)
    trace_length = _extract_trace_length(output)
    if initial_budget is None or trace_length is None:
        return False

    return trace_length == initial_budget + 1


def output_is_expected_terminal_deadlock(output: str) -> bool:
    if output_is_expected_budget_deadlock(output):
        return True
    return _output_is_deadlock_only(output) and "all operations covered" in output.lower()


def _write_counterexample(mch_path: Path, command_results: List[CommandResult]) -> Path:
    counterexample_path = mch_path.with_suffix(".counterexample.txt")
    lines = [f"Verification failure for {mch_path}", ""]
    for result in command_results:
        lines.append(f"Command: {' '.join(result.command)}")
        lines.append(f"Passed: {result.passed}")
        lines.append(f"Timed out: {result.timed_out}")
        lines.append(f"Return code: {result.returncode}")
        lines.append(f"Elapsed seconds: {result.elapsed_seconds:.3f}")
        if result.error_message:
            lines.append(f"Error: {result.error_message}")
        lines.append("Output:")
        lines.append(result.output or "<no output captured>")
        lines.append("")
    counterexample_path.write_text("\n".join(lines), encoding="utf-8")
    return counterexample_path


def run_prob_command(
    mch_path: Path,
    name: str,
    command_args: List[str],
    timeout: int,
    probcli: str,
) -> CommandResult:
    command = [
        probcli,
        str(mch_path),
        *_probcli_scope_args(mch_path),
        *command_args,
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
    except FileNotFoundError:
        elapsed = time.perf_counter() - start
        return CommandResult(
            name=name,
            command=command,
            elapsed_seconds=elapsed,
            returncode=None,
            output="",
            passed=False,
            timed_out=False,
            error_message=f"{probcli} not found while verifying {mch_path}",
        )
    except subprocess.TimeoutExpired as exc:
        elapsed = time.perf_counter() - start
        output = _combine_output(exc.stdout, exc.stderr)
        return CommandResult(
            name=name,
            command=command,
            elapsed_seconds=elapsed,
            returncode=None,
            output=output,
            passed=False,
            timed_out=True,
            error_message=(
                f"Verification timed out for {mch_path} after {timeout} seconds "
                f"while running {name}"
            ),
        )

    elapsed = time.perf_counter() - start
    output = _combine_output(completed.stdout, completed.stderr)
    passed = completed.returncode == 0 and not _output_indicates_failure(output)
    error_message = None if passed else f"Verification command {name} failed for {mch_path}"
    return CommandResult(
        name=name,
        command=command,
        elapsed_seconds=elapsed,
        returncode=completed.returncode,
        output=output,
        passed=passed,
        timed_out=False,
        error_message=error_message,
    )


def verify_single(
    mch_path: Path,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    probcli: str = DEFAULT_PROBCLI,
    state_limit: int = DEFAULT_MODEL_CHECK_STATE_LIMIT,
) -> VerificationResult:
    mch_path = Path(mch_path).resolve()
    command_results = [
        run_prob_command(mch_path, "-mc", ["-mc", str(state_limit)], timeout, probcli),
        run_prob_command(mch_path, "-cbc_deadlock", ["-cbc_deadlock"], timeout, probcli),
    ]
    elapsed_seconds = sum(result.elapsed_seconds for result in command_results)

    timed_out_result = next((result for result in command_results if result.timed_out), None)
    if timed_out_result is not None:
        counterexample_path = _write_counterexample(mch_path, command_results)
        return VerificationResult(
            mch_path=mch_path,
            status="timeout",
            exit_code=2,
            elapsed_seconds=elapsed_seconds,
            command_results=command_results,
            error_description=timed_out_result.error_message,
            counterexample_path=counterexample_path,
        )

    failed_results = [result for result in command_results if not result.passed]
    if failed_results and all(output_is_expected_terminal_deadlock(result.output) for result in failed_results):
        return VerificationResult(
            mch_path=mch_path,
            status="pass",
            exit_code=0,
            elapsed_seconds=elapsed_seconds,
            command_results=command_results,
            error_description=None,
            counterexample_path=None,
        )

    failed_result = next(iter(failed_results), None)
    if failed_result is not None:
        counterexample_path = _write_counterexample(mch_path, command_results)
        description = failed_result.error_message or f"Verification failed for {mch_path}"
        return VerificationResult(
            mch_path=mch_path,
            status="fail",
            exit_code=1,
            elapsed_seconds=elapsed_seconds,
            command_results=command_results,
            error_description=description,
            counterexample_path=counterexample_path,
        )

    return VerificationResult(
        mch_path=mch_path,
        status="pass",
        exit_code=0,
        elapsed_seconds=elapsed_seconds,
        command_results=command_results,
        error_description=None,
        counterexample_path=None,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify a single Classical B machine with ProB.")
    parser.add_argument("mch_path", help="Path to the .mch file to verify.")
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
    args = parse_args()
    result = verify_single(
        Path(args.mch_path),
        timeout=args.timeout,
        probcli=args.probcli,
        state_limit=args.state_limit,
    )

    if result.status == "pass":
        print(f"PASS {result.mch_path} ({result.elapsed_seconds:.3f}s)")
    elif result.status == "timeout":
        print(f"TIMEOUT {result.mch_path}: {result.error_description}")
        if result.counterexample_path is not None:
            print(f"Counterexample saved to {result.counterexample_path}")
    else:
        print(f"FAIL {result.mch_path}: {result.error_description}")
        if result.counterexample_path is not None:
            print(f"Counterexample saved to {result.counterexample_path}")

    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
