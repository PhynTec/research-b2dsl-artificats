# Seeded Fault Matrix: Separated Invariant/Deadlock Workflow

This rerun uses the same three seeded smart-contract faults as the original matrix, but replaces the
older combined verification wrapper with the separated workflow used by the semantic mutation
campaign.

## Workflow

For each seeded `.mch` machine and each bound configuration:

1. run invariant/assertion model checking with `probcli <machine> -card ADDRESS N -nodead -mc LIMIT`;
2. if invariant checking does not kill the mutant, run deadlock checking separately with
   `probcli <machine> -card ADDRESS N -cbc_deadlock`;
3. classify expected terminal or animation-budget deadlocks as non-killing outcomes;
4. classify state-limit exhaustion during invariant checking as `Capped`, not `pass`.

The full rerun is recorded in `prob_matrix_results_separated.csv`.

## Experimental Setup

- OS: Microsoft Windows 11 Home Single Language, version 10.0.26200, build 26200
- Machine: Lenovo 83EM, x64-based PC
- CPU: 13th Gen Intel(R) Core(TM) i7-13620H, 16 logical processors
- RAM: 16,077 MB physical memory
- ProB: ProB CLI 1.13.0-final, SICStus Prolog 4.8.0
- ProB search strategy: default `-mc` strategy, reported by ProB help as mixed breadth-first/depth-first. No `-bf`, `-df`, or `-mc_mode` override was used.
- Timeout: 60 seconds per ProB command
- State limits: 100, 1000, 5000
- ADDRESS cardinalities: 2, 5, 10

## Results

Across 27 configurations:

- 24 configurations were killed;
- 21 were killed by invariant violations;
- 3 were killed by initialization failure;
- 3 were capped during invariant checking;
- 0 timed out.

Per model:

| Model | Configurations | Killed | Capped | Main reason |
| --- | ---: | ---: | ---: | --- |
| `access_control_missing_value_guard` | 9 | 9 | 0 | Removing the non-negative value guard violates `secret_value >= 0`. |
| `escrow_missing_positive_deposit_guard` | 9 | 9 | 0 | ADDRESS cardinality 2 makes distinct-party initialization impossible; larger cardinalities expose `balance >= 0` violations. |
| `erc20_missing_mint_supply_update` | 9 | 6 | 3 | ADDRESS 2 and 5 expose `total_supply == sum(balances)` violations; ADDRESS 10 reaches the invariant state cap at all three state limits. |

## Difference From The Older Matrix

The older seeded matrix used a combined wrapper that ran normal `-mc` and reported the first failing
condition it observed. That allowed expected terminal deadlocks to interact with invariant
exploration and produced the earlier ERC-20 address-cardinality-10 observations, including the
length-13 trace after 272 or 478 states.

With the separated workflow, invariant checking is run as `-nodead -mc LIMIT`. For the ERC-20
missing-supply fault at ADDRESS cardinality 10, this invariant-only search reaches the configured
state cap at 100, 1000, and 5000 states without reporting the violating trace. Deadlock checking then
reports only the expected terminal animation-budget deadlock, so these rows are classified as
`Capped` rather than killed.
