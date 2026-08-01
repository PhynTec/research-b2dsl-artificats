"""Tests for the Task 3 ProB verification helpers."""

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[1]
VERIFICATION_DIR = REPO_ROOT / "verification"
sys.path.insert(0, str(VERIFICATION_DIR))

import bench  # noqa: E402
import verify  # noqa: E402
import verify_all  # noqa: E402


def test_verify_single_fails_on_non_deadlock_verification_error(monkeypatch):
    """Invariant-style verification errors should still fail the verifier."""

    calls = []

    def fake_run(command, capture_output, text, timeout, check):
        calls.append(command)
        if "-mc" in command:
            return SimpleNamespace(
                returncode=0,
                stdout="*** COUNTER EXAMPLE FOUND ***\nInvariant violation on balance >= 0",
                stderr="",
            )
        return SimpleNamespace(
            returncode=0,
            stdout="No DEADLOCK state found",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = verify.verify_single(Path("examples/token_state.mch"), timeout=5, probcli="probcli")

    assert calls[0][-5:] == [
        "-card",
        "ADDRESS",
        str(verify.DEFAULT_ADDRESS_CARDINALITY),
        "-mc",
        str(verify.DEFAULT_MODEL_CHECK_STATE_LIMIT),
    ]
    assert calls[1][-1] == "-cbc_deadlock"
    assert result.status == "fail"
    assert result.counterexample_path is not None

    result.counterexample_path.unlink()


def test_run_benchmark_marks_counterexample_output_as_failed(monkeypatch):
    """Benchmarks should not mark a counterexample-producing run as passed."""

    def fake_run(command, capture_output, text, timeout, check):
        return SimpleNamespace(
            returncode=0,
            stdout="States analysed: 88\n*** COUNTER EXAMPLE FOUND ***",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    row = bench.run_benchmark(Path("examples/token_state.mch"), 100, timeout=5, probcli="probcli")

    assert row["passed"] is False
    assert row["states_explored"] == 88


def test_run_benchmark_does_not_treat_no_counterexample_message_as_failure(monkeypatch):
    """A successful bounded run with a 'No counter example found' message should pass."""

    def fake_run(command, capture_output, text, timeout, check):
        return SimpleNamespace(
            returncode=0,
            stdout="States analysed: 100\nNo counter example Found, not all states visited",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    row = bench.run_benchmark(Path("examples/access_control.mch"), 100, timeout=5, probcli="probcli")

    assert row["passed"] is True
    assert row["states_explored"] == 100


def test_run_benchmark_accepts_expected_animation_budget_deadlock(monkeypatch):
    """Benchmarks should treat the intentional budget-stop deadlock as a pass."""

    def fake_run(command, capture_output, text, timeout, check):
        return SimpleNamespace(
            returncode=0,
            stdout=(
                "ALL OPERATIONS COVERED\n"
                "States analysed: 304\n"
                "*** COUNTER EXAMPLE FOUND ***\n\n"
                "deadlock\n"
                "*** TRACE (length=13):\n"
                " 1: INITIALISATION(anim_steps_left=12,balance=0)\n"
                " 2 - 13: deposit(0)   (12 repetitions)\n"
            ),
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    row = bench.run_benchmark(Path("examples/escrow.mch"), 5000, timeout=5, probcli="probcli")

    assert row["passed"] is True
    assert row["states_explored"] == 304


def test_run_benchmark_accepts_terminal_deadlock_after_operation_coverage(monkeypatch):
    """Benchmarks should accept terminal deadlocks after full workflow coverage."""

    def fake_run(command, capture_output, text, timeout, check):
        return SimpleNamespace(
            returncode=0,
            stdout=(
                "ALL OPERATIONS COVERED\n"
                "States analysed: 19\n"
                "*** COUNTER EXAMPLE FOUND ***\n"
                "deadlock\n"
                "*** TRACE (length=4):\n"
                " 1: INITIALISATION(balance=0,status=0)\n"
                " 2: deposit(4)\n"
                " 3: refund\n"
            ),
            stderr="! *** error occurred ***\n! deadlock",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    row = bench.run_benchmark(Path("examples/escrow.mch"), 100, timeout=5, probcli="probcli")

    assert row["passed"] is True
    assert row["states_explored"] == 19


def test_run_benchmark_fails_on_unexpected_deadlock(monkeypatch):
    """Benchmarks should still fail for deadlocks unrelated to expected endings."""

    def fake_run(command, capture_output, text, timeout, check):
        return SimpleNamespace(
            returncode=0,
            stdout=(
                "States analysed: 17\n"
                "*** COUNTER EXAMPLE FOUND ***\n"
                "*** DEADLOCK state found ***\n"
                "*** STATE = \n"
                "     ( balance=0 & status=1 )\n"
                "*** END DEADLOCKING STATE\n"
            ),
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    row = bench.run_benchmark(Path("examples/escrow.mch"), 100, timeout=5, probcli="probcli")

    assert row["passed"] is False
    assert row["states_explored"] == 17


def test_verify_single_marks_timeout_and_saves_counterexample(monkeypatch):
    """A timed out ProB invocation should return timeout and save diagnostics."""

    calls = {"count": 0}

    def fake_run(command, capture_output, text, timeout, check):
        calls["count"] += 1
        if calls["count"] == 1:
            raise subprocess.TimeoutExpired(
                cmd=command,
                timeout=timeout,
                output="Visited states: 41",
                stderr="timeout reached",
            )
        return SimpleNamespace(
            returncode=0,
            stdout="No deadlock found.",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = verify.verify_single(Path("examples/token_state.mch"), timeout=5, probcli="probcli")

    assert result.status == "timeout"
    assert result.counterexample_path is not None
    assert result.counterexample_path.exists()
    assert "timed out" in result.counterexample_path.read_text(encoding="utf-8").lower()

    result.counterexample_path.unlink()


def test_verify_single_accepts_expected_animation_budget_deadlock(monkeypatch):
    """Budget exhaustion should not fail verification when it is the only deadlock."""

    calls = []

    def fake_run(command, capture_output, text, timeout, check):
        calls.append(command)
        if "-mc" in command:
            return SimpleNamespace(
                returncode=0,
                stdout=(
                    "ALL OPERATIONS COVERED\n"
                    "*** COUNTER EXAMPLE FOUND ***\n\n"
                    "deadlock\n"
                    "*** TRACE (length=13):\n"
                    " 1: INITIALISATION(anim_steps_left=12,balance=0)\n"
                    " 2 - 13: deposit(0)   (12 repetitions)\n"
                ),
                stderr="! *** error occurred ***\n! deadlock",
            )
        return SimpleNamespace(
            returncode=0,
            stdout=(
                "% Starting Constraint-Based DEADLOCK check\n"
                "*** DEADLOCK state found ***\n"
                "*** STATE = \n"
                "     ( anim_steps_left=0 &\n"
                "       balance=0 )\n"
                "*** END DEADLOCKING STATE\n"
            ),
            stderr="! *** error occurred ***\n! cbc_deadlock_check",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = verify.verify_single(Path("examples/escrow.mch"), timeout=5, probcli="probcli")

    assert calls[0][-5:] == [
        "-card",
        "ADDRESS",
        str(verify.DEFAULT_ADDRESS_CARDINALITY),
        "-mc",
        str(verify.DEFAULT_MODEL_CHECK_STATE_LIMIT),
    ]
    assert calls[1][-1] == "-cbc_deadlock"
    assert result.status == "pass"
    assert result.counterexample_path is None


def test_verify_single_accepts_terminal_deadlock_after_operation_coverage(monkeypatch):
    """Covered finite workflows may end in a terminal deadlock without failing verification."""

    def fake_run(command, capture_output, text, timeout, check):
        if "-mc" in command:
            return SimpleNamespace(
                returncode=0,
                stdout=(
                    "ALL OPERATIONS COVERED\n"
                    "*** COUNTER EXAMPLE FOUND ***\n"
                    "deadlock\n"
                    "*** TRACE (length=4):\n"
                    " 1: INITIALISATION(balance=0,status=0)\n"
                    " 2: deposit(4)\n"
                    " 3: refund\n"
                ),
                stderr="! *** error occurred ***\n! deadlock",
            )
        return SimpleNamespace(
            returncode=0,
            stdout="No deadlock found.",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = verify.verify_single(Path("examples/escrow.mch"), timeout=5, probcli="probcli")

    assert result.status == "pass"
    assert result.counterexample_path is None


def test_verify_single_fails_on_unexpected_deadlock(monkeypatch):
    """Generic deadlocks should fail verification instead of being auto-accepted."""

    def fake_run(command, capture_output, text, timeout, check):
        if "-mc" in command:
            return SimpleNamespace(
                returncode=0,
                stdout="No counter example found",
                stderr="",
            )
        return SimpleNamespace(
            returncode=0,
            stdout=(
                "% Starting Constraint-Based DEADLOCK check\n"
                "*** DEADLOCK state found ***\n"
                "*** STATE = \n"
                "     ( balance=0 & status=1 )\n"
                "*** END DEADLOCKING STATE\n"
            ),
            stderr="! *** error occurred ***\n! cbc_deadlock_check",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = verify.verify_single(Path("examples/escrow.mch"), timeout=5, probcli="probcli")

    assert result.status == "fail"
    assert result.counterexample_path is not None

    result.counterexample_path.unlink()


def test_verify_single_skips_address_scope_for_machine_without_address(monkeypatch):
    """Machines without ADDRESS should not receive an invalid -card ADDRESS scope."""

    calls = []

    def fake_run(command, capture_output, text, timeout, check):
        calls.append(command)
        return SimpleNamespace(
            returncode=0,
            stdout="No deadlock found.",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = verify.verify_single(Path("examples/auction.mch"), timeout=5, probcli="probcli")

    assert result.status == "pass"
    assert "-card" not in calls[0]


def test_verify_all_prints_summary_for_discovered_machines(monkeypatch, capsys):
    """The corpus verifier should summarize pass/fail totals for all .mch files."""

    scratch_dir = REPO_ROOT / ".tmp_tests" / "pytest_verify_all"
    scratch_dir.mkdir(parents=True, exist_ok=True)
    examples_dir = scratch_dir / "examples"
    examples_dir.mkdir(exist_ok=True)
    (examples_dir / "alpha.mch").write_text("MACHINE Alpha\nEND\n", encoding="utf-8")
    (examples_dir / "beta.mch").write_text("MACHINE Beta\nEND\n", encoding="utf-8")

    def fake_verify_single(mch_path, timeout, probcli, state_limit):
        return verify.VerificationResult(
            mch_path=Path(mch_path),
            status="pass",
            exit_code=0,
            elapsed_seconds=1.25,
            command_results=[],
            error_description=None,
            counterexample_path=None,
        )

    monkeypatch.setattr(verify_all, "verify_single", fake_verify_single)
    monkeypatch.setattr(
        sys,
        "argv",
        ["verify_all.py", "--examples-dir", str(examples_dir), "--probcli", "probcli"],
    )

    exit_code = verify_all.main()
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "alpha.mch" in output
    assert "beta.mch" in output
    assert "Passed: 2" in output
    assert "Failed: 0" in output
    assert "Timeouts: 0" in output


def test_write_csv_uses_expected_columns():
    """Benchmark output should preserve the CSV schema promised by Task 3."""

    output_dir = REPO_ROOT / ".tmp_tests" / "pytest_bench"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "benchmarks.csv"
    bench.write_csv(
        [
            {
                "contract": "token_state",
                "state_limit": 100,
                "time_seconds": "1.234567",
                "passed": True,
                "states_explored": 100,
            }
        ],
        output_path,
    )

    content = output_path.read_text(encoding="utf-8").splitlines()
    assert content[0] == "contract,state_limit,time_seconds,passed,states_explored"
    assert content[1] == "token_state,100,1.234567,True,100"


def test_bench_main_fails_when_any_benchmark_row_fails(monkeypatch):
    """The benchmark CLI should exit non-zero if ProB did not pass every run."""

    scratch_dir = REPO_ROOT / ".tmp_tests" / "pytest_bench_main"
    scratch_dir.mkdir(parents=True, exist_ok=True)
    examples_dir = scratch_dir / "examples"
    examples_dir.mkdir(exist_ok=True)
    machine_path = examples_dir / "alpha.mch"
    machine_path.write_text("MACHINE Alpha\nEND\n", encoding="utf-8")
    output_path = scratch_dir / "benchmarks.csv"

    monkeypatch.setattr(bench, "iter_mch_files", lambda _: [machine_path])
    monkeypatch.setattr(
        bench,
        "run_benchmark",
        lambda mch_path, state_limit, timeout, probcli: {
            "contract": mch_path.stem,
            "state_limit": state_limit,
            "time_seconds": "0.100000",
            "passed": False,
            "states_explored": "",
        },
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "bench.py",
            "--examples-dir",
            str(examples_dir),
            "--output",
            str(output_path),
            "--timeout",
            "5",
        ],
    )

    exit_code = bench.main()

    assert exit_code == 1
    assert output_path.exists()
