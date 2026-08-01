# DSL and ProB Example Corpus

This directory contains the repository's checked-in DSL examples and their
generated classical B machines. Each `examples/*.dsl` source has:

- an offensive-style `examples/*.mch` snapshot, where contract guards remain
  in operation `PRE` clauses;
- a defensive-style `examples/defensive/*.mch` snapshot, where contract guards
  are evaluated inside top-level `IF` substitutions;
- checked-in generated machines corresponding to the paper artifact;
- ProB model-checking and deadlock-checking results summarized in
  `verification/verification_report.md`.

The generator implementation is not included in the public artifact. The files
in this directory are the generated snapshots used for the paper.

## Corpus Overview

### `access_control.dsl`

Models an owner-controlled state update. Its guard ensures that only the stored
owner can change the protected value.

### `arithmetic_ops.dsl`

Provides regression coverage for multiplication, integer division, and
modulo. The generated B machine renders `%` as the Classical B `mod` operator,
and the positive-divisor guard keeps division and modulo defined.

### `auction.dsl`

Models a time-bounded auction with a monotonically advancing clock and guards
that reject late or non-improving bids.

### `conditional_fee.dsl`

Exercises `if/then/else/end` generation by routing a deposit through either a
fee-charging branch or a direct-balance branch.

### `context_access_control.dsl`

Exercises execution-context identifiers. It reads `msg_sender` and
`block_timestamp` without declaring them as DSL event parameters; the B backend
adds them as typed operation parameters.

### `erc20_full.dsl`

Exercises nested owner/spender maps, multi-variable quantified invariants,
`sum(map)`, nested map updates, and conditional transfer behavior.

### `escrow.dsl`

Exercises enums. The lifecycle state has type `Status`, with the named
values `Pending`, `Funded`, `Released`, and `Refunded`; the generated B machine
uses an enumerated set rather than integer status codes.

### `loan_book.dsl`

Exercises named structs, record literals, record field access, and maps whose
values are records.

### `multisig.dsl`

Models per-signer approvals, a positive execution threshold, and a native
boolean `executed` flag that prevents repeated execution.

### `nft_sketch.dsl`

Models token ownership and a `map(int -> bool)` minted registry. The boolean map
prevents duplicate minting before ownership transfers are considered.

### `simple_vault.dsl`

Models deposits, withdrawals, accounting invariants, and a bounded pause-state
encoding in a compact vault example.

### `token_state.dsl`

Models fungible-token balances, minting, transfers, and the invariant that the
sum of account balances equals total supply.

### `voting.dsl`

Models a two-candidate tally. It retains its compact arithmetic update encoding
as a useful example even though conditional actions are now supported.

## Generated-Machine Conventions

The transpiler adds a bounded `anim_steps_left` execution budget and finite
ranges for numeric operation parameters. These bounds make the examples
practical to animate and model-check in ProB; they are verification harness
constraints, not part of the source-level smart-contract semantics.

Transfer-shaped operations also receive a non-self-transfer guard where needed
to avoid consuming animation steps on stuttering transitions. Numeric map reads
are totalized with a zero default, while boolean map reads use `FALSE` as their
default.

## Current Scope

The corpus now covers native booleans, structs, enums, nested maps, full numeric
arithmetic, conditional actions, quantified invariants, aggregation, and
execution-context identifiers through generated B and ProB verification.

The project still intentionally excludes full Solidity semantics. Inheritance,
arbitrary external calls, low-level EVM behavior, emitted logs, and arrays
without a deliberate abstraction require manual modeling or future compiler
work.
