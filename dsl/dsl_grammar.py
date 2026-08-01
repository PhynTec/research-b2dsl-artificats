"""
DSL grammar definition for the prototype smart-contract language.

This module exposes a single `grammar` string consumed by Lark (LALR parser)
to parse contracts into a syntax tree before B-machine generation.
"""

# Key grammar structure (high-level):
# - `start` and `contract`: enforce one contract per DSL file.
# - `state_section`, `invariants_section`, `event_section`: define major blocks.
# - `declaration` and `type`: capture typed state variables.
# - `event_decl`, `guard_list`, `action_list`: model transition rules.
# - `expr` family: supports logical/arithmetic/comparison/quantified expressions.
grammar = r"""
    start: contract

    // The contract body contains an optional ordered list of sections.
    contract: _CONTRACT STRING "{" [section_list] "}"

    // A section can define enums, structs, state variables, invariants, or events.
    section_list: (enum_decl | struct_decl | state_section | invariants_section | event_section)*

    enum_decl: _ENUM NAME "{" enum_value_list "}"
    enum_value_list: NAME ("," NAME)* ","?

    struct_decl: _STRUCT NAME "{" struct_field_list "}"
    struct_field_list: struct_field (";" struct_field)* ";"?
    struct_field: identifier_name ":" type

    state_section: _STATE ":" declaration_list
    invariants_section: _INVARIANTS ":" expr_list
    event_section: event_decl

    // Each state declaration binds an identifier to a DSL type.
    declaration_list: declaration+
    declaration: identifier_name ":" type

    expr_list: expr (";" expr)* ";"?

    // Event signature and body (guards + actions).
    event_decl: _EVENT NAME "(" [param_list] ")" "{" body "}"
    param_list: param ("," param)*
    param: identifier_name ":" type

    // Transition body: optional guards, then one or more actions/substitutions.
    body: guard_list _DO ":" action_list ";"?
    guard_list: (_WHERE expr ";"?)*
    action_list: action_item ("," action_item)* ","?
    ?action_item: action
                | conditional_action
    action: lvalue _BECOMES expr
    conditional_action: _IF expr _THEN action_list (_ELSE action_list)? _END

    // L-value indexing allows map updates such as balances[addr] := ...
    lvalue: identifier_name index*
    index: "[" expr "]"

    // Expressions: quantified, logical, arithmetic, or comparison forms.
    ?expr: quantified
         | xor_expr

    quantified: _FORALL name_list "." expr
    name_list: NAME ("," NAME)*

    ?xor_expr: or_expr
             | xor_expr _XOR or_expr         -> logical_xor
    ?or_expr: and_expr
            | or_expr _OR and_expr           -> logical_or
    ?and_expr: not_expr
             | and_expr _AND not_expr        -> logical_and
    ?not_expr: _NOT not_expr                  -> logical_not
             | comparison

    ?comparison: arithmetic ((EQEQ | NEQ | GTE | LTE | GT | LT) arithmetic)?
    ?arithmetic: product ((PLUS | MINUS) product)*
    ?product: term ((STAR | SLASH | PERCENT) term)*
    ?term: field_expr
         | indexed_expr
         | struct_literal
         | function_call
         | context_identifier
         | NAME
         | NUMBER
         | _TRUE                             -> true_literal
         | _FALSE                            -> false_literal
         | "(" expr ")"

    field_expr: field_base field_access+
    ?field_base: indexed_expr | NAME
    field_access: "." NAME

    ?identifier_name: NAME | context_identifier
    context_identifier: MSG_SENDER | MSG_VALUE | BLOCK_NUMBER | BLOCK_TIMESTAMP

    struct_literal: NAME "{" struct_value_list "}"
    struct_value_list: struct_value (";" struct_value)* ";"?
    struct_value: NAME ":" expr

    indexed_expr: NAME index+
    function_call: NAME "(" [arg_list] ")"
    arg_list: expr ("," expr)*

    // Supported built-in DSL types, including recursively nested maps.
    ?type: basic_type
         | map_type
         | NAME                 -> named_type

    ?basic_type: _ADDRESS           -> address_type
               | _INT               -> int_type
               | _NAT               -> nat_type
               | _BOOL              -> bool_type

    map_type: _MAP "(" type _ARROW type ")"

    _CONTRACT.10: "contract"
    _STATE.10: "state"
    _INVARIANTS.10: "invariants"
    _EVENT.10: "event"
    _ENUM.10: "enum"
    _STRUCT.10: "struct"
    _WHERE.10: "where"
    _DO.10: "do"
    _FORALL.10: "forall"
    _IF.10: "if"
    _THEN.10: "then"
    _ELSE.10: "else"
    _END.10: "end"
    _MAP.10: "map"
    _ADDRESS.10: "address"
    _INT.10: "int"
    _NAT.10: "nat"
    _BOOL.10: "bool"
    _TRUE.10: "true"
    _FALSE.10: "false"
    _NOT.10: "not"
    _AND.10: "and"
    _OR.10: "or"
    _XOR.10: "xor"
    MSG_SENDER.10: "msg_sender"
    MSG_VALUE.10: "msg_value"
    BLOCK_NUMBER.10: "block_number"
    BLOCK_TIMESTAMP.10: "block_timestamp"

    EQEQ: "=="
    NEQ: "!="
    GTE: ">="
    LTE: "<="
    GT: ">"
    LT: "<"
    PLUS: "+"
    MINUS: "-"
    STAR: "*"
    SLASH: "/"
    PERCENT: "%"
    _ARROW: "->"
    _BECOMES: ":="

    %import common.CNAME -> NAME
    %import common.INT -> NUMBER
    %import common.ESCAPED_STRING -> STRING
    %import common.WS
    %ignore WS
    // Ignore single-line comments in DSL source files.
    %ignore /\/\/[^\n]*/
"""
