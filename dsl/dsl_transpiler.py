"""
Convert DSL parse trees into classical B machine text.

Walk the Lark tree bottom-up: each method named after a grammar rule
receives already-transformed children and returns the fragment consumed
by its parent rule.

Read the class in two halves. Use the grammar-rule handlers near the
top to normalize parse nodes into intermediate dicts and strings. Use
the private helpers near the bottom to render those normalized pieces
into final B clauses, initialisation blocks, and operations.

Keep three design decisions in mind while editing this file:
- Bound animation with `anim_steps_left` because ProB needs a finite
  step budget when animating open-ended event systems.
- Rewrite numeric map reads to `({k |-> 0} <+ map)(k)` so absent keys
  behave like zero instead of becoming undefined B applications.
- Infer `x : dom(map)` guards by scanning rendered guard expressions,
  while skipping `sum(map)` rewrites whose SIGMA binder is local to the
  expression.
"""

import re

from lark import Transformer, v_args


CONTEXT_PARAM_TYPES = {
    "msg_sender": {"kind": "address"},
    "msg_value": {"kind": "nat"},
    "block_number": {"kind": "nat"},
    "block_timestamp": {"kind": "nat"},
}


class EventBGenerator(Transformer):
    """Transform the DSL into a classical B machine."""

    def __init__(self, defensive=False):
        super().__init__()
        self.defensive = defensive
        # Keeps declared state variable types for later typing/rewriting steps.
        self.declared_types = {}
        # Finite demo bound used to keep operation-parameter
        # enumeration executable in ProB.
        self.demo_max_amount = 100
        # Finite execution budget used to stop unbounded animation
        # loops in ProB.
        self.demo_max_steps = 12
        self.animation_steps_var = "anim_steps_left"
        self.enum_types = {}
        self.struct_types = {}

    def start(self, args):
        """Return the transformed contract node."""
        return args[0]

    def contract(self, args):
        """Assemble one complete B machine from tagged section payloads.

        Merge declarations, semantic invariants, and events before
        rendering the global clauses in the order expected by
        classical B.
        """
        name = str(args[0]).strip('"')
        sections = args[1] if (len(args) > 1 and args[1] is not None) else []

        enum_declarations = []
        struct_declarations = []
        declarations = []
        semantic_invariants = []
        events = []

        for section in sections:
            if not isinstance(section, dict):
                continue
            section_type = section.get("type")
            if section_type == "enum":
                enum_declarations.append(section)
            elif section_type == "struct":
                struct_declarations.append(section)
            elif section_type == "vars":
                declarations.extend(section["data"])
            elif section_type == "invs":
                semantic_invariants.extend(section["data"])
            elif section_type == "evt":
                events.append(section["data"])

        has_events = bool(events)
        variable_names = [decl["name"] for decl in declarations]
        if has_events:
            variable_names.append(self.animation_steps_var)
        invariants = [self._declaration_to_type_invariant(decl) for decl in declarations]
        invariants.extend(semantic_invariants)
        if has_events:
            invariants.append(f"{self.animation_steps_var} : NATURAL")
            invariants.append(f"{self.animation_steps_var} <= MAX_STEPS")

        output = [f"MACHINE {name}"]

        sets = self._render_sets(enum_declarations, declarations, events)
        if sets:
            output.append("SETS")
            output.extend(sets)

        output.extend(self._render_definitions())

        if variable_names:
            output.append("VARIABLES")
            output.append(f"  {', '.join(variable_names)}")

        output.append("INVARIANT")
        if invariants:
            for i, invariant in enumerate(invariants):
                suffix = " &" if i < len(invariants) - 1 else ""
                output.append(f"  {invariant}{suffix}")
        else:
            output.append("  TRUE")

        output.extend(
            self._render_initialisation(
                declarations,
                semantic_invariants=semantic_invariants,
                include_animation_budget=has_events,
            )
        )

        output.append("OPERATIONS")
        if events:
            for i, event in enumerate(events):
                operation_lines = self._render_operation(event)
                if i < len(events) - 1:
                    operation_lines[-1] = f"{operation_lines[-1]};"
                output.extend(operation_lines)
        else:
            output.append("  skip_op = skip")

        output.append("END")
        return "\n".join(output)

    def section_list(self, args):
        """Keep section order from the DSL source."""
        return args

    def enum_decl(self, args):
        """Capture one enum declaration for B SETS rendering."""
        name = str(args[0])
        values = args[1]
        self.enum_types[name] = values
        return {"type": "enum", "name": name, "values": values}

    def enum_value_list(self, args):
        """Return enum alternatives in source order."""
        return [str(value) for value in args]

    def struct_decl(self, args):
        """Capture one struct declaration for B record type rendering."""
        name = str(args[0])
        fields = args[1]
        self.struct_types[name] = fields
        return {"type": "struct", "name": name, "fields": fields}

    def struct_field_list(self, args):
        """Return struct fields in source order."""
        return args

    def struct_field(self, args):
        """Capture one typed struct field."""
        return {"name": str(args[0]), "type": args[1]}

    def state_section(self, args):
        """Tag parsed state declarations for later contract assembly."""
        return {"type": "vars", "data": args[0]}

    def declaration_list(self, args):
        """Return state declarations as a flat list."""
        return args

    def declaration(self, args):
        """Capture one typed state declaration and store its type metadata."""
        name = str(args[0])
        type_spec = args[1]
        self.declared_types[name] = type_spec
        return {"name": name, "type": type_spec}

    def invariants_section(self, args):
        """Tag semantic invariants provided in the DSL contract."""
        return {"type": "invs", "data": args[0]}

    def expr_list(self, args):
        """Normalize invariant expression list to plain strings."""
        return [str(item) for item in args]

    def event_section(self, args):
        """Pass through already-tagged event data."""
        return args[0]

    def event_decl(self, args):
        """Build the normalized event dict consumed by later renderers.

        Keep parameters optional because zero-argument events omit the
        parameter-list node from the parse tree.
        """
        name = str(args[0])
        if len(args) == 3:
            params = args[1] or []
            body = args[2]
        else:
            params = []
            body = args[1]

        return {
            "type": "evt",
            "data": {
                "name": name,
                "params": params,
                "guards": body.get("guards", []),
                "actions": body.get("actions", []),
            },
        }

    def param_list(self, args):
        """Return event parameters in declared order."""
        return args

    def param(self, args):
        """Capture one typed event parameter."""
        return {"name": str(args[0]), "type": args[1]}

    def body(self, args):
        """Split one event body into normalized guard and action lists.

        Accept missing child lists so later renderers can treat every
        event uniformly, even when the source omits guards.
        """
        guards = args[0] if len(args) > 0 and isinstance(args[0], list) else []
        actions = args[1] if len(args) > 1 and isinstance(args[1], list) else []
        return {"guards": guards, "actions": actions}

    def guard_list(self, args):
        """Convert parsed guards to plain strings for PRE assembly.

        Keep the list shape stable so inferred domain guards can be
        combined with source guards later.
        """
        return [str(item) for item in args]

    def action_list(self, args):
        """Keep event actions in source order for substitution rendering."""
        return args

    def action(self, args):
        """Represent one assignment action without flattening indexed targets.

        Preserve the structured lvalue so substitution rendering can
        choose between direct assignment and map override patterns.
        """
        return {"kind": "assign", "lvalue": args[0], "expr": str(args[1])}

    def conditional_action(self, args):
        """Represent one IF/THEN[/ELSE] action block."""
        condition = self._as_b_predicate(self._safeify_bool_map_reads(self._safeify_numeric_map_reads(str(args[0]))))
        then_actions = args[1] if len(args) > 1 else []
        else_actions = args[2] if len(args) > 2 else []
        return {
            "kind": "conditional",
            "condition": condition,
            "then_actions": then_actions,
            "else_actions": else_actions,
        }

    def lvalue(self, args):
        """Capture the left-hand side as a base name plus index list.

        Preserve each index separately because one-dimensional and
        nested map updates are rendered differently in B.
        """
        return {"base": str(args[0]), "indices": [str(idx) for idx in args[1:]]}

    def index(self, args):
        """Return one index expression used in map access/update."""
        return str(args[0])

    def name_list(self, args):
        """Return quantified variable names in declared order."""
        return [str(name) for name in args]

    def quantified(self, args):
        """Translate `forall` while inserting map definedness checks.

        Keep generated predicates well-defined even when the DSL source
        omits explicit domain guards around indexed map reads.
        """
        var_names = args[0] if isinstance(args[0], list) else [str(args[0])]
        body = str(args[1])
        checks_by_var = self._domain_checks_for_quantified_vars(var_names, body)

        rendered = body
        for var_name in reversed(var_names):
            var_checks = checks_by_var.get(var_name, [])
            if rendered.startswith("!"):
                rendered = f"({rendered})"
            if var_checks:
                antecedent = " & ".join(var_checks)
                if " & " in antecedent:
                    antecedent = f"({antecedent})"
                rendered = f"!{var_name}.({antecedent} => {rendered})"
            else:
                rendered = f"!{var_name}.({rendered})"
        return rendered

    def comparison(self, args):
        """Render an optional comparison over arithmetic expressions."""
        if len(args) == 1:
            return str(args[0])
        return f"{args[0]} {args[1]} {args[2]}"

    def arithmetic(self, args):
        """Render left-associative arithmetic expression text."""
        expr = str(args[0])
        i = 1
        while i < len(args):
            expr = f"{expr} {args[i]} {args[i + 1]}"
            i += 2
        return expr

    def product(self, args):
        """Render multiplication-level arithmetic, including DSL modulo."""
        expr = str(args[0])
        i = 1
        while i < len(args):
            expr = f"{expr} {args[i]} {args[i + 1]}"
            i += 2
        return expr

    def logical_and(self, args):
        """Render DSL boolean conjunction as a B predicate conjunction."""
        return f"({args[0]} & {args[1]})"

    def logical_or(self, args):
        """Render DSL boolean disjunction as a B predicate disjunction."""
        return f"({args[0]} or {args[1]})"

    def logical_xor(self, args):
        """Render DSL xor through ordinary B boolean connectives."""
        return f"(({args[0]} or {args[1]}) & not({args[0]} & {args[1]}))"

    def logical_not(self, args):
        """Render DSL boolean negation."""
        return f"not({args[0]})"

    def indexed_expr(self, args):
        """Convert DSL indexing `x[y]` into B application syntax `x(y)`."""
        expr = str(args[0])
        for idx in args[1:]:
            expr = f"{expr}({idx})"
        return expr

    def field_expr(self, args):
        """Convert DSL dot access into B record field selection."""
        expr = str(args[0])
        for field_name in args[1:]:
            expr = f"{expr}'{field_name}"
        return expr

    def field_access(self, args):
        """Return the accessed field name."""
        return str(args[0])

    def function_call(self, args):
        """Render ordinary calls and special-case DSL `sum(map)`.

        Rewrite `sum(map)` because classical B uses `SIGMA` rather than
        a built-in `sum`, while leaving unrelated function names alone.
        """
        name = str(args[0])
        call_args = args[1] if len(args) > 1 else []

        if name == "sum" and len(call_args) == 1:
            target = str(call_args[0]).strip()
            if self._is_map_variable(target):
                sigma_var = self._fresh_sigma_var(target)
                # Use SIGMA over the map domain because B has no `sum`
                # primitive for partial functions.
                return f"SIGMA({sigma_var}).({sigma_var} : dom({target}) | {target}({sigma_var}))"

        if not call_args:
            return f"{name}()"
        return f"{name}({', '.join(str(a) for a in call_args)})"

    def arg_list(self, args):
        """Return call arguments as plain expression strings."""
        return [str(item) for item in args]

    def struct_literal(self, args):
        """Render a DSL struct literal as a B record literal."""
        return f"rec({', '.join(args[1])})"

    def struct_value_list(self, args):
        """Return rendered record field assignments in source order."""
        return args

    def struct_value(self, args):
        """Render one field assignment inside a B record literal."""
        return f"{args[0]}: {args[1]}"

    def address_type(self, _args):
        """Create the internal node for the abstract `address` type.

        Keep types as small dicts so later helpers branch on `kind`
        instead of raw parse tokens.
        """
        return {"kind": "address"}

    def int_type(self, _args):
        """Create the internal node for the `int` scalar type.

        Keep the representation uniform with other types so rendering
        logic can treat all declarations through one interface.
        """
        return {"kind": "int"}

    def nat_type(self, _args):
        """Create the internal node for the `nat` scalar type.

        Preserve the distinction from `int` so parameter bounds and B
        type rendering can stay faithful to the DSL declaration.
        """
        return {"kind": "nat"}

    def bool_type(self, _args):
        """Create the internal node for the `bool` scalar type."""
        return {"kind": "bool"}

    def named_type(self, args):
        """Create an internal node for enum and struct names."""
        return {"kind": "named", "name": str(args[0])}

    def map_type(self, args):
        """Create the internal node for `map(domain -> codomain)`.

        Preserve both endpoint types so later helpers can recurse when
        rendering B types and choosing default values.
        """
        return {"kind": "map", "from": args[0], "to": args[1]}

    def true_literal(self, _args):
        """Render DSL true as B TRUE."""
        return "TRUE"

    def false_literal(self, _args):
        """Render DSL false as B FALSE."""
        return "FALSE"

    def context_identifier(self, args):
        """Render context identifiers as ordinary generated operation parameters."""
        return str(args[0])

    @v_args(inline=True)
    def NAME(self, name):
        """Token adapter: convert identifier token to string."""
        return str(name)

    @v_args(inline=True)
    def NUMBER(self, num):
        """Token adapter: convert numeric token to string."""
        return str(num)

    @v_args(inline=True)
    def EQEQ(self, _token):
        """Map DSL equality token to B equality symbol."""
        return "="

    @v_args(inline=True)
    def NEQ(self, _token):
        """Map DSL not-equal token to the classical B symbol."""
        return "/="

    @v_args(inline=True)
    def GTE(self, token):
        """Preserve greater-than-or-equal token text."""
        return str(token)

    @v_args(inline=True)
    def LTE(self, token):
        """Preserve less-than-or-equal token text."""
        return str(token)

    @v_args(inline=True)
    def GT(self, token):
        """Preserve greater-than token text."""
        return str(token)

    @v_args(inline=True)
    def LT(self, token):
        """Preserve less-than token text."""
        return str(token)

    @v_args(inline=True)
    def PLUS(self, token):
        """Preserve plus token text."""
        return str(token)

    @v_args(inline=True)
    def MINUS(self, token):
        """Preserve minus token text."""
        return str(token)

    @v_args(inline=True)
    def STAR(self, token):
        """Preserve multiplication token text."""
        return str(token)

    @v_args(inline=True)
    def SLASH(self, token):
        """Preserve division token text."""
        return str(token)

    @v_args(inline=True)
    def PERCENT(self, _token):
        """Map DSL modulo to the B modulo operator."""
        return "mod"

    @v_args(inline=True)
    def MSG_SENDER(self, token):
        """Token adapter for the caller context identifier."""
        return str(token)

    @v_args(inline=True)
    def MSG_VALUE(self, token):
        """Token adapter for the call-value context identifier."""
        return str(token)

    @v_args(inline=True)
    def BLOCK_NUMBER(self, token):
        """Token adapter for the block-number context identifier."""
        return str(token)

    @v_args(inline=True)
    def BLOCK_TIMESTAMP(self, token):
        """Token adapter for the block-timestamp context identifier."""
        return str(token)

    def _render_initialisation(
        self,
        declarations,
        semantic_invariants=None,
        include_animation_budget=False,
    ):
        """Render initial values in executable classical B syntax.

        Use `ANY ... WHERE ... THEN` when address-typed state needs
        elements from the abstract `ADDRESS` set during initialisation.
        """
        lines = ["INITIALISATION"]
        if not declarations:
            lines.append("  skip")
            return lines

        semantic_invariants = semantic_invariants or []
        assignments = []
        any_binders = []
        any_predicates = []
        binder_by_name = {}

        for decl in declarations:
            name = decl["name"]
            type_spec = decl["type"]
            if type_spec["kind"] == "address":
                binder = f"{name}_init"
                binder_by_name[name] = binder
                any_binders.append(binder)
                any_predicates.append(f"{binder} : ADDRESS")
                assignments.append(f"{name} := {binder}")
            else:
                assignments.append(f"{name} := {self._default_value_for_type(type_spec)}")

        any_predicates.extend(
            self._address_initialisation_invariant_predicates(
                binder_by_name,
                semantic_invariants,
            )
        )

        if include_animation_budget:
            assignments.append(f"{self.animation_steps_var} := MAX_STEPS")

        if any_binders:
            # Use ANY...WHERE...THEN to choose legal initial members of
            # the abstract ADDRESS set.
            lines.append(f"  ANY {', '.join(any_binders)} WHERE")
            lines.append(f"    {' & '.join(any_predicates)}")
            lines.append("  THEN")
            lines.append(f"    {' || '.join(assignments)}")
            lines.append("  END")
        else:
            lines.append(f"  {' || '.join(assignments)}")

        return lines

    def _render_definitions(self):
        """Render shared finite bounds used by demo-oriented helpers.

        Keep numeric limits centralized so operation bounds and the
        animation budget use the same constants everywhere.
        """
        return [
            "DEFINITIONS",
            f"  MAX_AMOUNT == {self.demo_max_amount};",
            "  MIN_AMOUNT == -MAX_AMOUNT;",
            f"  MAX_STEPS == {self.demo_max_steps}",
        ]

    def _render_operation(self, event):
        """Render one DSL event as a classical B operation.

        Offensive style keeps all guards in the PRE clause. Defensive
        style keeps typing/demo executability in PRE and wraps the body
        in a top-level IF so violated contract guards become a no-op.
        """
        name = event["name"]
        explicit_params = event.get("params") or []
        guards = [
            self._as_b_predicate(self._safeify_bool_map_reads(self._safeify_zero_equality_guard(guard)))
            for guard in event.get("guards", [])
        ]
        actions = event.get("actions", [])
        params = explicit_params + self._context_params_for_event(guards, actions, explicit_params)

        signature = f"{name}({', '.join(param['name'] for param in params)})" if params else name
        lines = [f"  {signature} ="]

        preconditions = [self._param_type_condition(param) for param in params]
        for param in params:
            preconditions.extend(self._param_execution_bounds(param, guards))
        preconditions.append(f"{self.animation_steps_var} > 0")
        preconditions.extend(self._event_specific_demo_guards(name, params))
        guard_conditions = self._domain_guards_from_guards(guards)
        guard_conditions.extend(guards)
        if not self.defensive:
            preconditions.extend(guard_conditions)
        preconditions = self._deduplicate_in_order(preconditions)
        guard_conditions = self._deduplicate_in_order(guard_conditions)
        if not preconditions:
            preconditions = ["TRUE"]

        lines.append("    PRE")
        for i, condition in enumerate(preconditions):
            suffix = " &" if i < len(preconditions) - 1 else ""
            lines.append(f"      {condition}{suffix}")

        lines.append("    THEN")
        substitution_blocks = self._render_substitutions(actions, include_animation_budget=True)
        if self.defensive and guard_conditions:
            substitution_blocks = [
                self._render_defensive_guarded_body(guard_conditions, substitution_blocks)
            ]
        if substitution_blocks:
            for i, block in enumerate(substitution_blocks):
                suffix = ";" if i < len(substitution_blocks) - 1 else ""
                lines.extend(self._format_substitution_block(block, indent="      ", suffix=suffix))
        else:
            lines.append("      skip")
        lines.append("    END")
        return lines

    def _address_initialisation_invariant_predicates(self, binder_by_name, semantic_invariants):
        """Preserve simple address-distinctness invariants in ANY initialisation."""
        predicates = []
        seen = set()
        pattern = re.compile(r"^([A-Za-z_]\w*)\s*/=\s*([A-Za-z_]\w*)$")

        for invariant in semantic_invariants:
            match = pattern.match(invariant.strip())
            if not match:
                continue

            left_name, right_name = match.groups()
            left_binder = binder_by_name.get(left_name)
            right_binder = binder_by_name.get(right_name)
            if not left_binder or not right_binder:
                continue

            predicate = f"{left_binder} /= {right_binder}"
            if predicate in seen:
                continue
            seen.add(predicate)
            predicates.append(predicate)

        return predicates

    def _render_defensive_guarded_body(self, conditions, substitution_blocks):
        """Wrap contract guards in a top-level IF for defensive style."""
        if not conditions:
            return self._flatten_nested_blocks(substitution_blocks, indent="")

        lines = []
        for i, condition in enumerate(conditions):
            prefix = "IF " if i == 0 else "   "
            suffix = " &" if i < len(conditions) - 1 else ""
            lines.append(f"{prefix}{condition}{suffix}")
        lines.append("THEN")
        lines.extend(self._flatten_nested_blocks(substitution_blocks, indent="  "))
        lines.append("END")
        return lines

    def _render_substitutions(self, actions, include_animation_budget=False):
        """Render DSL actions as formatted B substitution blocks."""
        substitutions = []
        for action in actions:
            substitutions.append(self._render_action_substitution(action))

        if include_animation_budget:
            substitutions.append([f"{self.animation_steps_var} := {self.animation_steps_var} - 1"])

        return substitutions

    def _declaration_to_type_invariant(self, declaration):
        """Render the automatic type invariant for one declaration.

        Keep these machine-generated checks separate from user-written
        semantic invariants before the final INVARIANT clause is built.
        """
        return f"{declaration['name']} : {self._render_b_type(declaration['type'])}"

    def _render_sets(self, enum_declarations, declarations, events):
        """Render abstract and enumerated sets required by the machine."""
        sets = []
        if self._uses_address(declarations, events):
            sets.append("  ADDRESS")
        for enum_decl in enum_declarations:
            values = ", ".join(enum_decl["values"])
            sets.append(f"  {enum_decl['name']} = {{{values}}}")
        for i in range(len(sets) - 1):
            sets[i] = f"{sets[i]};"
        return sets

    def _render_b_type(self, type_spec):
        """Render one internal type node as classical B syntax.

        Recurse through map endpoints so nested structures stay aligned
        with the original DSL declaration.
        """
        kind = type_spec["kind"]
        if kind == "address":
            return "ADDRESS"
        if kind == "int":
            return "INTEGER"
        if kind == "nat":
            return "NATURAL"
        if kind == "bool":
            return "BOOL"
        if kind == "named":
            if type_spec["name"] in self.struct_types:
                return self._render_struct_type(type_spec["name"])
            return type_spec["name"]
        if kind == "map":
            from_type = self._render_b_type(type_spec["from"])
            to_type = self._render_b_type(type_spec["to"])
            if type_spec["to"]["kind"] == "map":
                to_type = f"({to_type})"
            return f"{from_type} +-> {to_type}"
        return "INTEGER"

    def _default_value_for_type(self, type_spec):
        """Choose an initial value compatible with the declared type.

        Start scalars at zero and maps as empty partial functions so the
        generated machine begins in a well-typed state.
        """
        kind = type_spec["kind"]
        if kind in {"int", "nat"}:
            return "0"
        if kind == "bool":
            return "FALSE"
        if kind == "named":
            values = self.enum_types.get(type_spec["name"])
            if values:
                return values[0]
            fields = self.struct_types.get(type_spec["name"])
            if fields:
                return self._default_record_for_fields(fields)
            return "{}"
        if kind == "map":
            return "{}"
        return "0"

    def _param_type_condition(self, param):
        """Render the PRE fragment that enforces a parameter type.

        Keep type membership separate from demo bounds because abstract
        sets such as ADDRESS do not use numeric ranges.
        """
        return f"{param['name']} : {self._render_b_type(param['type'])}"

    def _param_execution_bounds(self, param, guards=None):
        """Add finite bounds that keep ProB parameter search executable.

        Apply these bounds only to numeric types because abstract sets
        are already limited by their own membership checks.
        """
        name = param["name"]
        kind = param["type"]["kind"]
        refined_range = self._refined_numeric_param_range(name, kind, guards or [])
        if refined_range is not None:
            return [refined_range]
        if kind == "int":
            return [f"{name} : MIN_AMOUNT..MAX_AMOUNT"]
        if kind == "nat":
            return [f"{name} : 0..MAX_AMOUNT"]
        if kind == "named" and param["type"]["name"] in self.struct_types:
            return self._struct_param_execution_bounds(name, param["type"]["name"])
        return []

    def _refined_numeric_param_range(self, name, kind, guards):
        """Infer an exact finite interval from simple constant guards.

        When a parameter has both a constant lower and upper bound in
        the DSL guards, emit that direct interval instead of the wider
        shared demo clamp. This keeps generated B closer to the source
        intent for examples like voting's `candidate : 1..2`.
        """
        if kind not in {"int", "nat"}:
            return None

        pattern = re.compile(rf"^{re.escape(name)}\s*(>=|>|<=|<)\s*(-?\d+)\s*$")
        lower = 0 if kind == "nat" else None
        upper = None

        for guard in guards:
            match = pattern.match(guard.strip())
            if not match:
                continue

            operator, raw_value = match.groups()
            value = int(raw_value)

            if operator == ">=":
                lower = value if lower is None else max(lower, value)
            elif operator == ">":
                lower = value + 1 if lower is None else max(lower, value + 1)
            elif operator == "<=":
                upper = value if upper is None else min(upper, value)
            elif operator == "<":
                upper = value - 1 if upper is None else min(upper, value - 1)

        if lower is None or upper is None or lower > upper:
            return None

        return f"{name} : {lower}..{upper}"

    def _deduplicate_in_order(self, items):
        """Remove repeated conditions without reordering the PRE clause.

        Preserve the first occurrence so the final output remains stable
        and readable after inferred guards are merged in.
        """
        seen = set()
        deduped = []
        for item in items:
            if item in seen:
                continue
            seen.add(item)
            deduped.append(item)
        return deduped

    def _event_specific_demo_guards(self, event_name, params):
        """Inject guards that keep demo traces informative in ProB.

        Block self-transfer stuttering so animation steps do not get
        consumed by transitions that leave state unchanged.
        """
        param_names = {param["name"] for param in params}
        if event_name.lower() == "transfer" and {"sender", "receiver"}.issubset(param_names):
            # Avoid self-transfer stuttering during demo animation.
            return ["sender /= receiver"]
        return []

    def _uses_address(self, declarations, events):
        """Decide whether the machine needs the abstract `ADDRESS` set.

        Scan both state declarations and event parameters because either
        location can introduce address-typed values.
        """
        for decl in declarations:
            if self._type_contains_address(decl["type"]):
                return True
        for event in events:
            for param in event.get("params") or []:
                if self._type_contains_address(param["type"]):
                    return True
            if self._event_uses_context_identifier(event, "msg_sender"):
                return True
        return False

    def _type_contains_address(self, type_spec):
        """Detect ADDRESS recursively inside nested type structures.

        Catch map types whose domain or codomain uses address so the
        generated machine does not omit the abstract set declaration.
        """
        kind = type_spec["kind"]
        if kind == "address":
            return True
        if kind == "named" and type_spec["name"] in self.struct_types:
            return any(
                self._type_contains_address(field["type"])
                for field in self.struct_types[type_spec["name"]]
            )
        if kind == "map":
            return self._type_contains_address(type_spec["from"]) or self._type_contains_address(type_spec["to"])
        return False

    def _render_struct_type(self, name):
        """Render a DSL struct as a B record type."""
        fields = self.struct_types[name]
        rendered_fields = [
            f"{field['name']}: {self._render_b_type(field['type'])}"
            for field in fields
        ]
        return f"struct({', '.join(rendered_fields)})"

    def _default_record_for_fields(self, fields):
        """Render a B record literal using each field type's default value."""
        values = [
            f"{field['name']}: {self._default_value_for_type(field['type'])}"
            for field in fields
        ]
        return f"rec({', '.join(values)})"

    def _struct_param_execution_bounds(self, param_name, struct_name):
        """Bound numeric fields of struct parameters for ProB animation."""
        bounds = []
        for field in self.struct_types[struct_name]:
            field_type = field["type"]
            selector = f"{param_name}'{field['name']}"
            kind = field_type["kind"]
            if kind == "int":
                bounds.append(f"{selector} : MIN_AMOUNT..MAX_AMOUNT")
            elif kind == "nat":
                bounds.append(f"{selector} : 0..MAX_AMOUNT")
        return bounds

    def _event_uses_context_identifier(self, event, name):
        """Check whether an event body references one execution-context name."""
        haystacks = list(event.get("guards", []))
        for action in event.get("actions", []):
            haystacks.extend(self._action_text_fragments(action))
        return any(self._contains_identifier(text, name) for text in haystacks)

    def _context_params_for_event(self, guards, actions, explicit_params):
        """Add implicit B operation parameters for referenced context identifiers."""
        explicit_names = {param["name"] for param in explicit_params}
        fragments = list(guards)
        for action in actions:
            fragments.extend(self._action_text_fragments(action))

        params = []
        for name, type_spec in CONTEXT_PARAM_TYPES.items():
            if name in explicit_names:
                continue
            if any(self._contains_identifier(fragment, name) for fragment in fragments):
                params.append({"name": name, "type": type_spec})
        return params

    def _action_text_fragments(self, action):
        """Collect rendered condition and expression text from an action tree."""
        if action.get("kind") == "conditional":
            fragments = [action["condition"]]
            for child in action.get("then_actions", []):
                fragments.extend(self._action_text_fragments(child))
            for child in action.get("else_actions", []):
                fragments.extend(self._action_text_fragments(child))
            return fragments
        return [action.get("expr", ""), action.get("lvalue", {}).get("base", "")]

    def _contains_identifier(self, text, name):
        """Match identifiers without treating substrings as references."""
        return bool(re.search(rf"\b{re.escape(name)}\b", str(text)))

    def _as_b_predicate(self, expr):
        """Convert bool-valued B expressions into explicit predicates.

        Classical B separates boolean values from predicates, so a DSL
        guard like `not executed` must render as a B predicate.
        Use `not(expr = TRUE)` rather than `expr = FALSE` because ProB's
        classical B parser rejects `= FALSE` in PRE/IF predicate positions.
        Numeric comparisons and existing predicates are left unchanged.
        """
        text = str(expr).strip()
        if not text:
            return text
        if self._looks_like_predicate(text):
            return text
        inner = self._unwrap_not_call(text)
        if inner is not None:
            return f"not({inner} = TRUE)"
        if text in self.declared_types and self.declared_types[text]["kind"] == "bool":
            return f"{text} = TRUE"
        if self._looks_like_bool_map_read(text):
            return f"{text} = TRUE"
        return text

    def _looks_like_predicate(self, text):
        """Return True for expressions already rendered as B predicates."""
        predicate_markers = (
            " = ",
            " /= ",
            " < ",
            " <= ",
            " > ",
            " >= ",
            " : ",
            " & ",
            " or ",
            "=>",
        )
        return any(marker in text for marker in predicate_markers)

    def _unwrap_not_call(self, text):
        """Return the body of `not(...)` when it wraps the whole expression."""
        if not text.startswith("not(") or not text.endswith(")"):
            return None
        close_paren = self._find_matching_paren(text, 3)
        if close_paren != len(text) - 1:
            return None
        return text[4:-1].strip()

    def _looks_like_bool_map_read(self, text):
        """Detect totalized or direct reads from bool-valued maps."""
        for map_name in self._map_variable_names():
            type_spec = self.declared_types[map_name]
            if not self._map_returns_kind(type_spec, "bool"):
                continue
            if re.search(rf"\b{re.escape(map_name)}\s*\(", text):
                return True
            if f"<+ {map_name})" in text:
                return True
        return False

    def _is_map_variable(self, name):
        """Check whether a declared state variable is a map.

        Use this gate before map-specific rewrites so plain identifiers
        are not mistaken for partial functions.
        """
        type_spec = self.declared_types.get(name)
        return bool(type_spec and type_spec["kind"] == "map")

    def _is_numeric_map_variable(self, name):
        """Check whether a declared map returns numeric values.

        Restrict zero-default rewrites to numeric codomains because the
        fallback value `0` is meaningful only for numeric maps.
        """
        type_spec = self.declared_types.get(name)
        if not type_spec or type_spec["kind"] != "map":
            return False
        return type_spec["to"]["kind"] in {"int", "nat"}

    def _fresh_sigma_var(self, map_name):
        """Choose a helper name for generated `SIGMA` binders.

        Avoid collisions with declared state names so the rendered
        expression stays unambiguous to readers and tools.
        """
        candidate = f"{map_name}_k"
        if candidate in self.declared_types:
            return f"{candidate}_1"
        return candidate

    def _domain_checks_for_quantified_vars(self, quantified_vars, body):
        """Infer domain premises for quantified variables used in map access chains.

        Compensate for DSL invariants that quantify over a variable and
        then index a map without writing `x : dom(map)` explicitly.
        """
        checks_by_var = {var_name: [] for var_name in quantified_vars}
        seen = set()
        quantified_set = set(quantified_vars)

        for access in self._iter_map_accesses(body):
            current_map_expr = access["base"]
            current_map_type = self.declared_types[access["base"]]

            for index_expr in access["indices"]:
                if current_map_type["kind"] != "map":
                    break

                if index_expr in quantified_set:
                    candidate = f"{index_expr} : dom({current_map_expr})"
                    if candidate not in seen:
                        seen.add(candidate)
                        checks_by_var[index_expr].append(candidate)

                current_map_expr = self._render_totalized_map_read(
                    current_map_expr,
                    current_map_type,
                    index_expr,
                )
                current_map_type = current_map_type["to"]

        return checks_by_var

    def _domain_guards_from_guards(self, guards):
        """Infer PRE guards for direct map applications in guard text.

        Scan rendered guards for map calls that need `x : dom(map)` to
        be well-defined, while skipping `sum(map)` because its `SIGMA`
        binder is local to the expression.
        """
        domain_conditions = []
        seen = set()
        for guard in guards:
            for access in self._iter_map_accesses(guard):
                current_map_expr = access["base"]
                current_map_type = self.declared_types[access["base"]]

                for index_expr in access["indices"]:
                    if current_map_type["kind"] != "map":
                        break
                    candidate = f"{index_expr} : dom({current_map_expr})"
                    if candidate not in seen:
                        seen.add(candidate)
                        domain_conditions.append(candidate)
                    current_map_expr = self._render_totalized_map_read(
                        current_map_expr,
                        current_map_type,
                        index_expr,
                    )
                    current_map_type = current_map_type["to"]
        return domain_conditions

    def _render_action_substitution(self, action):
        """Render one action as a B substitution block."""
        action_kind = action.get("kind", "assign")
        if action_kind == "conditional":
            return self._render_conditional_substitution(action)
        if action_kind != "assign":
            raise ValueError(f"Unsupported action kind: {action_kind}")

        lvalue = action["lvalue"]
        base = lvalue["base"]
        indices = lvalue["indices"]
        expr = self._safeify_numeric_map_reads(action["expr"])

        if not indices:
            return [f"{base} := {expr}"]

        type_spec = self.declared_types.get(base)
        if not type_spec:
            raise ValueError(f"Cannot update undeclared variable '{base}'")

        updated_expr = self._build_nested_override(base, type_spec, indices, expr)
        return [f"{base} := {updated_expr}"]

    def _render_conditional_substitution(self, action):
        """Render an IF/THEN[/ELSE] block recursively."""
        lines = [f"IF {action['condition']} THEN"]
        then_blocks = self._render_substitutions(action.get("then_actions", []))
        lines.extend(self._flatten_nested_blocks(then_blocks, indent="  "))

        else_actions = action.get("else_actions", [])
        if else_actions:
            lines.append("ELSE")
            else_blocks = self._render_substitutions(else_actions)
            lines.extend(self._flatten_nested_blocks(else_blocks, indent="  "))

        lines.append("END")
        return lines

    def _format_substitution_block(self, block, indent, suffix=""):
        """Indent one block and attach its sequencing suffix."""
        if not block:
            return [f"{indent}skip{suffix}"]

        formatted = [f"{indent}{line}" for line in block]
        formatted[-1] = f"{formatted[-1]}{suffix}"
        return formatted

    def _flatten_nested_blocks(self, blocks, indent):
        """Render nested substitution blocks under IF/ELSE branches."""
        if not blocks:
            return [f"{indent}skip"]

        rendered = []
        for i, block in enumerate(blocks):
            suffix = ";" if i < len(blocks) - 1 else ""
            rendered.extend(self._format_substitution_block(block, indent=indent, suffix=suffix))
        return rendered

    def _build_nested_override(self, map_expr, map_type, indices, value_expr):
        """Build nested B map overrides for indexed assignment."""
        if map_type["kind"] != "map":
            raise ValueError(f"Too many indices for non-map target '{map_expr}'")
        if not indices:
            raise ValueError(f"Missing index for map target '{map_expr}'")

        head_index = indices[0]
        if len(indices) == 1:
            return f"{map_expr} <+ {{{head_index} |-> {value_expr}}}"

        inner_type = map_type["to"]
        if inner_type["kind"] != "map":
            raise ValueError(f"Too many indices for map target '{map_expr}'")

        current_inner = self._render_totalized_map_read(map_expr, map_type, head_index)
        updated_inner = self._build_nested_override(current_inner, inner_type, indices[1:], value_expr)
        return f"{map_expr} <+ {{{head_index} |-> ({updated_inner})}}"

    def _render_totalized_map_read(self, map_expr, map_type, index_expr):
        """Read through a default override so nested lookups stay defined."""
        if map_type["kind"] != "map":
            raise ValueError(f"Cannot index non-map expression '{map_expr}'")

        default_value = self._default_value_for_type(map_type["to"])
        return f"({{{index_expr} |-> {default_value}}} <+ {map_expr})({index_expr})"

    def _iter_map_accesses(self, expr):
        """Yield declared map access chains found in a rendered B expression."""
        accesses = []
        for map_name in self._map_variable_names():
            if self._guard_contains_map_sum(expr, map_name):
                continue
            pattern = re.compile(rf"\b{re.escape(map_name)}\s*\(")
            for match in pattern.finditer(expr):
                indices = []
                current_type = self.declared_types[map_name]
                cursor = match.end() - 1

                while current_type["kind"] == "map" and cursor < len(expr) and expr[cursor] == "(":
                    close_paren = self._find_matching_paren(expr, cursor)
                    if close_paren == -1:
                        break
                    index_expr = expr[cursor + 1 : close_paren].strip()
                    if not index_expr:
                        break

                    indices.append(index_expr)
                    current_type = current_type["to"]
                    cursor = close_paren + 1
                    while cursor < len(expr) and expr[cursor].isspace():
                        cursor += 1

                if indices:
                    accesses.append({"base": map_name, "indices": indices})
        return accesses

    def _map_variable_names(self):
        """Return the declared state variables whose type is a map.

        Centralize this lookup so all map-sensitive rewrites share the
        same source of truth.
        """
        return [name for name, type_spec in self.declared_types.items() if type_spec["kind"] == "map"]

    def _extract_calls(self, expr, function_name):
        """Collect the argument text from direct calls to one symbol.

        Use balanced-parenthesis matching so nested expressions inside
        the argument stay intact during extraction.
        """
        args = []
        pattern = re.compile(rf"\b{re.escape(function_name)}\s*\(")
        for match in pattern.finditer(expr):
            open_paren = match.end() - 1
            close_paren = self._find_matching_paren(expr, open_paren)
            if close_paren == -1:
                continue
            arg_expr = expr[open_paren + 1 : close_paren].strip()
            if arg_expr:
                args.append(arg_expr)
        return args

    def _find_matching_paren(self, text, open_paren_index):
        """Locate the closing parenthesis for one known opening index.

        Count nesting depth so inner calls do not confuse the substring
        extraction logic used by several regex-assisted helpers.
        """
        depth = 0
        for i in range(open_paren_index, len(text)):
            char = text[i]
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    return i
        return -1

    def _guard_contains_map_sum(self, guard, map_name):
        """Detect raw or rewritten `sum(map_name)` guard text.

        Use this to avoid leaking the generated `SIGMA` binder into the
        surrounding PRE clause, which ProB would read as a free variable.
        """
        raw_sum_pattern = re.compile(rf"\bsum\s*\(\s*{re.escape(map_name)}\s*\)")
        if raw_sum_pattern.search(guard):
            return True

        sigma_pattern = re.compile(
            rf"SIGMA\([^)]*\)\.\([^)]*: dom\({re.escape(map_name)}\) \| {re.escape(map_name)}\([^)]*\)\)"
        )
        return bool(sigma_pattern.search(guard))

    def _safeify_numeric_map_reads(self, expr):
        """Rewrite numeric map reads so absent keys behave like zero.

        Find candidate calls with regex, then replace from right to left
        so earlier offsets do not shift while later replacements are
        still pending.
        """
        replacements = []
        for map_name in self._map_variable_names():
            pattern = re.compile(rf"\b{re.escape(map_name)}\s*\(")
            for match in pattern.finditer(expr):
                type_spec = self.declared_types[map_name]
                indices = []
                current_type = type_spec
                cursor = match.end() - 1
                last_close = -1

                while current_type["kind"] == "map" and cursor < len(expr) and expr[cursor] == "(":
                    close_paren = self._find_matching_paren(expr, cursor)
                    if close_paren == -1:
                        break
                    index_expr = expr[cursor + 1 : close_paren].strip()
                    if not index_expr:
                        break

                    indices.append(index_expr)
                    last_close = close_paren
                    cursor = close_paren + 1
                    while cursor < len(expr) and expr[cursor].isspace():
                        cursor += 1
                    current_type = current_type["to"]

                if not indices or current_type["kind"] not in {"int", "nat"}:
                    continue

                replacement = map_name
                current_map_type = type_spec
                for index_expr in indices:
                    replacement = self._render_totalized_map_read(replacement, current_map_type, index_expr)
                    current_map_type = current_map_type["to"]
                replacements.append((match.start(), last_close + 1, replacement))

        if not replacements:
            return expr

        rendered = expr
        for start, end, replacement in sorted(replacements, key=lambda item: item[0], reverse=True):
            rendered = rendered[:start] + replacement + rendered[end:]
        return rendered

    def _safeify_zero_equality_guard(self, guard):
        """Rewrite `map(key) = 0` guards to use zero-default lookup.

        Treat absent numeric-map entries as zero so empty approval or
        flag maps can be queried before any explicit write occurs.
        """
        stripped = guard.strip()
        for map_name in self._map_variable_names():
            if not self._is_numeric_map_variable(map_name):
                continue
            prefix = f"{map_name}("
            if not stripped.startswith(prefix):
                continue

            close_paren = self._find_matching_paren(stripped, len(map_name))
            if close_paren == -1:
                continue

            key_expr = stripped[len(prefix):close_paren].strip()
            remainder = stripped[close_paren + 1 :].strip()
            if not key_expr or remainder != "= 0":
                continue

            return f"({{{key_expr} |-> 0}} <+ {map_name})({key_expr}) = 0"

        return guard

    def _safeify_bool_map_reads(self, expr):
        """Rewrite bool map reads so absent keys behave like FALSE.

        This keeps guards such as `not minted[token_id]` executable in
        ProB before a token id has been explicitly written.
        """
        replacements = []
        for map_name in self._map_variable_names():
            type_spec = self.declared_types[map_name]
            if not self._map_returns_kind(type_spec, "bool"):
                continue

            pattern = re.compile(rf"\b{re.escape(map_name)}\s*\(")
            for match in pattern.finditer(expr):
                indices = []
                current_type = type_spec
                cursor = match.end() - 1
                last_close = -1

                while current_type["kind"] == "map" and cursor < len(expr) and expr[cursor] == "(":
                    close_paren = self._find_matching_paren(expr, cursor)
                    if close_paren == -1:
                        break
                    index_expr = expr[cursor + 1 : close_paren].strip()
                    if not index_expr:
                        break

                    indices.append(index_expr)
                    last_close = close_paren
                    cursor = close_paren + 1
                    while cursor < len(expr) and expr[cursor].isspace():
                        cursor += 1
                    current_type = current_type["to"]

                if not indices or current_type["kind"] != "bool":
                    continue

                replacement = map_name
                current_map_type = type_spec
                for index_expr in indices:
                    replacement = self._render_totalized_map_read(
                        replacement,
                        current_map_type,
                        index_expr,
                    )
                    current_map_type = current_map_type["to"]
                replacements.append((match.start(), last_close + 1, replacement))

        if not replacements:
            return expr

        rendered = expr
        for start, end, replacement in sorted(replacements, key=lambda item: item[0], reverse=True):
            rendered = rendered[:start] + replacement + rendered[end:]
        return rendered

    def _map_returns_kind(self, type_spec, kind):
        """Check whether a possibly nested map ultimately returns a kind."""
        current_type = type_spec
        while current_type["kind"] == "map":
            current_type = current_type["to"]
        return current_type["kind"] == kind
