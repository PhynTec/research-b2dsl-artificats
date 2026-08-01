# DSL Core Spec

This file defines the DSL as a standalone language. It is intended as a handoff document for future parser, analyzer, and automation work.

## Language Design Goals

### 1. Security-focused

The DSL is designed to make security-relevant behavior explicit:

- persistent state is declared directly
- transition guards are visible as `where` clauses
- updates are explicit assignments
- implicit Solidity context such as `msg.sender` is normally made explicit

### 2. B-Method compatible

The DSL is intentionally simpler than Solidity and closer to mathematical state-transition modeling. In particular:

- numeric state is normalized into `int` and `nat`
- keyed storage is normalized into `map(...)`
- contract behavior is organized as guarded transitions

This makes the DSL a stable semantic middle-layer for the current formal-tooling pipeline.

### 3. SSA-friendly / IR-friendly

The DSL is not literally SSA form, but it is friendly to SSA-like or normalized IR pipelines because:

- compound updates can be desugared into explicit assignments
- guards are separated from updates
- conditional control flow is localized in `if ... then ... else ... end`
- state-changing behavior is concentrated inside `event` bodies

This makes the language a good target for future Slither-based automation.

### 4. Audit-oriented

The DSL is intended to help a reviewer answer:

- what state exists?
- what must always hold?
- which transitions are allowed?
- what does each transition update?

That is why the language prefers explicit structure over Solidity convenience features.

## Formal Grammar (EBNF)

The following EBNF reflects the current implemented DSL shape.

```ebnf
contract            = "contract", STRING, "{", { section }, "}" ;

section             = enum_declaration | struct_declaration
                    | state_section | invariants_section | event_declaration ;

enum_declaration    = "enum", identifier, "{", identifier, { ",", identifier }, [ "," ], "}" ;
struct_declaration  = "struct", identifier, "{", struct_field, { ";", struct_field }, [ ";" ], "}" ;
struct_field        = identifier, ":", type ;

state_section       = "state", ":", declaration, { declaration } ;
declaration         = identifier, ":", type ;

invariants_section  = "invariants", ":", expression, { ";", expression }, [ ";" ] ;

event_declaration   = "event", identifier, "(", [ parameter_list ], ")", "{",
                      body,
                      "}" ;

parameter_list      = parameter, { ",", parameter } ;
parameter           = identifier, ":", type ;

body                = { guard }, "do", ":", action_list, [ ";" ] ;
guard               = "where", expression, [ ";" ] ;

action_list         = action_item, { ",", action_item }, [ "," ] ;
action_item         = action | conditional_action ;

action              = lvalue, ":=", expression ;

conditional_action  = "if", expression, "then", action_list,
                      [ "else", action_list ],
                      "end" ;

lvalue              = identifier, { "[", expression, "]" } ;

expression          = quantified | comparison ;
quantified          = "forall", identifier_list, ".", expression ;
identifier_list     = identifier, { ",", identifier } ;

comparison          = logical_or, [ comparator, logical_or ] ;
comparator          = "==" | "!=" | ">=" | "<=" | ">" | "<" ;

logical_or          = logical_xor, { "or", logical_xor } ;
logical_xor         = logical_and, { "xor", logical_and } ;
logical_and         = logical_not, { "and", logical_not } ;
logical_not         = [ "not" ], arithmetic ;

arithmetic          = product, { ("+" | "-"), product } ;
product             = term, { ("*" | "/" | "%"), term } ;
term                = field_expression
                    | indexed_expression
                    | struct_literal
                    | function_call
                    | identifier
                    | number
                    | "true"
                    | "false"
                    | "(", expression, ")" ;

indexed_expression  = identifier, "[", expression, "]", { "[", expression, "]" } ;
field_expression    = (identifier | indexed_expression), ".", identifier, { ".", identifier } ;

struct_literal      = identifier, "{", struct_value, { ";", struct_value }, [ ";" ], "}" ;
struct_value        = identifier, ":", expression ;

function_call       = identifier, "(", [ argument_list ], ")" ;
argument_list       = expression, { ",", expression } ;

type                = basic_type | map_type | identifier ;
basic_type          = "address" | "int" | "nat" | "bool" ;
map_type            = "map", "(", type, "->", type, ")" ;

identifier          = NAME ;
number              = NUMBER ;
```

Practical syntax notes:

- `where` clauses appear before `do:`
- invariant expressions are separated by semicolons
- actions inside an event body are separated by commas
- a trailing comma at the end of an action list is allowed
- a trailing semicolon after the invariants list is allowed
- comments use `// ...`

Quantified variables range over finite domains inferred from their use. For
example, in `forall a . balances[a] >= 0`, `a` ranges over the finite key set
used for the `address` domain under the configured run bounds. If a quantified
variable cannot be tied to a map key, declared carrier, or compatible finite
type, the checker rejects the invariant.

## AST Definition

The DSL should be treated as a structured AST first and rendered as text second.

### Core node set

| Node | Fields | Meaning |
|---|---|---|
| `Contract` | `name, sections` | top-level contract model |
| `StateDecl` | `name, type` | state variable declaration |
| `Invariant` | `expr` | one invariant |
| `EventDecl` | `name, params, guards, actions` | one transition |
| `Param` | `name, type` | one event parameter |
| `GuardCondition` | `expr` | one `where` condition |
| `UpdateAction` | `target, expr` | one assignment |
| `ConditionalAction` | `cond, then_actions, else_actions` | one conditional branch |
| `MapIndex` | `base, indices` | indexed map read/write path |
| `BinaryExpr` | `op, left, right` | arithmetic or comparison |
| `QuantifiedExpr` | `vars, body` | quantified invariant |
| `FunctionExpr` | `name, args` | call such as `sum(balances)` |
| `TypeNode` | `kind, from_type?, to_type?` | scalar or map type |

### Nested-list view

```text
Contract(name)
|- StateDecl(name, type)
|- StateDecl(name, type)
|- Invariant(expr)
`- EventDecl(name)
   |- Param(name, type)
   |- Param(name, type)
   |- GuardCondition(expr)
   |- GuardCondition(expr)
   |- UpdateAction(target, expr)
   `- ConditionalAction(cond)
      |- then_actions: [ ... ]
      `- else_actions: [ ... ]
```

### Visual AST example

```text
Contract("AccessControl")
|
|- StateDecl(owner: address)
|- StateDecl(secret_value: int)
`- EventDecl("update_secret")
   |
   |- Param(new_val: int)
   |- Param(caller: address)
   |- GuardCondition(caller == owner)
   |- GuardCondition(new_val >= 0)
   `- UpdateAction(secret_value := new_val)
```

## Type System

### Scalar types

#### `address`

Meaning:

- abstract account or identity value

Typical source:

- Solidity `address`

Rules:

- comparable for equality/inequality
- not numeric
- may appear as map domain or codomain

#### `nat`

Meaning:

- mathematical natural number

Typical source:

- Solidity `uint`, `uint256`

Rules:

- may appear in arithmetic and comparisons
- may be assigned to `int`
- should be used where the model assumes non-negativity

#### `int`

Meaning:

- mathematical signed integer

Typical source:

- Solidity `int`, `int256`

Rules:

- may appear in arithmetic and comparisons
- can receive `nat` values
- used when negative intermediate or stored values may matter semantically

### Map types

Syntax:

```text
map(domain_type -> codomain_type)
```

Examples:

```dsl
balances: map(address -> nat)
owner: map(int -> address)
allowances: map(address -> map(address -> nat))
```

Rules:

- maps can be nested recursively in the grammar
- indexed access must use a key whose type matches the declared map domain
- the result type of indexing is the map codomain
- numeric map codomains are important because `sum(map)` only applies to maps whose codomain is `int` or `nat`

### Type compatibility rules

Current checking rules:

- exact type matches are allowed
- `nat -> int` assignment is allowed
- `int -> nat` assignment is not implicitly allowed
- map index type must match the map domain type
- comparison requires compatible operand types
- arithmetic requires numeric operands

### Boolean status

`bool` is a native DSL type. State variables, event parameters, struct fields,
and map codomains may use it. The literals are `true` and `false`, and boolean
expressions support `and`, `or`, `xor`, and `not`.

The B backend renders the type as `BOOL` and the literals as `TRUE` and
`FALSE`. Older examples may retain an intentional `0`/`1` abstraction, but new
boolean state should normally use the native type.

## Automation Roadmap (Slither)

This section describes the intended future bridge from Solidity analysis to DSL generation.

### Mapping SlithIR nodes to DSL nodes

The recommended strategy is:

1. analyze Solidity with Slither
2. extract normalized semantic operations
3. build DSL AST nodes
4. render DSL text only at the end

| SlithIR / semantic pattern | DSL node | Intent |
|---|---|---|
| storage write | `UpdateAction(target, expr)` | one state update |
| assignment | `UpdateAction(target, expr)` | preserve explicit assignment |
| compound update | `UpdateAction(target, BinaryExpr(...))` | desugar first |
| condition guarding execution | `GuardCondition(expr)` | emit `where` |
| require-like validation | `GuardCondition(expr)` | preserve enable-condition |
| branch | `ConditionalAction(cond, then, else)` | preserve local control flow |
| state variable metadata | `StateDecl(name, type)` | emit state section |
| parameter metadata | `Param(name, type)` | emit event signature |
| indexed storage access | `MapIndex(base, indices)` | preserve key path |
| inferred accounting invariant | `Invariant(expr)` | emit only if semantically justified |

Examples:

- `Assignment(variable, value)` -> `UpdateAction(target, expr)`
- `Condition(expr)` -> `GuardCondition(expr)`
- `Index(variable, key)` -> `MapIndex(base, [key])`
- `Binary(op, left, right)` -> `BinaryExpr(op, left, right)`

### Handling Solidity-specific sugar

#### Modifiers

Current rule:

- inline modifier logic into event guards when the modifier is semantically just a precondition

Warning:

- modifiers with side effects should not be flattened blindly

#### Inheritance

Current rule:

- flatten inherited state and externally relevant behavior conceptually before building the DSL model

Warning:

- do not preserve Solidity inheritance syntax directly in the DSL

#### `msg.sender`

Current rule:

- translate to the read-only DSL context identifier `msg_sender`; an explicit
  `caller` parameter remains available when the model intentionally treats the
  caller as ordinary input

#### `block.timestamp`

Current rule:

- translate to the read-only DSL context identifier `block_timestamp`, or use
  modeled time state when the model needs explicit control over time progress

#### Compound assignments

Current rule:

- desugar `+=` and `-=` into explicit DSL assignments

#### Constructor logic

Current rule:

- move durable constructor assumptions into invariants
- do not model constructors as runtime DSL events

## Known Constraints

This section records current language and implementation limits that future teams should respect.

### Language-level constraints

- no arrays
- no native modifier syntax
- no native constructor block
- no native event/log syntax
- Solidity context uses underscore-form DSL identifiers: `msg_sender`,
  `msg_value`, `block_number`, and `block_timestamp`
- DSL logical operators are `and`, `or`, `xor`, and `not`, rather than Solidity
  `&&`, `||`, and `!`
- only `sum(map)` is supported as a built-in function call form

### Type-checking constraints

- event parameters may not shadow state variables
- quantified variables must be inferrable from usage
- `sum(...)` requires a map with numeric codomain
- map indices must match declared domain types

### Backend-facing practical constraints

- the current grammar supports recursively nested maps
- the current checked corpus exercises nested maps up to two levels, for example `map(address -> map(address -> nat))`
- deeper nesting may parse and type-check, but it is less validated by the checked examples than one- and two-level cases
- numeric-map reads are treated with zero-default semantics by the current backend-oriented tooling
- generated workflows currently assume a finite demo-oriented step budget and bounded numeric parameter ranges in later formal backends

### Automation constraints

- full `.sol -> .dsl` conversion cannot be purely syntactic
- invariant promotion still requires semantic judgment
- unsupported Solidity mechanisms such as `delegatecall` should be abstracted only when the security meaning is clear

## Summary

The DSL is a small, security-oriented, map-friendly contract-modeling language. Its main strengths are:

- explicit state
- explicit guards
- explicit updates
- explicit invariants
- a simple enough structure to support future AST-driven or Slither-driven automation

Its main limitation is intentional: it is not a full Solidity clone. It is a semantic modeling language.
