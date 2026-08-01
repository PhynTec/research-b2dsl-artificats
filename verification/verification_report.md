# Verification Report

This report summarizes the checked-in ProB verification evidence for the two
baseline corpora used by the paper:

- the offensive-style machines in `examples/`
- the defensive-style machines in `examples/defensive/`

The benchmark grid uses three state limits: `100`, `1000`, and `5000`.

## Verification Summary

- Offensive top-level corpus (`examples/*.mch`): 13 models
- Defensive corpus (`examples/defensive/*.mch`): 13 models
- Combined baseline corpus: 26 generated B machines
- Benchmark rows: 78 runs, equal to 13 models x 2 policies x 3 state limits
- Cap hits: 7 runs, all at the `100`-state setting

The verifier configuration used bounded model checking with `-mc`, a 60 s
timeout, bounded numeric parameters in `[-100,100]`, a 12-step workflow budget,
and a ten-address carrier where a machine declares `ADDRESS`.

## Baseline Models

| Family | Offensive B | Defensive B |
| --- | --- | --- |
| `access_control` | `examples/access_control.mch` | `examples/defensive/access_control.mch` |
| `arithmetic_ops` | `examples/arithmetic_ops.mch` | `examples/defensive/arithmetic_ops.mch` |
| `auction` | `examples/auction.mch` | `examples/defensive/auction.mch` |
| `conditional_fee` | `examples/conditional_fee.mch` | `examples/defensive/conditional_fee.mch` |
| `context_access_control` | `examples/context_access_control.mch` | `examples/defensive/context_access_control.mch` |
| `erc20_full` | `examples/erc20_full.mch` | `examples/defensive/erc20_full.mch` |
| `escrow` | `examples/escrow.mch` | `examples/defensive/escrow.mch` |
| `loan_book` | `examples/loan_book.mch` | `examples/defensive/loan_book.mch` |
| `multisig` | `examples/multisig.mch` | `examples/defensive/multisig.mch` |
| `nft_sketch` | `examples/nft_sketch.mch` | `examples/defensive/nft_sketch.mch` |
| `simple_vault` | `examples/simple_vault.mch` | `examples/defensive/simple_vault.mch` |
| `token_state` | `examples/token_state.mch` | `examples/defensive/token_state.mch` |
| `voting` | `examples/voting.mch` | `examples/defensive/voting.mch` |

## Benchmark CSV

The machine-readable source of truth is `verification/benchmarks.csv`. Its
columns are:

```text
policy,contract,state_limit,time_seconds,passed,states_explored,cap_hit
```

The CSV contains all 78 baseline benchmark rows. The `cap_hit` column records
whether the explored-state count reached the configured state limit for that
row. A below-cap result is still bounded evidence only; it does not prove an
exhaustive search of the unbounded model.

## Test Report

The implementation test report is checked in as `verification/test_report.md`.
It records the local `python -m pytest` run over the included parser,
type-checker, generator, and verification-wrapper tests.
