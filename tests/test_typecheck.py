"""Tests for the Task 5 static type checker."""

import subprocess
import sys
import uuid
from pathlib import Path

import pytest
from lark import Lark


REPO_ROOT = Path(__file__).resolve().parents[1]
DSL_DIR = REPO_ROOT / "dsl"
sys.path.insert(0, str(DSL_DIR))

from dsl_grammar import grammar  # noqa: E402
from dsl_typecheck import DSLTypeChecker, DSLTypeError  # noqa: E402


def _parse_program(source: str):
    return Lark(grammar, parser="lalr", propagate_positions=True).parse(source)


def _check_program(source: str) -> None:
    tree = _parse_program(source)
    DSLTypeChecker().check(tree)


def _assert_type_error(source: str, expected_text: str) -> str:
    with pytest.raises(DSLTypeError) as excinfo:
        _check_program(source)
    message = str(excinfo.value)
    assert expected_text in message
    assert "line" in message
    assert "column" in message
    return message


def _find_tree(node, data: str):
    if getattr(node, "data", None) == data:
        return node
    for child in getattr(node, "children", []):
        found = _find_tree(child, data)
        if found is not None:
            return found
    return None


def test_rejects_undeclared_identifier():
    message = _assert_type_error(
        """contract "Bad" {
    state:
        balance: int

    event set(amount: int) {
        do:
            balance := missing
    }
}
""",
        "Undeclared identifier 'missing'",
    )

    assert "line 7" in message


def test_rejects_assignment_with_wrong_scalar_type():
    _assert_type_error(
        """contract "Bad" {
    state:
        owner: address

    event set(amount: int) {
        do:
            owner := amount
    }
}
""",
        "Cannot assign value of type int to address",
    )


def test_event_parameter_type_mismatch():
    _assert_type_error(
        """contract "Bad" {
    state:
        balance: int

    event transfer(recipient: address) {
        do:
            balance := recipient
    }
}
""",
        "Cannot assign value of type address to int",
    )


def test_rejects_map_index_with_wrong_domain_type():
    _assert_type_error(
        """contract "Bad" {
    state:
        balances: map(address -> int)

    event set(amount: int) {
        do:
            balances[amount] := 1
    }
}
""",
        "Map index has the wrong type",
    )


def test_rejects_duplicate_state_declaration():
    _assert_type_error(
        """contract "Bad" {
    state:
        balance: int
        balance: address
}
""",
        "Duplicate state declaration",
    )


def test_rejects_duplicate_event_parameter_name():
    _assert_type_error(
        """contract "Bad" {
    state:
        balance: int

    event set(amount: int, amount: address) {
        do:
            balance := 0
    }
}
""",
        "Duplicate or shadowing declaration for event parameter",
    )


def test_rejects_indexing_non_map_value():
    _assert_type_error(
        """contract "Bad" {
    state:
        total: int

    event set(amount: int) {
        do:
            total[amount] := amount
    }
}
""",
        "Cannot index value of type int",
    )


def test_rejects_non_numeric_arithmetic_operand():
    _assert_type_error(
        """contract "Bad" {
    state:
        owner: address
        balance: int

    event set() {
        do:
            balance := owner + 1
    }
}
""",
        "Arithmetic operand must be numeric",
    )


def test_rejects_boolean_arithmetic_operand():
    _assert_type_error(
        """contract "Bad" {
    state:
        enabled: bool
        total: int

    event set() {
        do:
            total := enabled + 1
    }
}
""",
        "Arithmetic operand must be numeric",
    )


def test_rejects_incompatible_comparison():
    _assert_type_error(
        """contract "Bad" {
    state:
        owner: address

    invariants:
        owner >= 0
}
""",
        "Left side of comparison must be numeric",
    )


def test_rejects_bool_numeric_comparison_mismatch():
    _assert_type_error(
        """contract "Bad" {
    state:
        enabled: bool

    invariants:
        enabled == 1
}
""",
        "Cannot compare bool with nat",
    )


def test_rejects_non_boolean_guard():
    _assert_type_error(
        """contract "Bad" {
    state:
        balance: int

    event set(amount: int) {
        where amount + 1
        do:
            balance := amount
    }
}
""",
        "Guard in event 'set' must be a boolean expression",
    )


def test_rejects_numeric_conditional_guard():
    _assert_type_error(
        """contract "Bad" {
    state:
        flag: int

    event set() {
        do:
            if flag then
                flag := 1
            else
                flag := 0
            end
    }
}
""",
        "Conditional guard must be a boolean expression",
    )


def test_rejects_numeric_logical_operand():
    _assert_type_error(
        """contract "Bad" {
    state:
        enabled: bool
        total: int

    event set() {
        where enabled and total
        do:
            total := 1
    }
}
""",
        "Logical operand must be boolean",
    )


def test_rejects_bool_assigned_to_numeric_state():
    _assert_type_error(
        """contract "Bad" {
    state:
        total: int

    event set() {
        do:
            total := true
    }
}
""",
        "Cannot assign value of type bool to int",
    )


def test_rejects_numeric_assigned_to_bool_state():
    _assert_type_error(
        """contract "Bad" {
    state:
        enabled: bool

    event set() {
        do:
            enabled := 1
    }
}
""",
        "Cannot assign value of type nat to bool",
    )


def test_rejects_type_mismatch_inside_conditional_branch():
    _assert_type_error(
        """contract "Bad" {
    state:
        balance: int

    event set(flag: int, recipient: address) {
        do:
            if flag > 0 then
                balance := recipient
            else
                balance := 0
            end
    }
}
""",
        "Cannot assign value of type address to int",
    )


def test_accepts_struct_state_literal_and_field_access():
    _check_program(
        """contract "Good" {
    struct Loan { borrower: address; amount: nat; deadline: nat }

    state:
        current: Loan
        total: nat

    event issue(borrower: address, amount: nat, deadline: nat) {
        where amount > 0
        do:
            current := Loan { borrower: borrower; amount: amount; deadline: deadline },
            total := current.amount
    }
}
"""
    )


def test_accepts_bool_state_logical_expression_and_event_param():
    _check_program(
        """contract "Good" {
    state:
        enabled: bool
        paused: bool

    invariants:
        enabled or not paused

    event set(next: bool) {
        where next xor paused
        do:
            enabled := next and true
    }
}
"""
    )


def test_accepts_struct_typed_event_parameter_whole_assignment():
    _check_program(
        """contract "Good" {
    struct Position { holder: address; balance: nat; opened_at: nat }

    state:
        active: Position

    event replace(next: Position) {
        do:
            active := next
    }
}
"""
    )


def test_accepts_boolean_comparisons_and_conditional_guard():
    _check_program(
        """contract "Good" {
    state:
        enabled: bool
        count: int

    event set(next: bool) {
        do:
            if next == true then
                enabled := false
            else
                enabled := true
            end,
            count := count + 1
    }
}
"""
    )


def test_accepts_struct_inside_map_and_nested_field_guard():
    _check_program(
        """contract "Good" {
    struct Loan { borrower: address; amount: nat; deadline: nat }

    state:
        loans: map(nat -> Loan)

    event close(loan_id: nat, replacement: Loan) {
        where loans[loan_id].amount > 0
        do:
            loans[loan_id] := replacement
    }
}
"""
    )


def test_accepts_bool_map_state_and_indexed_guard():
    _check_program(
        """contract "Good" {
    state:
        minted: map(int -> bool)

    event mint(token_id: int) {
        where not minted[token_id]
        do:
            minted[token_id] := true
    }
}
"""
    )


def test_parses_enum_declaration_syntax():
    tree = Lark(grammar, parser="lalr", propagate_positions=True).parse(
        """contract "Good" {
    enum Status { Pending, Funded, Released, Refunded }

    state:
        status: Status
}
"""
    )

    enum_decl = tree.children[0].children[1].children[0]
    assert enum_decl.data == "enum_decl"
    assert str(enum_decl.children[0]) == "Status"
    assert [str(value) for value in enum_decl.children[1].children] == [
        "Pending",
        "Funded",
        "Released",
        "Refunded",
    ]


def test_accepts_enum_state_and_value_comparisons():
    _check_program(
        """contract "Good" {
    enum Status { Pending, Funded, Released, Refunded }

    state:
        status: Status

    invariants:
        status != Refunded

    event fund(next: Status) {
        where status == Pending
        where next == Funded
        do:
            status := next
    }
}
"""
    )


def test_accepts_enum_event_parameter_and_conditional_guard():
    _check_program(
        """contract "Good" {
    enum Status { Pending, Funded, Released }

    state:
        status: Status
        released: bool

    event transition(next: Status) {
        do:
            if next == Released then
                released := true
            else
                released := false
            end,
            status := next
    }
}
"""
    )


def test_accepts_enum_inside_map_state():
    _check_program(
        """contract "Good" {
    enum Status { Pending, Funded, Closed }

    state:
        statuses: map(nat -> Status)

    event close(escrow_id: nat) {
        where statuses[escrow_id] == Funded
        do:
            statuses[escrow_id] := Closed
    }
}
"""
    )


def test_rejects_cross_enum_comparison():
    _assert_type_error(
        """contract "Bad" {
    enum Status { Pending, Funded }
    enum Phase { Open, Closed }

    state:
        status: Status
        phase: Phase

    invariants:
        status == Open
}
""",
        "Cannot compare Status with Phase",
    )


def test_rejects_enum_arithmetic():
    _assert_type_error(
        """contract "Bad" {
    enum Status { Pending, Funded }

    state:
        status: Status
        total: int

    event set() {
        do:
            total := status + 1
    }
}
""",
        "Arithmetic operand must be numeric",
    )


def test_rejects_undeclared_enum_value():
    _assert_type_error(
        """contract "Bad" {
    enum Status { Pending, Funded }

    state:
        status: Status

    invariants:
        status == Released
}
""",
        "Undeclared enum value 'Released'",
    )


def test_rejects_enum_integer_mismatch():
    _assert_type_error(
        """contract "Bad" {
    enum Status { Pending, Funded }

    state:
        status: Status

    event set() {
        do:
            status := 1
    }
}
""",
        "Cannot assign value of type nat to Status",
    )


def test_accepts_multiplication_division_and_modulo_on_numeric_values():
    _check_program(
        """contract "Good" {
    state:
        balance: nat
        fee: nat

    event charge(amount: nat, rate: nat, divisor: nat) {
        where divisor > 0
        do:
            fee := amount * rate / divisor,
            balance := balance % divisor
    }
}
"""
    )


def test_arithmetic_precedence_keeps_product_inside_addition_tree():
    source = """contract "Good" {
    state:
        total: nat

    event set(a: nat, b: nat, c: nat) {
        do:
            total := a + b * c
    }
}
"""
    tree = _parse_program(source)

    arithmetic = _find_tree(tree, "arithmetic")
    assert arithmetic is not None
    assert str(arithmetic.children[1]) == "+"
    product = arithmetic.children[2]
    assert getattr(product, "data", None) == "product"
    assert str(product.children[1]) == "*"
    _check_program(source)


def test_parentheses_can_make_addition_bind_before_multiplication():
    tree = _parse_program(
        """contract "Good" {
    state:
        total: nat

    event set(a: nat, b: nat, c: nat) {
        do:
            total := (a + b) * c
    }
}
"""
    )

    product = _find_tree(tree, "product")
    assert product is not None
    assert str(product.children[1]) == "*"
    assert getattr(product.children[0], "data", None) == "arithmetic"
    _check_program(
        """contract "Good" {
    state:
        total: nat

    event set(a: nat, b: nat, c: nat) {
        do:
            total := (a + b) * c
    }
}
"""
    )


def test_rejects_multiplication_on_non_numeric_operand():
    _assert_type_error(
        """contract "Bad" {
    state:
        owner: address
        total: nat

    event set(amount: nat) {
        do:
            total := owner * amount
    }
}
""",
        "Arithmetic operand must be numeric",
    )


def test_rejects_modulo_on_boolean_operand():
    _assert_type_error(
        """contract "Bad" {
    state:
        enabled: bool
        total: nat

    event set(amount: nat) {
        do:
            total := enabled % amount
    }
}
""",
        "Arithmetic operand must be numeric",
    )


def test_rejects_division_on_enum_operand():
    _assert_type_error(
        """contract "Bad" {
    enum Status { Pending, Funded }

    state:
        status: Status
        total: nat

    event set(amount: nat) {
        do:
            total := amount / status
    }
}
""",
        "Arithmetic operand must be numeric",
    )


def test_accepts_msg_sender_guard_inside_event_body():
    _check_program(
        """contract "Good" {
    state:
        owner: address
        paused: bool

    event pause() {
        where msg_sender == owner
        do:
            paused := true
    }
}
"""
    )


def test_accepts_numeric_context_identifiers_inside_event_body():
    _check_program(
        """contract "Good" {
    state:
        last_paid: nat
        deadline: nat

    event pay() {
        where msg_value > 0
        where block_number >= 0
        do:
            last_paid := block_timestamp,
            deadline := block_timestamp + 100
    }
}
"""
    )


def test_rejects_assignment_to_context_identifier():
    _assert_type_error(
        """contract "Bad" {
    state:
        owner: address

    event set(next: address) {
        do:
            msg_sender := next
    }
}
""",
        "Cannot assign to read-only context identifier 'msg_sender'",
    )


def test_rejects_context_identifier_parameter_shadowing():
    _assert_type_error(
        """contract "Bad" {
    state:
        owner: address

    event set(msg_sender: address) {
        do:
            owner := msg_sender
    }
}
""",
        "Duplicate or shadowing declaration for event parameter 'msg_sender'",
    )


def test_rejects_context_identifier_outside_event_body():
    _assert_type_error(
        """contract "Bad" {
    state:
        owner: address

    invariants:
        msg_sender == owner
}
""",
        "Context identifier 'msg_sender' is only available inside event bodies",
    )


def test_rejects_context_identifier_struct_field_shadowing():
    _assert_type_error(
        """contract "Bad" {
    struct Call { msg_sender: address; value: nat }

    state:
        current: Call
}
""",
        "Struct field 'msg_sender' conflicts with a context identifier",
    )


def test_context_access_control_example_typechecks():
    source = (REPO_ROOT / "examples" / "context_access_control.dsl").read_text(encoding="utf-8")
    _check_program(source)


def test_rejects_undeclared_struct_state_type():
    _assert_type_error(
        """contract "Bad" {
    state:
        current: Loan
}
""",
        "Undeclared named type 'Loan'",
    )


def test_rejects_undeclared_struct_event_parameter_type():
    _assert_type_error(
        """contract "Bad" {
    state:
        total: nat

    event replace(next: Loan) {
        do:
            total := 0
    }
}
""",
        "Undeclared named type 'Loan'",
    )


def test_rejects_struct_literal_missing_field():
    _assert_type_error(
        """contract "Bad" {
    struct Loan { borrower: address; amount: nat; deadline: nat }

    state:
        current: Loan

    event issue(borrower: address, amount: nat) {
        do:
            current := Loan { borrower: borrower; amount: amount }
    }
}
""",
        "Missing field 'deadline' for struct 'Loan'",
    )


def test_rejects_struct_literal_mistyped_field():
    _assert_type_error(
        """contract "Bad" {
    struct Loan { borrower: address; amount: nat; deadline: nat }

    state:
        current: Loan

    event issue(borrower: address, deadline: nat) {
        do:
            current := Loan { borrower: borrower; amount: borrower; deadline: deadline }
    }
}
""",
        "Cannot assign value of type address to nat",
    )


def test_rejects_missing_struct_field_access():
    _assert_type_error(
        """contract "Bad" {
    struct Loan { borrower: address; amount: nat; deadline: nat }

    state:
        current: Loan
        total: nat

    event read() {
        do:
            total := current.status
    }
}
""",
        "Struct 'Loan' has no field 'status'",
    )


def test_rejects_struct_assignment_between_different_struct_types():
    _assert_type_error(
        """contract "Bad" {
    struct Loan { borrower: address; amount: nat; deadline: nat }
    struct Position { holder: address; balance: nat; opened_at: nat }

    state:
        current: Loan

    event replace(next: Position) {
        do:
            current := next
    }
}
""",
        "Cannot assign value of type Position to Loan",
    )


def test_rejects_sum_on_non_map():
    _assert_type_error(
        """contract "Bad" {
    state:
        total: int

    invariants:
        sum(total) >= 0
}
""",
        "sum(...) expects a map",
    )


def test_accepts_nested_maps_quantifiers_and_conditionals():
    _check_program(
        """contract "Good" {
    state:
        allowances: map(address -> map(address -> nat))
        fee: nat

    invariants:
        forall owner, spender . allowances[owner][spender] >= 0;
        fee >= 0

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
    )


def test_main_cli_surfaces_type_errors_without_traceback():
    tmp_dir = REPO_ROOT / ".tmp_tests" / f"typecheck_cli_{uuid.uuid4().hex}"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    source_path = tmp_dir / "bad.dsl"
    output_path = tmp_dir / "bad.mch"
    source_path.write_text(
        """contract "Bad" {
    state:
        owner: address

    event set(amount: int) {
        do:
            owner := amount
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

    assert result.returncode == 1
    assert "Type error at line" in result.stdout
    assert "Traceback" not in result.stdout
    assert not output_path.exists()
