# Solidity to DSL Conversion Guide

This guide explains the transformation:

`Solidity (.sol) -> DSL (.dsl)`


The purpose of this document is to formalize the manual conversion logic already visible in the paired contracts under [`Solidity/`](../Solidity) and [`examples/`](../examples). 

## 1. Mindset & Design Philosophy

### 1.1 Conceptual shift

Solidity code is written for execution on the EVM. The DSL is written for modeling contract intent, state rules, and secure transitions.

So the conversion is not:

- opcode thinking
- ABI thinking
- gas thinking
- deployment-script thinking

It is:

- state modeling
- transition modeling
- explicit authorization modeling
- invariant modeling
- audit-oriented simplification

The central conversion question is:

> "What persistent state exists, what must always remain true, and under exactly which conditions may that state change?"

### 1.2 Core principles recovered from the example corpus

Across the corpus, the conversion style follows these principles:

1. Explicit over implicit.
   Solidity hides many assumptions inside defaults, execution context, and syntax sugar. The DSL makes them explicit.

2. Intent over mechanism.
   The DSL captures business logic and safety logic, not EVM machinery.

3. Guards are first-class.
   Solidity `require(...)` checks become visible DSL `where` clauses.

4. Authorization is made explicit.
   Solidity `msg.sender` becomes the typed, read-only DSL identifier
   `msg_sender`. Explicit parameters such as `caller` remain useful when caller
   identity is deliberately modeled as ordinary input.

5. Constructor logic becomes state assumptions.
   Constructor constraints are not kept as execution code. They are translated into state declarations and invariants.

6. Safety properties are promoted.
   Important properties that are only implicit in Solidity are often made explicit in DSL invariants.

7. Unsupported Solidity richness is abstracted, not copied blindly.
   If Solidity contains a feature outside the DSL subset, the correct move is to abstract it faithfully or mark it out of scope, not invent unsupported DSL syntax.

### 1.3 What the Solidity-to-DSL conversion is trying to preserve

The conversion should preserve:

- state structure
- authorization logic
- enable/disable conditions for actions
- arithmetic/accounting behavior
- branch behavior
- key security properties

The conversion does not try to preserve:

- gas costs
- ABI encoding details
- revert strings
- storage slot layout
- low-level EVM execution artifacts
- logging syntax

## 2. DSL Subset That the Solidity Conversion Targets

This section is included only to define the target language of the `.sol -> .dsl` conversion.

### 2.0 DSL Language Core Specification

This subsection is the source of truth for the DSL as a standalone target language. It is included so a future team can:

- write DSL files manually
- generate DSL from Solidity automatically
- build parsers or AST emitters for the DSL

### 2.1 Structural units used in the DSL

The current conversion targets these constructs:

| DSL construct | Role in conversion |
|---|---|
| `contract "Name"` | top-level contract model |
| `state:` | persistent contract storage |
| `invariants:` | properties that should always hold |
| `event name(...)` | one modeled state transition |
| `where expr` | guard/precondition |
| `do:` | state updates |
| `if ... then ... else ... end` | conditional update logic |

### 2.2 Types used in the DSL

| DSL type | Typical Solidity source |
|---|---|
| `address` | `address` |
| `int` | `int256`, `int` |
| `nat` | `uint256`, `uint` |
| `bool` | `bool` |
| named enum | Solidity `enum` |
| named struct | Solidity `struct` |
| `map(T1 -> T2)` | `mapping(K => V)` |

Nested mappings become nested maps, for example:

```solidity
mapping(address => mapping(address => uint256)) allowances;
```

becomes:

```dsl
allowances: map(address -> map(address -> nat))
```

### 2.3 Important target-language limits

The `.sol -> .dsl` conversion must respect the current DSL subset actually used in the repo:

- no arrays
- no native modifiers
- no native constructor block
- no native logs/events
- context identifiers use DSL spellings such as `msg_sender` and
  `block_timestamp`, not dotted Solidity member-access syntax

This matters because the conversion is not literal. It is constrained by what the DSL can express.

### 2.4 DSL Grammar Specification (EBNF)

The following EBNF defines the target DSL shape that the Solidity conversion must produce.

```ebnf
contract            = "contract", STRING, "{", { section }, "}" ;

section             = state_section | invariants_section | event_declaration ;

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

comparison          = arithmetic, [ comparator, arithmetic ] ;
comparator          = "==" | "!=" | ">=" | "<=" | ">" | "<" ;

arithmetic          = term, { ("+" | "-"), term } ;
term                = indexed_expression
                    | function_call
                    | identifier
                    | number
                    | "(", expression, ")" ;

indexed_expression  = identifier, "[", expression, "]", { "[", expression, "]" } ;

function_call       = identifier, "(", [ argument_list ], ")" ;
argument_list       = expression, { ",", expression } ;

type                = basic_type | map_type ;
basic_type          = "address" | "int" | "nat" ;
map_type            = "map", "(", type, "->", type, ")" ;

identifier          = NAME ;
number              = NUMBER ;
```

Practical writing rules for the next team:

- `where` clauses come before `do:`
- actions inside the `do:` block are comma-separated
- invariant expressions are semicolon-separated
- a trailing semicolon after the invariants list is allowed
- a trailing comma at the end of an action list is allowed
- event parameter types and state variable types use the same type grammar

### 2.5 DSL AST core nodes

For automation, the DSL should be thought of as an AST, not only as text. A minimal conceptual AST is:

| DSL AST node | Meaning |
|---|---|
| `Contract(name, sections)` | top-level model |
| `StateDecl(name, type)` | one persistent storage declaration |
| `Invariant(expr)` | one always-true property |
| `EventDecl(name, params, guards, actions)` | one transition |
| `Param(name, type)` | one event parameter |
| `GuardCondition(expr)` | one `where` clause |
| `UpdateAction(target, expr)` | one assignment |
| `ConditionalAction(cond, then_actions, else_actions)` | one branch |
| `MapIndex(base, indices)` | indexed lvalue or expression |
| `BinaryExpr(op, left, right)` | comparison or arithmetic |
| `QuantifiedExpr(kind, vars, body)` | quantified invariant |
| `FunctionExpr(name, args)` | call such as `sum(balances)` |

This is useful because a Slither-based generator should build these nodes first, then render DSL text second.

## 3. AST Extraction & Syntax Tree Mapping

### 3.1 Why AST-based conversion is necessary

A reliable `.sol -> .dsl` conversion should be AST-driven, not regex-driven.

Recommended parsing sources:

- `solc --ast-json`
- `@solidity-parser/parser`
- `tree-sitter-solidity`

### 3.2 AST workflow

Use this order:

1. Parse the Solidity file into an AST.
2. Find the target `ContractDefinition`.
3. Extract persistent state variables.
4. Extract constructor constraints.
5. Extract each state-changing function.
6. Inside each function:
   - collect parameters
   - collect authorization and validation guards
   - collect assignments
   - collect conditional branches
7. Normalize unsupported Solidity sugar into explicit forms.
8. Emit DSL sections in this order:
   - `contract`
   - `state`
   - `invariants`
   - `event`s

### 3.3 AST node to DSL mapping

| Solidity AST node | DSL target | Rule |
|---|---|---|
| `ContractDefinition` | `contract "Name"` | preserve the semantic contract name |
| `VariableDeclaration` (state) | `state` line | map supported Solidity type to DSL type |
| `Mapping` | `map(...)` | recursively convert key/value type |
| `FunctionDefinition` | `event` | convert externally meaningful state-changing function into one DSL event |
| `ParameterList` | event parameters | preserve names and mapped types |
| constructor | `state` + `invariants` | translate deployment assumptions into admissible state constraints |
| `require(...)` | `where` | keep condition, drop revert message |
| assignment | `:=` action | convert to explicit state update |
| compound assignment | `:=` action | desugar first |
| `IfStatement` | `if ... then ... else ... end` | preserve branch condition and branch updates |
| `IndexAccess` | `m[k]` | preserve map access shape |
| `MemberAccess(msg.sender)` | `msg_sender` | use the typed, read-only caller context |
| `MemberAccess(block.timestamp)` | `block_timestamp` or modeled state | use native context unless explicit time progression is required |
| `emit` | dropped | do not model as DSL syntax unless converted into state by design |

### 3.4 Slither IR to DSL AST mapping

If the next team automates `.sol -> .dsl` using Slither, they should not map Slither IR directly to strings first. They should map Slither IR into DSL AST nodes, then render the final DSL source.

| Slither IR / semantic pattern | DSL AST node | Conversion intent |
|---|---|---|
| state variable write | `UpdateAction(target, expr)` | convert one storage mutation into one DSL action |
| assignment `x = y` | `UpdateAction(target, expr)` | preserve explicit assignment |
| compound update `x += y` / `x -= y` | `UpdateAction(target, BinaryExpr(...))` | desugar before rendering |
| mapping write `m[k] = v` | `UpdateAction(MapIndex(...), expr)` | preserve indexed target |
| nested mapping write `m[a][b] = v` | `UpdateAction(MapIndex(...), expr)` | preserve full key path |
| condition used as transition gate | `GuardCondition(expr)` | convert enable-condition into `where` |
| require-like validation | `GuardCondition(expr)` | drop revert string, keep predicate |
| if-branch | `ConditionalAction(cond, then, else)` | preserve branch semantics |
| function parameter | `Param(name, type)` | explicit event input |
| state variable declaration | `StateDecl(name, type)` | explicit persistent state |
| recognized quantified/accounting invariant candidate | `Invariant(expr)` | promote semantic property when justified |

Examples of the intended mapping shape:

- `Assignment(variable, value)` -> `UpdateAction(target, expr)`
- `Condition(expr)` -> `GuardCondition(expr)`
- `Index(variable, key)` inside a write target -> `MapIndex(base, indices)`
- `Binary(op, left, right)` -> `BinaryExpr(op, left, right)`

### 3.5 Minimal AST example

From [`Solidity/access_control.sol`](../Solidity/access_control.sol):

```text
FunctionDefinition update_secret
|- ParameterList
|  |- VariableDeclaration new_val : int256
|  `- VariableDeclaration caller  : address
`- Block
   |- require(caller == owner)
   |- require(new_val >= 0)
   `- secret_value = new_val
```

becomes:

```dsl
event update_secret(new_val: int, caller: address) {
    where caller == owner
    where new_val >= 0
    do:
        secret_value := new_val
}
```

### 3.6 Visual AST diagram

This diagram shows the transformation at the tree level. The important point is that the conversion is semantic: Solidity nodes are reorganized into DSL state, parameter, guard, and action nodes.

```text
Solidity AST
============

ContractDefinition("AccessControl")
|
|- StateVariable(owner: address)
|- StateVariable(secret_value: int256)
`- FunctionDefinition("update_secret")
   |
   |- Parameter(new_val: int256)
   |- Parameter(caller: address)
   `- Block
      |
      |- Require(caller == owner)
      |- Require(new_val >= 0)
      `- Assign(secret_value = new_val)

              ||
              || semantic mapping
              \/

DSL AST
=======

Contract("AccessControl")
|
|- StateDecl(owner: address)
|- StateDecl(secret_value: int)
`- EventDecl("update_secret")
   |
   |- Param(new_val: int)
   |- Param(caller: address)
   |- Guard(caller == owner)
   |- Guard(new_val >= 0)
   `- Action(secret_value := new_val)
```

Reading rule:

- Solidity storage declarations become DSL state declarations.
- Solidity parameters become DSL event parameters.
- Solidity `require(...)` checks become DSL guards.
- Solidity assignments become DSL actions.
- Solidity machine-oriented type detail such as `int256` is normalized into DSL `int`.

## 4. Step-by-Step Solidity to DSL Conversion Workflow

### Step 1. Select the contract surface to model

Input:

- one Solidity file, possibly with helpers/imports/interfaces

Actions:

- identify the real stateful contract
- ignore test scaffolding and deployment scripts
- flatten inheritance conceptually if needed

Checkpoint:

- Enumerate the contract’s persistent storage and externally relevant actions

Common pitfalls:

- modeling interfaces instead of real behavior
- forgetting inherited state or modifier logic

### Step 2. Extract state variables

Input:

- Solidity contract storage declarations

Actions:

- collect each persistent state variable
- map each type into DSL type form
- rewrite unsupported state representations if needed

Checkpoint:

- every later state update has a declared DSL target

Example:

```solidity
mapping(address => uint256) public balances;
uint256 public total_supply;
```

becomes:

```dsl
state:
    balances: map(address -> nat)
    total_supply: nat
```

### Step 3. Convert constructor intent into invariants

Input:

- constructor parameters, constructor `require`s, constructor assignments

Actions:

- identify what the constructor is asserting about valid initial state
- move enduring conditions into `invariants`
- do not create a fake DSL constructor event

Example from [`Solidity/escrow.sol`](../Solidity/escrow.sol):

```solidity
require(initialBuyer != initialSeller, "buyer and seller must differ");
require(initialBuyer != initialBroker, "buyer and broker must differ");
require(initialSeller != initialBroker, "seller and broker must differ");
```

becomes:

```dsl
invariants:
    buyer != seller;
    buyer != broker;
    seller != broker
```

Checkpoint:

- constructor logic has been re-expressed as admissible state assumptions, not runtime behavior

Common pitfalls:

- copying constructor code literally
- losing role separation constraints

### Step 4. Convert each function into one DSL event

Input:

- each Solidity function that changes state

Actions:

- preserve the function name
- convert parameters to explicit DSL parameters
- keep only state-relevant behavior

Checkpoint:

- every meaningful state-changing function has a DSL event

Common pitfalls:

- trying to encode visibility keywords as DSL syntax
- keeping helper/view functions that do not matter to state behavior

### Step 5. Convert `require` checks into `where` guards

Input:

- function body

Actions:

- collect guard predicates
- drop revert messages
- keep the logical condition

Example:

```solidity
require(allowances[owner][spender] >= amount, "allowance too low");
require(balances[owner] >= amount, "balance too low");
```

becomes:

```dsl
where allowances[owner][spender] >= amount
where balances[owner] >= amount
```

Checkpoint:

- every enable/disable condition is visible in the DSL guard list

Common pitfalls:

- forgetting modifier-based checks
- keeping strings or EVM-specific revert detail

### Step 6. Convert assignments into explicit actions

Input:

- body statements after guard extraction

Actions:

- desugar compound updates
- convert assignments to `:=`
- preserve map index structure

Examples:

```solidity
balances[receiver] += amount;
total_supply += amount;
```

becomes:

```dsl
balances[receiver] := balances[receiver] + amount,
total_supply := total_supply + amount
```

Checkpoint:

- every state mutation is explicit and typed

Common pitfalls:

- forgetting to desugar `+=` / `-=`
- flattening nested mappings incorrectly

### Step 7. Convert conditional logic

Input:

- Solidity `if / else` branches

Actions:

- convert branch condition to DSL condition
- convert branch updates into DSL action lists

Example from [`Solidity/conditional_fee.sol`](../Solidity/conditional_fee.sol):

```solidity
if (amount > 10) {
    balance += amount - 1;
    fee_pool += 1;
} else {
    balance += amount;
}
```

becomes:

```dsl
if amount > 10 then
    balance := balance + (amount - 1),
    fee_pool := fee_pool + 1
else
    balance := balance + amount
end
```

Checkpoint:

- branch behavior is preserved without introducing unsupported syntax

### Step 8. Add semantic invariants that the Solidity code implies

Input:

- full state model + all event updates

Actions:

- promote important safety properties into explicit DSL invariants
- especially preserve accounting and domain properties

Common examples from the corpus:

- `total_supply == sum(balances)`
- `forall addr . balances[addr] >= 0`
- `executed >= 0; executed <= 1`
- role-distinctness constraints

Checkpoint:

- the DSL expresses not only updates but also the security expectations of the model

Common pitfalls:

- translating only syntax and losing the real contract property

## 5. Construct Mapping Reference

| Solidity construct | DSL equivalent | Transformation rule | Security meaning |
|---|---|---|---|
| storage variable | `state` declaration | map type into DSL subset | makes persistent assets/roles explicit |
| `mapping(K => V)` | `map(K -> V')` | convert recursively | preserves keyed ownership/accounting |
| constructor constraint | `invariants` | promote valid-initial-state assumption | keeps trusted setup visible |
| function | `event` | model one state transition | exposes transition surface |
| `require(cond, msg)` | `where cond` | drop message | keeps only semantic guard |
| `x += y` | `x := x + y` | desugar | explicit state update |
| `x -= y` | `x := x - y` | desugar | explicit state update |
| `m[k] = v` | `m[k] := v` | preserve indexing | explicit map mutation |
| nested mapping write | nested indexed lvalue | preserve full key path | explicit allowance/permission update |
| `if / else` | `if ... then ... else ... end` | preserve branch logic | branch conditions stay visible |
| `msg.sender` | `msg_sender` | translate dotted Solidity context to DSL context | typed, read-only authority source |
| `block.timestamp` | `block_timestamp` or modeled time | choose native context or explicit clock semantics | makes the time assumption reviewable |
| `emit` | omitted | drop unless intentionally modeled as state | logs are not core transition logic |

## 6. Special Conversion Patterns Seen in the Corpus

### 6.1 Access control pattern

Reference:

- [`Solidity/access_control.sol`](../Solidity/access_control.sol)
- [`examples/access_control.dsl`](../examples/access_control.dsl)

Pattern:

- `owner` is preserved as state
- caller identity is explicit
- owner check becomes `where caller == owner`

### 6.2 Time abstraction pattern

Reference:

- [`Solidity/auction.sol`](../Solidity/auction.sol)
- [`examples/auction.dsl`](../examples/auction.dsl)

Pattern:

- blockchain time is not kept as implicit environment state
- instead, time becomes explicit contract state: `current_time`
- time progress becomes its own modeled event: `tick()`

### 6.3 Native boolean pattern

Reference:

- [`Solidity/nft_sketch.sol`](../Solidity/nft_sketch.sol)
- [`examples/nft_sketch.dsl`](../examples/nft_sketch.dsl)

Pattern:

```solidity
mapping(int256 => bool) public minted;
```

becomes:

```dsl
minted: map(int -> bool)
```

with usage:

```dsl
where not minted[token_id]
...
minted[token_id] := true
```

### 6.4 Supply/accounting invariant pattern

Reference:

- [`Solidity/token_state.sol`](../Solidity/token_state.sol)
- [`examples/token_state.dsl`](../examples/token_state.dsl)

Pattern:

- Solidity updates imply conservation/accounting structure
- DSL makes that explicit:

```dsl
invariants:
    total_supply == sum(balances);
    forall addr . balances[addr] >= 0
```

### 6.5 Nested mapping pattern

Reference:

- [`Solidity/erc20_full.sol`](../Solidity/erc20_full.sol)
- [`examples/erc20_full.dsl`](../examples/erc20_full.dsl)

Pattern:

```solidity
mapping(address => mapping(address => uint256)) public allowances;
```

becomes:

```dsl
allowances: map(address -> map(address -> nat))
```

and:

```solidity
allowances[owner][spender] = amount;
```

becomes:

```dsl
allowances[owner][spender] := amount
```

## 7. Validation of the Solidity-to-DSL Conversion

This section is about validating the `.sol -> .dsl` result only.

### 7.1 Function-to-event equivalence check

For each Solidity function and corresponding DSL event, verify:

1. same logical purpose
2. same parameter meaning
3. same authorization conditions
4. same guard conditions
5. same state updates
6. same branch behavior

### 7.2 State-equivalence check

Verify that all important storage concepts from Solidity are present in DSL:

- balances
- allowances
- role addresses
- lifecycle flags
- counters
- deadlines

If a concept is missing, it must be either:

- intentionally abstracted
- intentionally dropped with justification

### 7.3 Security-equivalence check

Verify that the DSL still exposes:

- access control checks
- balance/allowance constraints
- one-time execution constraints
- lifecycle restrictions
- accounting properties

## 8. Unsupported Solidity Features and Correct Fallbacks

If a Solidity contract uses a feature the current DSL cannot express directly, apply this policy:

1. Preserve the security intent.
2. Replace the mechanism with explicit state + guards if possible.
3. Do not invent unsupported DSL syntax.
4. If faithful abstraction is impossible, mark the feature out of scope.

### Common unsupported features

- inline assembly
- `delegatecall`
- raw low-level `call`
- proxy routing logic
- arrays
- structs
- enums
- complex modifier side effects
- event logs as behavioral artifacts

## 8.5 Heuristics & Abstractions

This subsection records the manual decisions behind the current conversion style. It is meant to help the next team reproduce the same choices in an automated pipeline.

### Booleans

Current rule:

- translate Solidity `bool` state to native DSL `bool`

Example:

- `false -> false`
- `true -> true`

Use a numeric `0`/`1` abstraction only when a model intentionally needs
arithmetic encoding rather than boolean semantics.

### Boolean mappings

Current rule:

- convert `mapping(K => bool)` into `map(K -> bool)`

The backend renders this as a partial function to `BOOL` and totalizes missing
reads with `FALSE` where required by generated guards.

Example from the corpus:

- `not minted[token_id]` means "not minted yet"
- `minted[token_id] := true` means "minted"

### Arrays

Manual rule:

- if an array must be represented in the current DSL subset, flatten it into an index-keyed map such as `map(int -> T)` only when that abstraction is semantically faithful

Why:

- the DSL has maps but no native array syntax

Warning:

- do not flatten arrays blindly if array length, ordering, or dense-iteration semantics are security-relevant

### Implicit caller context

Current rule:

- translate `msg.sender` to the read-only DSL identifier `msg_sender`

The B backend exposes it as a typed operation parameter. An explicit
`caller`/`sender` parameter remains valid when that abstraction is intentional.

### Blockchain time

Current rule:

- translate `block.timestamp` to `block_timestamp` and `block.number` to
  `block_number`, or use modeled state when explicit clock progression matters

Why:

- native context is typed and read-only, while modeled state supports deliberate
  control of time progression

### Constructors

Manual rule:

- do not model constructors as runtime events
- lift durable constructor assumptions into invariants

Why:

- the DSL is centered on steady-state behavior and admissible state, not deployment procedure syntax

### Unsupported features

Manual rule:

- when a Solidity feature cannot be expressed faithfully, prefer explicit rejection or documented abstraction over fake syntax

Why:

- a semantically wrong DSL model is worse than an incomplete one

## 9. Future Roadmap: Automated Transpilation via Slither IR

This is a future direction for automating the `.sol -> .dsl` conversion. It does not replace the manual semantic method described above, but it could support it.

### 9.1 Why Slither IR is useful

A raw Solidity AST is excellent for structure, but some conversions become easier after semantic normalization. Slither IR can help expose:

- explicit read/write effects
- desugared assignments
- branch structure
- internal call flow
- storage access patterns

That makes it a good intermediate layer between Solidity syntax and the DSL model.

### 9.2 Proposed future pipeline

```text
Solidity source
   |
   v
Solidity AST
   |
   v
Slither IR
   |
   v
Normalized semantic model
   |
   +-> state inventory
   +-> event inventory
   +-> guard inventory
   +-> action inventory
   +-> invariant candidates
   |
   v
DSL AST
   |
   v
Rendered .dsl
```

### 9.3 What Slither IR could automate well

- detecting which state variables are read and written by each function
- desugaring `+=`, `-=`, and similar update forms
- extracting guard-like conditions before state transitions
- identifying nested mapping access paths
- extracting branch conditions and branch-local updates
- separating state-changing functions from helper/view functions

### 9.4 What still needs manual judgment

Even with Slither IR, some parts of the methodology remain semantic and should stay manually reviewed:

- deciding which implied properties should become DSL invariants
- deciding whether native context or an explicit input abstraction best matches
  the intended authority and time semantics
- deciding whether unsupported Solidity features should be abstracted or rejected
- deciding whether a constructor condition is a true invariant or only an initialization check

### 9.5 Recommended automation strategy

The safest long-term design is not one-click blind translation. It is:

1. automatic extraction of candidate state, guards, updates, and branches
2. rule-based conversion into a preliminary DSL AST
3. manual review of invariants and abstractions
4. final emission of the `.dsl` file

That matches the nature of this artifact: the conversion is semantic, not merely syntactic.

### 9.6 Design intent and downstream constraints

This guide is about `.sol -> .dsl`, but the DSL is also a middle-language inside the repository. That means future teams should not change the DSL carelessly.

Design intent:

- the DSL is simpler than Solidity
- the DSL is more explicit than Solidity
- the DSL uses mathematical modeling concepts such as `int`, `nat`, and `map(...)`
- the DSL is designed to be easy to inspect, reason about, and lower into later formal tooling

Practical constraint:

- choices such as `int`/`nat` normalization, explicit guards, and map-based state are not arbitrary style choices
- they are part of why the DSL works as a stable semantic middle-ground

Guidance for future changes:

- if the DSL syntax changes, the `.sol -> .dsl` automation rules must change with it
- prefer native `bool`, enum, struct, and context constructs over legacy manual
  encodings unless the abstraction is intentional and documented
- any future grammar extension should preserve the DSL’s role as a precise semantic representation rather than letting Solidity complexity leak in directly

## Final Rule

The `.sol -> .dsl` methodology is not a literal syntax translation.

It is a semantic modeling process:

- extract persistent state
- extract guards
- extract updates
- extract branch logic
- promote invariants
- translate supported EVM context into typed DSL context identifiers or an
  explicitly justified modeled input/state abstraction


