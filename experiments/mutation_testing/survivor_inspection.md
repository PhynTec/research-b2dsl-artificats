# Survivor Inspection

Baseline run:

- State limit: 5000
- ADDRESS cardinality: 10
- Animation budget: generated default `MAX_STEPS == 12`
- Result: 20 mutants total, 8 killed, 12 survived
- Invariant checking is run separately from deadlock checking: the harness calls ProB with
  `-nodead -mc N` first, then runs `-cbc_deadlock`. This prevents terminal deadlocks from being
  reported before invariant exploration finishes.

Bound analysis:

- Increasing `-mc` to 20000 and ADDRESS to 20 killed 0 of 12 unresolved mutants.
- Increasing generated `MAX_STEPS` to 50 with `-mc 20000` and ADDRESS 10 killed 0 of 12 unresolved mutants.
- The deeper `MAX_STEPS` run timed out for all five ERC20 survivors, `nft/remove_transfer_owner_check`, and two multisig survivors; `auction/allow_non_improving_bid` reached the invariant state cap. This is useful evidence that deeper exploration is substantially more expensive.

Seeded ERC20 consistency check:

- The `remove_total_supply_update` operator now deletes the `total_supply := total_supply + amount`
  assignment rather than replacing it with `total_supply := total_supply`.
- The generated mutation machine and the original seeded
  `erc20_missing_mint_supply_update.mch` differ only in the machine name.
- With normal `-mc`, both machines report the expected 12-step budget deadlock before an invariant
  violation. With separated `-nodead -mc`, both reach the invariant state cap at 5,000 states.
- The old seeded result should therefore be read as a verification-detection result under combined
  deadlock/invariant checking, not as evidence that the current invariant-only pass finds the
  missing-supply violation at the same bound.

Targeted checks:

- Symbolic BMC (`-symbolic_model_check bmc`) was tried for the ERC20 mutants with relevant
  invariants, but ProB reported incomplete model checking.
- CBC (`-cbc mint` or `-cbc transfer_from`) was also tried for the relevant operation and timed out.
- These targeted diagnostics are recorded in `targeted_checks.csv` and are not counted in the main
  mutation score.

## Survivor Findings

| Model | Mutant | Reachable? | Semantic change? | Detecting invariant exists? | Larger `-mc` / ADDRESS killed it? | Interpretation |
| --- | --- | --- | --- | --- | --- | --- |
| erc20 | `remove_total_supply_update` | Likely yes: `mint(receiver, amount)` can choose positive `amount`. | Yes: receiver balance changes but `total_supply` does not. | Yes: `total_supply == sum(balances)` should detect positive mint. | No. Separate invariant checking reached the `-mc` cap; larger 20,000-state checks timed out. | Equivalent to the seeded missing-assignment machine except for machine name. Invariant exploration still does not reach the violating state within the tested cost envelope. Needs guided checking. |
| erc20 | `transfer_from_does_not_debit_owner` | Likely yes after mint/approve/transfer setup. | Yes: receiver can be credited without owner debit. | Yes: `total_supply == sum(balances)` should detect supply/balance mismatch. | No. Separate invariant checking reached the cap or timed out at larger bounds. | Meaningful mutant, but not killed within current explicit-state exploration. |
| erc20 | `allowance_increases_on_spend` | Likely yes after approve and transfer_from. | Yes: spending increases allowance. | No direct invariant captures monotonic allowance consumption. Existing invariant only checks allowances are non-negative. | No; invariant checking reached the cap at larger bounds. | This is mostly a specification gap. It needs a stronger safety property or event-level postcondition. |
| erc20 | `remove_owner_balance_guard` | Likely yes after allowance exists; generated B uses totalized map reads, so absent balance maps to 0. | Yes: transfer can subtract from a missing/zero owner balance. | Yes: balance type/invariant should reject negative balances. | No. Separate invariant checking reached the cap or timed out at larger bounds. | Meaningful mutant, but current search does not reach the violating state. |
| erc20 | `mint_subtracts_balance` | Likely yes: positive mint can subtract from a zero balance. | Yes: mint decreases receiver balance. | Yes: `balances : ADDRESS +-> NATURAL` and quantified non-negativity should detect it. | No; invariant checking reached the 20,000-state cap in the long run. | Meaningful mutant, but ERC20 search remains too large without guidance. |
| escrow | `refund_keeps_balance` | Yes: deposit then refund reaches refunded status with nonzero balance. | Yes: refunded escrow can retain funds. | No: current invariants only require distinct parties and `balance >= 0`. | No at `-mc 20000`, ADDRESS 20. No with `MAX_STEPS=50`. | True surviving mutant due to missing lifecycle invariant such as `status = Refunded => balance = 0`. |
| access_control | `remove_owner_check` | Yes: any caller can update a non-negative value. | Yes: authorization is removed. | No: current invariant only requires `secret_value >= 0`. | No at `-mc 20000`, ADDRESS 20. No with `MAX_STEPS=50`. | True surviving mutant due to missing authorization property. Invariant cannot distinguish authorized from unauthorized update. |
| nft | `remove_transfer_owner_check` | Likely yes after mint then transfer by a different sender. | Yes: unauthorized transfer is allowed. | No: there is no ownership authorization invariant. | No; separate invariant checking reached caps/timeouts. | Mostly a specification gap; deeper search is expensive, but no invariant states that only owners transfer. |
| nft | `mint_does_not_mark_token` | Yes: mint writes owner but leaves `minted[token_id] = false`. | Yes: token can be repeatedly minted. | No: current model has no invariant linking `owner` and `minted`. | No at `-mc 20000`, ADDRESS 20. No with `MAX_STEPS=50`. | True survivor due to missing consistency invariant such as `token_id : dom(owner) => minted[token_id] = TRUE`. |
| multisig | `allow_zero_threshold` | Yes: `set_required(0)` is allowed. | Yes: zero threshold is permitted. | Existing invariant only has `required >= 0`, so zero is allowed by the invariant. | No; ADDRESS 20 and `MAX_STEPS=50` increase cost but do not kill it. | True survivor due to weak invariant; add `required > 0` once configured, or model initialization separately. |
| multisig | `execute_below_threshold` | Yes: operation guard explicitly enables `sum(approved) < required`. | Yes: execution can happen before threshold. | No: no invariant says `executed => sum(approved) >= required`. | No; larger/deeper runs do not kill it and may timeout. | True survivor due to missing execution-safety invariant. |
| auction | `allow_non_improving_bid` | Yes: bid accepts any non-negative amount while open. | Yes: lower/equal bids can overwrite the highest bid. | No: invariants only constrain numeric non-negativity. | No; the deeper run reaches the invariant state cap. | True survivor due to missing monotonicity property for `highest_bid`. |

## Takeaway

The survivors split into two groups:

1. ERC20-style accounting/type mutants that appear semantically killable. Separating invariant checking from deadlock checking removes the terminal-deadlock preemption, but these checks still reach the state cap or timeout before finding the violation.
2. Authorization/lifecycle/monotonicity mutants that survive because the current DSL examples do not specify invariants strong enough to detect them.

The next best improvement is to add explicit safety invariants for the second group and add guided/deeper ProB checks for the first group.
