"""Regression tests for the DSL parsing and B generation pipeline."""

import difflib
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
from hypothesis import given, note, settings, strategies as st
from lark import Lark


REPO_ROOT = Path(__file__).resolve().parents[1]
DSL_DIR = REPO_ROOT / "dsl"
sys.path.insert(0, str(DSL_DIR))

from dsl_grammar import grammar  # noqa: E402
from dsl_transpiler import EventBGenerator  # noqa: E402
from dsl_typecheck import DSLTypeChecker  # noqa: E402


BOOL_EXAMPLE_NAMES = {"multisig.dsl", "nft_sketch.dsl"}
STRUCT_EXAMPLE_NAMES = {"loan_book.dsl"}
ENUM_EXAMPLE_NAMES = {"escrow.dsl"}
CONTEXT_EXAMPLE_NAMES = {"context_access_control.dsl"}
UNSUPPORTED_TRANSPILER_EXAMPLE_NAMES = set()


def _transpile(source, defensive=False):
    parser = Lark(grammar, parser="lalr")
    tree = parser.parse(source)
    return EventBGenerator(defensive=defensive).transform(tree)


def test_snapshot_my_token():
    """Transpile the canonical token DSL file and compare it to the stored B snapshot."""
    source_path = DSL_DIR / "my_token.dsl"
    expected_path = DSL_DIR / "MyToken_Machine.mch"

    actual = _transpile(source_path.read_text(encoding="utf-8"))
    expected = expected_path.read_text(encoding="utf-8")

    if actual != expected:
        diff = "\n".join(
            difflib.unified_diff(
                expected.splitlines(),
                actual.splitlines(),
                fromfile=str(expected_path),
                tofile="generated",
                lineterm="",
            )
        )
        pytest.fail(f"Generated MyToken machine differs from snapshot:\n{diff}")


@pytest.mark.parametrize(
    "dsl_path",
    sorted((REPO_ROOT / "examples").glob("*.dsl")),
    ids=lambda path: path.name,
)
def test_examples_transpile(dsl_path):
    """Every checked-in DSL example should parse and transpile into a B machine."""
    if dsl_path.name in UNSUPPORTED_TRANSPILER_EXAMPLE_NAMES:
        pytest.skip("awaiting Event-B transpiler")
    output = _transpile(dsl_path.read_text(encoding="utf-8"))
    assert "MACHINE" in output
    assert output.rstrip().endswith("END")


def test_main_cli_custom_input_output():
    """Run the public CLI with explicit input/output paths."""
    tmp_dir = REPO_ROOT / ".tmp_tests" / f"cli_{uuid.uuid4().hex}"
    tmp_dir.mkdir(parents=True)
    try:
        source_path = tmp_dir / "sample.dsl"
        output_path = tmp_dir / "sample.mch"
        source_path.write_text(
            """contract "Sample" {
    state:
        counter: int

    event set(value: int) {
        where value >= 0
        do:
            counter := value
    }
}
""",
            encoding="utf-8",
        )

        result = subprocess.run(
            [sys.executable, str(DSL_DIR / "main.py"), str(source_path), str(output_path)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0, result.stderr
        output = output_path.read_text(encoding="utf-8")
        assert "MACHINE Sample" in output
        assert output.rstrip().endswith("END")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_main_cli_defensive_flag_moves_contract_guards_into_body():
    """The public CLI should expose defensive-style generation."""
    tmp_dir = REPO_ROOT / ".tmp_tests" / f"cli_defensive_{uuid.uuid4().hex}"
    tmp_dir.mkdir(parents=True)
    try:
        source_path = tmp_dir / "sample.dsl"
        output_path = tmp_dir / "sample_defensive.mch"
        source_path.write_text(
            """contract "Sample" {
    state:
        balance: int

    event deposit(amount: int) {
        where amount > 0
        do:
            balance := balance + amount
    }
}
""",
            encoding="utf-8",
        )

        result = subprocess.run(
            [
                sys.executable,
                str(DSL_DIR / "main.py"),
                "--defensive",
                str(source_path),
                str(output_path),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0, result.stderr
        output = output_path.read_text(encoding="utf-8")
        assert "amount > 0" not in output.split("THEN", maxsplit=1)[0]
        assert "IF amount > 0" in output
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_main_cli_defaults_to_my_token_output():
    """Running the CLI without arguments should preserve the original default behavior."""
    output_path = DSL_DIR / "MyToken_Machine.mch"
    expected = output_path.read_text(encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(DSL_DIR / "main.py")],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert output_path.read_text(encoding="utf-8") == expected


def test_regenerate_corpus_helper_builds_defensive_snapshot_in_custom_output_dir():
    """The corpus helper should regenerate defensive machines into a chosen directory."""
    tmp_dir = REPO_ROOT / ".tmp_tests" / f"regen_{uuid.uuid4().hex}"
    tmp_dir.mkdir(parents=True)
    try:
        examples_dir = tmp_dir / "examples"
        output_dir = tmp_dir / "out"
        examples_dir.mkdir()
        source_path = examples_dir / "sample.dsl"
        source_path.write_text(
            """contract "Sample" {
    state:
        counter: int

    event set(value: int) {
        where value >= 0
        do:
            counter := value
    }
}
""",
            encoding="utf-8",
        )

        result = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "scripts" / "regenerate_corpus.py"),
                "--examples-dir",
                str(examples_dir),
                "--output-dir",
                str(output_dir),
                "--defensive",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0, result.stderr
        output = (output_dir / "sample.mch").read_text(encoding="utf-8")
        assert "IF value >= 0" in output
        assert "Regenerated 1 defensive-style machine(s)" in result.stdout
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_task4_nested_maps_multi_quantifier_and_conditional_render_cleanly():
    """Task 4 features should transpile to the expected B constructs."""
    source = """contract "Task4Demo" {
    state:
        allowances: map(address -> map(address -> nat))
        fee: nat

    invariants:
        forall owner, spender . allowances[owner][spender] >= 0;
        fee >= 0

    event approve(owner: address, spender: address, amount: nat) {
        do:
            allowances[owner][spender] := amount
    }

    event charge(owner: address, spender: address, amount: nat) {
        where allowances[owner][spender] >= amount
        do:
            if amount > 10 then
                fee := amount - 10
            else
                fee := 0
            end,
            allowances[owner][spender] := allowances[owner][spender] - amount
    }
}
"""

    output = _transpile(source)

    assert "allowances : ADDRESS +-> (ADDRESS +-> NATURAL)" in output
    assert "!owner.(owner : dom(allowances) => (!spender." in output
    assert "IF amount > 10 THEN" in output
    assert "allowances := allowances <+ {owner |->" in output


def test_task4_numeric_operators_render_to_b_machine():
    """Task 4 numeric operators should be emitted in B expressions."""
    source = """contract "ArithmeticDemo" {
    state:
        fee: nat

    event charge(amount: nat, rate: nat, divisor: nat) {
        where divisor > 0
        do:
            fee := amount * rate / divisor % 7
    }
}
"""

    output = _transpile(source)

    assert "fee := amount * rate / divisor mod 7" in output


def test_task3_enum_example_renders_enumerated_b_set():
    """Task 3 enum declarations should reach B instead of being skipped."""
    dsl_path = REPO_ROOT / "examples" / "escrow.dsl"
    output = _transpile(dsl_path.read_text(encoding="utf-8"))

    assert "Status = {Pending, Funded, Released, Refunded}" in output
    assert "status : Status" in output
    assert "status := Pending" in output
    assert "status = Funded" in output


def test_task5_context_example_renders_implicit_operation_parameters():
    """Task 5 context identifiers should become typed B operation parameters."""
    dsl_path = REPO_ROOT / "examples" / "context_access_control.dsl"
    output = _transpile(dsl_path.read_text(encoding="utf-8"))

    assert "pause(msg_sender, block_timestamp) =" in output
    assert "msg_sender : ADDRESS" in output
    assert "block_timestamp : NATURAL" in output
    assert "last_update := block_timestamp" in output


def test_task2_struct_example_renders_b_records():
    """Task 2 structs should reach B as record types and record values."""
    dsl_path = REPO_ROOT / "examples" / "loan_book.dsl"
    output = _transpile(dsl_path.read_text(encoding="utf-8"))

    assert "loans : NATURAL +-> struct(borrower: ADDRESS, amount: NATURAL, deadline: NATURAL)" in output
    assert "loans := loans <+ {loan_id |-> rec(borrower: borrower, amount: amount, deadline: deadline)}" in output
    assert "loans(loan_id)'amount > 0" in output


def test_defensive_style_keeps_typing_in_pre_and_moves_contract_guards_into_if():
    """Defensive mode should keep parameter typing in PRE but guard the body with IF."""
    source = """contract "DefensiveDemo" {
    state:
        balances: map(address -> int)

    event transfer(sender: address, receiver: address, amount: int) {
        where balances[sender] >= amount
        where amount > 0
        do:
            balances[sender] := balances[sender] - amount,
            balances[receiver] := balances[receiver] + amount
    }
}
"""

    output = _transpile(source, defensive=True)

    assert "sender : ADDRESS" in output
    assert "receiver : ADDRESS" in output
    assert "amount : INTEGER" in output
    assert "balances(sender) >= amount" not in output.split("THEN", maxsplit=1)[0]
    assert "IF sender : dom(balances) &" in output
    assert "balances(sender) >= amount &" in output
    assert "amount > 0" in output


def test_offensive_style_keeps_contract_guards_in_pre_clause():
    """The default rendering should remain offensive style for compatibility."""
    source = """contract "OffensiveDemo" {
    state:
        counter: int

    event set(value: int) {
        where value >= 0
        do:
            counter := value
    }
}
"""

    output = _transpile(source)

    assert "PRE" in output
    assert "value >= 0" in output.split("THEN", maxsplit=1)[0]
    assert "IF value >= 0" not in output


def test_address_distinctness_invariants_shape_any_initialisation():
    """Address inequality invariants should constrain generated ANY binders."""
    source = """contract "EscrowInit" {
    state:
        buyer: address
        seller: address

    invariants:
        buyer != seller
}
"""

    output = _transpile(source, defensive=True)

    assert "ANY buyer_init, seller_init WHERE" in output
    assert "buyer_init : ADDRESS & seller_init : ADDRESS &" in output
    assert "buyer_init /= seller_init" in output

RESERVED_WORDS = {
    "contract",
    "state",
    "invariants",
    "event",
    "where",
    "do",
    "forall",
    "if",
    "then",
    "else",
    "end",
    "map",
    "address",
    "int",
    "nat",
    "struct",
    "enum",
    "bool",
    "true",
    "false",
    "not",
    "and",
    "or",
    "xor",
    "msg_sender",
    "msg_value",
    "block_number",
    "block_timestamp",
}


identifier = st.from_regex(r"[a-z][a-z_]{2,8}", fullmatch=True).filter(
    lambda name: name not in RESERVED_WORDS
    and not any(name.startswith(word) for word in RESERVED_WORDS)
    and not any(name.startswith(f"{word}_") for word in RESERVED_WORDS)
)
contract_name = st.from_regex(r"[A-Z][a-z]{3,10}", fullmatch=True)
dsl_type = st.sampled_from(["int", "nat", "address", "map(address -> int)", "map(int -> int)"])
arithmetic_operator = st.sampled_from(["+", "-", "*", "/", "%"])


def _is_map_type(type_name):
    return type_name.startswith("map(")


def _map_domain_type(type_name):
    return type_name.removeprefix("map(").removesuffix(")").split(" -> ", maxsplit=1)[0]


def _unique_helper_name(base, unavailable):
    candidate = base
    index = 1
    while candidate in unavailable:
        candidate = f"{base}_{index}"
        index += 1
    return candidate


@st.composite
def valid_programs(draw):
    state_names = draw(st.lists(identifier, min_size=1, max_size=3, unique=True))
    state_types = draw(
        st.lists(dsl_type, min_size=len(state_names), max_size=len(state_names))
    )
    states = list(zip(state_names, state_types))

    event_names = draw(st.lists(identifier, min_size=1, max_size=2, unique=True))
    events = []
    for event_name in event_names:
        action_var, action_type = draw(st.sampled_from(states))
        generated_params = []
        action_expr = "0"
        action_lvalue = action_var
        unavailable_names = set(state_names)
        if action_type == "address":
            address_param_name = _unique_helper_name("actor", unavailable_names)
            generated_params.append((address_param_name, "address"))
            unavailable_names.add(address_param_name)
            action_expr = address_param_name
        elif _is_map_type(action_type):
            key_param_name = _unique_helper_name("key", unavailable_names)
            generated_params.append((key_param_name, _map_domain_type(action_type)))
            unavailable_names.add(key_param_name)
            action_lvalue = f"{action_var}[{key_param_name}]"

        extra_param_names = draw(
            st.lists(
                identifier.filter(lambda name: name not in unavailable_names),
                min_size=0,
                max_size=2,
                unique=True,
            )
        )
        extra_param_types = draw(
            st.lists(
                dsl_type,
                min_size=len(extra_param_names),
                max_size=len(extra_param_names),
            )
        )
        params = generated_params + list(zip(extra_param_names, extra_param_types))
        numeric_state_names = [
            name for name, type_name in states if type_name in {"int", "nat"}
        ]
        guard_var = (
            draw(st.none() | st.sampled_from(numeric_state_names))
            if numeric_state_names
            else None
        )
        events.append((event_name, params, guard_var, action_lvalue, action_expr))

    lines = [f'contract "{draw(contract_name)}" {{', "    state:"]
    for name, type_name in states:
        lines.append(f"        {name}: {type_name}")

    for event_name, params, guard_var, action_var, action_expr in events:
        rendered_params = ", ".join(
            f"{name}: {type_name}" for name, type_name in params
        )
        lines.append("")
        lines.append(f"    event {event_name}({rendered_params}) {{")
        if guard_var is not None:
            lines.append(f"        where {guard_var} >= 0")
        lines.append("        do:")
        lines.append(f"            {action_var} := {action_expr}")
        lines.append("    }")

    lines.append("}")
    return "\n".join(lines)


@st.composite
def valid_numeric_operator_programs(draw):
    contract = draw(contract_name)
    target = draw(identifier)
    left = draw(identifier.filter(lambda name: name != target))
    right = draw(identifier.filter(lambda name: name not in {target, left}))
    first_op = draw(arithmetic_operator)
    second_op = draw(st.none() | arithmetic_operator)

    expr = f"{left} {first_op} {right}"
    if second_op is not None:
        expr = f"{expr} {second_op} {right}"

    return f"""contract "{contract}" {{
    state:
        {target}: nat

    event calculate({left}: nat, {right}: nat) {{
        do:
            {target} := {expr}
    }}
}}
"""


@given(valid_programs())
@settings(max_examples=50, deadline=10000)
def test_fuzz_valid_programs(source):
    """Generate small valid DSL programs and ensure the real pipeline keeps a B skeleton."""
    note(source)
    try:
        output = _transpile(source)
    except Exception as exc:
        pytest.fail(f"Generated DSL source raised {exc!r}:\n{source}")

    assert "MACHINE" in output, source
    assert "END" in output, source


@given(valid_numeric_operator_programs())
@settings(max_examples=50, deadline=10000)
def test_fuzz_task4_numeric_operators_parse_and_typecheck(source):
    """Task 4 arithmetic fuzzing should stay at parser/type-checker level."""
    note(source)
    tree = Lark(grammar, parser="lalr", propagate_positions=True).parse(source)
    DSLTypeChecker().check(tree)


def test_task4_examples_include_standalone_conditional_demo():
    """Task 4 should include a small contract dedicated to conditionals."""
    dsl_path = REPO_ROOT / "examples" / "conditional_fee.dsl"
    output = _transpile(dsl_path.read_text(encoding="utf-8"))

    assert "MACHINE ConditionalFee" in output
    assert "IF amount > 10 THEN" in output


def test_erc20_full_self_transfer_keeps_balance_conserved():
    """The richer ERC20 example should preserve supply on self-transfer."""
    dsl_path = REPO_ROOT / "examples" / "erc20_full.dsl"
    output = _transpile(dsl_path.read_text(encoding="utf-8"))

    assert "total_supply = SIGMA" in output
    assert "IF owner = receiver THEN" in output
    assert "balances := balances <+ {owner |->" in output


@pytest.mark.parametrize(
    ("dsl_name", "mch_name"),
    [
        ("arithmetic_ops.dsl", "arithmetic_ops.mch"),
        ("conditional_fee.dsl", "conditional_fee.mch"),
        ("erc20_full.dsl", "erc20_full.mch"),
    ],
)
def test_task4_example_snapshots_match_generated_output(dsl_name, mch_name):
    """Task 4 example machines should stay in sync with the transpiler."""
    dsl_path = REPO_ROOT / "examples" / dsl_name
    mch_path = REPO_ROOT / "examples" / mch_name

    actual = _transpile(dsl_path.read_text(encoding="utf-8"))
    expected = mch_path.read_text(encoding="utf-8")

    if actual != expected:
        diff = "\n".join(
            difflib.unified_diff(
                expected.splitlines(),
                actual.splitlines(),
                fromfile=str(mch_path),
                tofile="generated",
                lineterm="",
            )
        )
        pytest.fail(f"Generated Task 4 machine differs from snapshot:\n{diff}")


@pytest.mark.parametrize(
    ("dsl_name", "mch_name"),
    [
        ("escrow.dsl", "escrow.mch"),
        ("context_access_control.dsl", "context_access_control.mch"),
    ],
)
def test_task3_task5_example_snapshots_match_generated_output(dsl_name, mch_name):
    """Task 3 and 5 examples should stay in sync with the transpiler."""
    dsl_path = REPO_ROOT / "examples" / dsl_name
    mch_path = REPO_ROOT / "examples" / mch_name

    actual = _transpile(dsl_path.read_text(encoding="utf-8"))
    expected = mch_path.read_text(encoding="utf-8")

    if actual != expected:
        diff = "\n".join(
            difflib.unified_diff(
                expected.splitlines(),
                actual.splitlines(),
                fromfile=str(mch_path),
                tofile="generated",
                lineterm="",
            )
        )
        pytest.fail(f"Generated Task 3/5 machine differs from snapshot:\n{diff}")


@pytest.mark.parametrize(
    ("dsl_name", "mch_name"),
    [
        ("access_control.dsl", "access_control.mch"),
        ("arithmetic_ops.dsl", "arithmetic_ops.mch"),
        ("auction.dsl", "auction.mch"),
        ("conditional_fee.dsl", "conditional_fee.mch"),
        ("context_access_control.dsl", "context_access_control.mch"),
        ("erc20_full.dsl", "erc20_full.mch"),
        ("escrow.dsl", "escrow.mch"),
        ("loan_book.dsl", "loan_book.mch"),
        ("multisig.dsl", "multisig.mch"),
        ("nft_sketch.dsl", "nft_sketch.mch"),
        ("token_state.dsl", "token_state.mch"),
        ("voting.dsl", "voting.mch"),
    ],
)
def test_task6_defensive_example_snapshots_match_generated_output(dsl_name, mch_name):
    """Task 6 defensive corpus snapshots should stay in sync with the transpiler."""
    dsl_path = REPO_ROOT / "examples" / dsl_name
    mch_path = REPO_ROOT / "examples" / "defensive" / mch_name

    actual = _transpile(dsl_path.read_text(encoding="utf-8"), defensive=True)
    expected = mch_path.read_text(encoding="utf-8")

    if actual != expected:
        diff = "\n".join(
            difflib.unified_diff(
                expected.splitlines(),
                actual.splitlines(),
                fromfile=str(mch_path),
                tofile="generated",
                lineterm="",
            )
        )
        pytest.fail(f"Generated Task 6 defensive machine differs from snapshot:\n{diff}")
