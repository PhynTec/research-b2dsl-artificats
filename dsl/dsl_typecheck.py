"""
Static type checker for the smart-contract DSL.

This pass runs after parsing and before B generation. It validates that
identifiers are declared, indexed map access uses the correct key type,
assignments are type compatible, and arithmetic/comparison expressions
stay within the supported type rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional

from lark import Token, Tree


@dataclass(frozen=True)
class DSLType:
    """Concrete DSL type."""

    kind: str
    from_type: Optional["DSLType"] = None
    to_type: Optional["DSLType"] = None
    fields: Optional[Dict[str, "DSLType"]] = None

    def render(self) -> str:
        if self.kind == "map":
            return f"map({self.from_type.render()} -> {self.to_type.render()})"
        if self.kind in {"struct", "enum"}:
            return self.to_type.render() if self.to_type is not None else "<struct>"
        return self.kind


class UnknownType:
    """Mutable placeholder used for quantified variables."""

    def __init__(self, name: str):
        self.name = name
        self.bound: Optional[DSLType] = None

    def render(self) -> str:
        if self.bound is None:
            return f"<unknown {self.name}>"
        return self.bound.render()


BOOL_TYPE = DSLType("bool")
INT_TYPE = DSLType("int")
NAT_TYPE = DSLType("nat")
ADDRESS_TYPE = DSLType("address")
CONTEXT_TYPES = {
    "msg_sender": ADDRESS_TYPE,
    "msg_value": NAT_TYPE,
    "block_number": NAT_TYPE,
    "block_timestamp": NAT_TYPE,
}
CONTEXT_TOKEN_TYPES = {
    "MSG_SENDER",
    "MSG_VALUE",
    "BLOCK_NUMBER",
    "BLOCK_TIMESTAMP",
}


class DSLTypeError(Exception):
    """User-facing static type error with source location."""

    def __init__(self, message: str, line: int, column: int):
        super().__init__(f"Type error at line {line}, column {column}: {message}")
        self.message = message
        self.line = line
        self.column = column


class DSLTypeChecker:
    """Check one parsed DSL contract for static type errors."""

    def __init__(self):
        self.global_symbols: Dict[str, DSLType] = {}
        self.enum_symbols: Dict[str, DSLType] = {}
        self.enum_value_symbols: Dict[str, DSLType] = {}
        self.struct_symbols: Dict[str, DSLType] = {}

    def check(self, tree: Tree) -> None:
        if tree.data == "start":
            tree = tree.children[0]

        if tree.data != "contract":
            self._raise(tree, "Expected a contract node")

        sections = []
        if len(tree.children) > 1 and isinstance(tree.children[1], Tree):
            sections = tree.children[1].children

        for section in sections:
            if isinstance(section, Tree) and section.data == "enum_decl":
                self._register_enum_declaration(section)

        for section in sections:
            if isinstance(section, Tree) and section.data == "struct_decl":
                self._register_struct_declaration(section)

        for section in sections:
            if isinstance(section, Tree) and section.data == "state_section":
                self._register_state_declarations(section)

        for section in sections:
            if not isinstance(section, Tree):
                continue
            if section.data == "invariants_section":
                self._check_invariants_section(section)
            elif section.data == "event_section":
                self._check_event_section(section)

    def _register_enum_declaration(self, enum_decl: Tree) -> None:
        name_token = enum_decl.children[0]
        enum_name = str(name_token)
        if enum_name in self.enum_symbols:
            self._raise(name_token, f"Duplicate enum declaration for '{enum_name}'")
        if enum_name in self.struct_symbols:
            self._raise(name_token, f"Enum name '{enum_name}' conflicts with a struct type")
        if enum_name in {"int", "nat", "address", "bool", "map"}:
            self._raise(name_token, f"Enum name '{enum_name}' conflicts with a built-in type")

        enum_type = DSLType("enum", to_type=DSLType(enum_name))
        self.enum_symbols[enum_name] = enum_type

        seen_values = set()
        value_list = enum_decl.children[1]
        for value_token in value_list.children:
            value_name = str(value_token)
            if value_name in seen_values:
                self._raise(value_token, f"Duplicate value '{value_name}' in enum '{enum_name}'")
            if value_name in self.enum_value_symbols:
                self._raise(value_token, f"Enum value '{value_name}' is already declared")
            seen_values.add(value_name)
            self.enum_value_symbols[value_name] = enum_type

    def _register_struct_declaration(self, struct_decl: Tree) -> None:
        name_token = struct_decl.children[0]
        struct_name = str(name_token)
        if struct_name in self.struct_symbols:
            self._raise(name_token, f"Duplicate struct declaration for '{struct_name}'")
        if struct_name in self.enum_symbols:
            self._raise(name_token, f"Struct name '{struct_name}' conflicts with an enum type")
        if struct_name in {"int", "nat", "address", "bool", "map"}:
            self._raise(name_token, f"Struct name '{struct_name}' conflicts with a built-in type")

        field_list = struct_decl.children[1]
        fields: Dict[str, DSLType] = {}
        struct_type = DSLType("struct", to_type=DSLType(struct_name), fields=fields)
        self.struct_symbols[struct_name] = struct_type

        for field in field_list.children:
            field_name_token = self._identifier_token(field.children[0])
            field_name = str(field_name_token)
            if field_name in fields:
                self._raise(field_name_token, f"Duplicate field '{field_name}' in struct '{struct_name}'")
            if field_name in CONTEXT_TYPES:
                self._raise(field_name_token, f"Struct field '{field_name}' conflicts with a context identifier")
            fields[field_name] = self._parse_type(field.children[1])

    def _register_state_declarations(self, state_section: Tree) -> None:
        declaration_list = state_section.children[0]
        for declaration in declaration_list.children:
            name_token = self._identifier_token(declaration.children[0])
            type_tree = declaration.children[1]
            name = str(name_token)
            if name in self.global_symbols:
                self._raise(name_token, f"Duplicate state declaration for '{name}'")
            if name in self.enum_value_symbols:
                self._raise(name_token, f"State declaration '{name}' conflicts with an enum value")
            if name in CONTEXT_TYPES:
                self._raise(name_token, f"State declaration '{name}' conflicts with a context identifier")
            self.global_symbols[name] = self._parse_type(type_tree)

    def _check_invariants_section(self, invariants_section: Tree) -> None:
        expr_list = invariants_section.children[0]
        for expr in expr_list.children:
            expr_type = self._infer_expr_type(expr, dict(self.global_symbols))
            self._require_type(expr_type, BOOL_TYPE, expr, "Invariant must be a boolean expression")

    def _check_event_section(self, event_section: Tree) -> None:
        event_decl = event_section.children[0]
        name_token = event_decl.children[0]
        params_tree = None
        body_tree = None

        if len(event_decl.children) == 3:
            params_tree = event_decl.children[1]
            body_tree = event_decl.children[2]
        else:
            body_tree = event_decl.children[1]

        scope = dict(self.global_symbols)
        scope.update(CONTEXT_TYPES)
        if params_tree is not None:
            for param in params_tree.children:
                param_name_token = self._identifier_token(param.children[0])
                param_name = str(param_name_token)
                if param_name in scope:
                    self._raise(
                        param_name_token,
                        f"Duplicate or shadowing declaration for event parameter '{param_name}'",
                    )
                if param_name in self.enum_value_symbols:
                    self._raise(param_name_token, f"Event parameter '{param_name}' conflicts with an enum value")
                scope[param_name] = self._parse_type(param.children[1])

        guards_tree = body_tree.children[0] if body_tree.children else None
        actions_tree = body_tree.children[1] if len(body_tree.children) > 1 else None

        if guards_tree is not None:
            for guard in guards_tree.children:
                guard_type = self._infer_expr_type(guard, scope)
                self._require_type(
                    guard_type,
                    BOOL_TYPE,
                    guard,
                    f"Guard in event '{name_token}' must be a boolean expression",
                )

        if actions_tree is not None:
            for action in actions_tree.children:
                self._check_action(action, scope)

    def _check_action(self, action: Tree, scope: Dict[str, object]) -> None:
        if action.data == "action":
            lhs_type = self._infer_lvalue_type(action.children[0], scope)
            rhs_type = self._infer_expr_type(action.children[1], scope)
            self._require_assignable(lhs_type, rhs_type, action.children[1])
            return

        if action.data == "conditional_action":
            condition_type = self._infer_expr_type(action.children[0], scope)
            self._require_type(
                condition_type,
                BOOL_TYPE,
                action.children[0],
                "Conditional guard must be a boolean expression",
            )
            self._check_action_list(action.children[1], scope)
            if len(action.children) > 2:
                self._check_action_list(action.children[2], scope)
            return

        self._raise(action, f"Unsupported action node '{action.data}'")

    def _check_action_list(self, action_list: Tree, scope: Dict[str, object]) -> None:
        for child in action_list.children:
            self._check_action(child, scope)

    def _infer_lvalue_type(self, lvalue: Tree, scope: Dict[str, object]) -> DSLType:
        base_token = self._identifier_token(lvalue.children[0])
        if str(base_token) in CONTEXT_TYPES:
            self._raise(base_token, f"Cannot assign to read-only context identifier '{base_token}'")
        current_type = self._lookup_name(base_token, scope)
        for index_tree in lvalue.children[1:]:
            current_type = self._infer_indexed_type(current_type, index_tree.children[0], scope)
        return self._resolve_type(current_type, lvalue)

    def _infer_expr_type(self, node, scope: Dict[str, object]):
        if isinstance(node, Token):
            if node.type == "NAME":
                return self._lookup_name(node, scope)
            if node.type in CONTEXT_TOKEN_TYPES:
                return self._lookup_name(node, scope)
            if node.type == "NUMBER":
                return NAT_TYPE if int(str(node)) >= 0 else INT_TYPE
            self._raise(node, f"Unsupported token '{node.type}'")

        if not isinstance(node, Tree):
            self._raise(node, "Unsupported expression node")

        if node.data == "comparison":
            if len(node.children) == 1:
                return self._infer_expr_type(node.children[0], scope)
            left = self._infer_expr_type(node.children[0], scope)
            operator = str(node.children[1])
            right = self._infer_expr_type(node.children[2], scope)
            if operator in {"=", "/=", "==", "!="}:
                self._require_comparable(left, right, node)
            else:
                self._require_numeric(left, node.children[0], "Left side of comparison must be numeric")
                self._require_numeric(right, node.children[2], "Right side of comparison must be numeric")
                self._require_numeric_compatible(left, right, node)
            return BOOL_TYPE

        if node.data in {"logical_and", "logical_or", "logical_xor"}:
            if len(node.children) == 1:
                return self._infer_expr_type(node.children[0], scope)
            for operand in node.children:
                operand_type = self._infer_expr_type(operand, scope)
                self._require_type(operand_type, BOOL_TYPE, operand, "Logical operand must be boolean")
            return BOOL_TYPE

        if node.data == "logical_not":
            operand_type = self._infer_expr_type(node.children[0], scope)
            self._require_type(operand_type, BOOL_TYPE, node.children[0], "Logical operand must be boolean")
            return BOOL_TYPE

        if node.data in {"arithmetic", "product"}:
            return self._infer_numeric_expr_type(node, scope)

        if node.data == "indexed_expr":
            base_token = self._identifier_token(node.children[0])
            current_type = self._lookup_name(base_token, scope)
            for index_tree in node.children[1:]:
                current_type = self._infer_indexed_type(current_type, index_tree.children[0], scope)
            return self._resolve_type(current_type, node)

        if node.data in {"identifier_name", "context_identifier"}:
            return self._infer_expr_type(self._identifier_token(node), scope)

        if node.data == "field_expr":
            current_type = self._infer_expr_type(node.children[0], scope)
            for field_access in node.children[1:]:
                current_type = self._infer_field_type(current_type, field_access.children[0])
            return self._resolve_type(current_type, node)

        if node.data == "function_call":
            function_name = str(node.children[0])
            args_tree = node.children[1] if len(node.children) > 1 else None
            args = [] if args_tree is None else args_tree.children
            if function_name != "sum":
                self._raise(node, f"Unsupported function '{function_name}'")
            if len(args) != 1:
                self._raise(node, "sum(...) expects exactly one argument")
            target_type = self._infer_expr_type(args[0], scope)
            target_type = self._resolve_type(target_type, args[0])
            if target_type.kind != "map":
                self._raise(args[0], f"sum(...) expects a map, got {target_type.render()}")
            codomain = target_type.to_type
            if codomain.kind not in {"int", "nat"}:
                self._raise(args[0], f"sum(...) requires a numeric map codomain, got {codomain.render()}")
            return codomain

        if node.data == "struct_literal":
            return self._infer_struct_literal_type(node, scope)

        if node.data in {"true_literal", "false_literal"}:
            return BOOL_TYPE

        if node.data == "quantified":
            quantified_scope = dict(scope)
            for name_token in self._iter_name_tokens(node.children[0]):
                name = str(name_token)
                if name in quantified_scope:
                    self._raise(name_token, f"Duplicate quantified variable '{name}'")
                quantified_scope[name] = UnknownType(name)
            body_type = self._infer_expr_type(node.children[1], quantified_scope)
            self._require_type(body_type, BOOL_TYPE, node.children[1], "Quantified body must be boolean")
            return BOOL_TYPE

        if node.data == "name_list":
            self._raise(node, "Unexpected standalone quantified name list")

        if node.data == "arg_list":
            self._raise(node, "Unexpected standalone argument list")

        if node.data == "expr_list":
            self._raise(node, "Unexpected expression list")

        if node.data in {"struct_value_list", "struct_value"}:
            self._raise(node, "Unexpected standalone struct literal field")

        if len(node.children) == 1:
            return self._infer_expr_type(node.children[0], scope)

        self._raise(node, f"Unsupported expression node '{node.data}'")

    def _infer_indexed_type(self, current_type, index_expr, scope: Dict[str, object]):
        resolved = self._resolve_type(current_type, index_expr)
        if resolved.kind != "map":
            self._raise(index_expr, f"Cannot index value of type {resolved.render()}")
        index_type = self._infer_expr_type(index_expr, scope)
        self._require_type(index_type, resolved.from_type, index_expr, "Map index has the wrong type")
        return resolved.to_type

    def _infer_field_type(self, current_type, field_token: Token) -> DSLType:
        resolved = self._resolve_type(current_type, field_token)
        if resolved.kind != "struct":
            self._raise(field_token, f"Cannot access field on value of type {resolved.render()}")
        field_name = str(field_token)
        if field_name not in resolved.fields:
            self._raise(field_token, f"Struct '{resolved.render()}' has no field '{field_name}'")
        return resolved.fields[field_name]

    def _infer_struct_literal_type(self, node: Tree, scope: Dict[str, object]) -> DSLType:
        struct_name_token = node.children[0]
        struct_name = str(struct_name_token)
        if struct_name not in self.struct_symbols:
            self._raise(struct_name_token, f"Undeclared struct type '{struct_name}'")
        struct_type = self.struct_symbols[struct_name]
        expected_fields = struct_type.fields or {}
        values_tree = node.children[1]
        provided: Dict[str, object] = {}

        for value in values_tree.children:
            field_name_token = value.children[0]
            field_name = str(field_name_token)
            if field_name in provided:
                self._raise(field_name_token, f"Duplicate value for field '{field_name}' in struct '{struct_name}'")
            if field_name not in expected_fields:
                self._raise(field_name_token, f"Struct '{struct_name}' has no field '{field_name}'")
            provided[field_name] = value.children[1]

        missing = [field_name for field_name in expected_fields if field_name not in provided]
        if missing:
            self._raise(node, f"Missing field '{missing[0]}' for struct '{struct_name}'")

        for field_name, expr in provided.items():
            actual_type = self._infer_expr_type(expr, scope)
            self._require_assignable(expected_fields[field_name], actual_type, expr)

        return struct_type

    def _infer_numeric_expr_type(self, node: Tree, scope: Dict[str, object]) -> DSLType:
        current_type = self._infer_expr_type(node.children[0], scope)
        if len(node.children) == 1:
            return current_type
        self._require_numeric(current_type, node.children[0], "Arithmetic operand must be numeric")
        current_concrete = self._resolve_numeric_type(current_type, node.children[0])
        index = 1
        while index < len(node.children):
            rhs = self._infer_expr_type(node.children[index + 1], scope)
            self._require_numeric(rhs, node.children[index + 1], "Arithmetic operand must be numeric")
            rhs_concrete = self._resolve_numeric_type(rhs, node.children[index + 1])
            self._require_numeric_compatible(current_concrete, rhs_concrete, node)
            current_concrete = NAT_TYPE if current_concrete.kind == rhs_concrete.kind == "nat" else INT_TYPE
            index += 2
        return current_concrete

    def _lookup_name(self, name_token: Token, scope: Dict[str, object]):
        name = str(name_token)
        if name in scope:
            return scope[name]
        if name in CONTEXT_TYPES:
            self._raise(name_token, f"Context identifier '{name}' is only available inside event bodies")
        if name in self.enum_value_symbols:
            return self.enum_value_symbols[name]
        if name[:1].isupper():
            self._raise(name_token, f"Undeclared enum value '{name}'")
        if name not in scope:
            self._raise(name_token, f"Undeclared identifier '{name}'")

    def _parse_type(self, node: Tree) -> DSLType:
        if node.data == "address_type":
            return ADDRESS_TYPE
        if node.data == "int_type":
            return INT_TYPE
        if node.data == "nat_type":
            return NAT_TYPE
        if node.data == "named_type":
            type_name = str(node.children[0])
            if type_name in self.struct_symbols:
                return self.struct_symbols[type_name]
            if type_name in self.enum_symbols:
                return self.enum_symbols[type_name]
            self._raise(node.children[0], f"Undeclared named type '{type_name}'")
        if node.data == "bool_type":
            return BOOL_TYPE
        if node.data == "map_type":
            return DSLType("map", self._parse_type(node.children[0]), self._parse_type(node.children[1]))
        self._raise(node, f"Unsupported type node '{node.data}'")

    def _require_assignable(self, target_type, value_type, node) -> None:
        target_type = self._resolve_type(target_type, node)
        value_type = self._resolve_type(value_type, node)

        if self._types_equal(target_type, value_type):
            return
        if target_type.kind == "int" and value_type.kind == "nat":
            return
        self._raise(
            node,
            f"Cannot assign value of type {value_type.render()} to {target_type.render()}",
        )

    def _require_type(self, actual_type, expected_type: DSLType, node, message: str) -> None:
        actual_type = self._resolve_type(actual_type, node, expected_type=expected_type)
        if self._types_equal(actual_type, expected_type):
            return
        self._raise(node, f"{message}; got {actual_type.render()}, expected {expected_type.render()}")

    def _require_comparable(self, left_type, right_type, node) -> None:
        left_type = self._resolve_type(left_type, node)
        right_type = self._resolve_type(right_type, node)
        if self._types_equal(left_type, right_type):
            return
        if self._is_numeric_type(left_type) and self._is_numeric_type(right_type):
            return
        self._raise(node, f"Cannot compare {left_type.render()} with {right_type.render()}")

    def _require_numeric(self, actual_type, node, message: str) -> None:
        actual_type = self._resolve_type(actual_type, node, expected_type=INT_TYPE, prefer_numeric=True)
        if self._is_numeric_type(actual_type):
            return
        self._raise(node, f"{message}; got {actual_type.render()}")

    def _require_numeric_compatible(self, left_type, right_type, node) -> None:
        left_type = self._resolve_type(left_type, node)
        right_type = self._resolve_type(right_type, node)
        if self._is_numeric_type(left_type) and self._is_numeric_type(right_type):
            return
        self._raise(node, f"Numeric operands are incompatible: {left_type.render()} and {right_type.render()}")

    def _resolve_numeric_type(self, actual_type, node) -> DSLType:
        resolved = self._resolve_type(actual_type, node, expected_type=INT_TYPE, prefer_numeric=True)
        if not self._is_numeric_type(resolved):
            self._raise(node, f"Expected a numeric type, got {resolved.render()}")
        return resolved

    def _resolve_type(self, type_spec, node, expected_type: Optional[DSLType] = None, prefer_numeric: bool = False) -> DSLType:
        if isinstance(type_spec, UnknownType):
            if type_spec.bound is not None:
                return type_spec.bound
            if expected_type is not None:
                type_spec.bound = expected_type
                return expected_type
            if prefer_numeric:
                type_spec.bound = INT_TYPE
                return INT_TYPE
            self._raise(node, f"Could not infer type for '{type_spec.name}'")
        return type_spec

    def _types_equal(self, left: DSLType, right: DSLType) -> bool:
        if left.kind != right.kind:
            return False
        if left.kind in {"struct", "enum"}:
            return left.render() == right.render()
        if left.kind != "map":
            return True
        return self._types_equal(left.from_type, right.from_type) and self._types_equal(left.to_type, right.to_type)

    def _is_numeric_type(self, type_spec: DSLType) -> bool:
        return type_spec.kind in {"int", "nat"}

    def _iter_name_tokens(self, name_list: Tree) -> Iterable[Token]:
        for child in name_list.children:
            if isinstance(child, Token) and child.type == "NAME":
                yield child

    def _identifier_token(self, node) -> Token:
        if isinstance(node, Token):
            return node
        if isinstance(node, Tree) and node.data in {"identifier_name", "context_identifier"}:
            return self._identifier_token(node.children[0])
        self._raise(node, "Expected an identifier")

    def _raise(self, node, message: str) -> None:
        line = getattr(node, "line", None)
        column = getattr(node, "column", None)
        meta = getattr(node, "meta", None)
        if meta is not None:
            line = line or getattr(meta, "line", None)
            column = column or getattr(meta, "column", None)
        raise DSLTypeError(message, line or 1, column or 1)
