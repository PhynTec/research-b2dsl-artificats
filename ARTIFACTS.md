# Artifact Index

This artifact accompanies the current submission:

**From Smart-Contract Audit Rules to Classical B: A Typed DSL for Bounded Invariant Checking**

The repository is a public artifact. It contains the models, generated
machines, documentation, result files, verification scripts, and prototype
source needed to inspect the paper evidence.

## Contents

| Directory / file | Description |
| --- | --- |
| `manifest.csv` | Tabular map from paper examples and experiments to artifact files. |
| `manifest.json` | JSON version of the artifact manifest. |
| `docs/` | Public documentation for the DSL scope, semantics, and Solidity-to-DSL modeling rules. |
| `dsl/` | Parser grammar, type checker, and Classical B generator source. |
| `tests/` | Pytest implementation tests. |
| `scripts/` | Corpus regeneration helper script. |
| `Solidity/` | Simplified Solidity reference contracts used for manual modeling. |
| `examples/` | DSL examples and generated offensive Classical B machines. |
| `examples/defensive/` | Generated defensive Classical B machines. |
| `experiments/fault_injections/` | Seeded-fault Solidity/DSL/B examples and result matrices. |
| `experiments/mutation_testing/` | Mutation campaign outputs, generated mutants, and survivor analysis. |
| `verification/` | Verification scripts, checked-in report, benchmark CSV, and test report. |

## Excluded

The public artifact does not include internal development history, private
notes or local workspace files, temporary solver outputs, caches, or unrelated
experiments. The generated DSL/B models and result tables are the frozen
evidence used by the paper.

The absence of a Solidity file in the manifest means that the row is a
DSL-only feature example rather than a Solidity-derived contract.

## Key Files

| Topic | Files |
| --- | --- |
| DSL syntax, map semantics, definedness rules, limitations | `docs/DSL_CORE_SPEC.md` |
| Offensive vs defensive B-generation styles | `docs/b_style_comparison.md` |
| Solidity-to-DSL modeling guide | `docs/SOLIDITY_TO_DSL_CONVERSION_GUIDE.md` |
| ERC20-style Solidity reference | `Solidity/erc20_full.sol` |
| ERC20-style DSL/B case study | `examples/erc20_full.dsl`, `examples/erc20_full.mch`, `examples/defensive/erc20_full.mch` |
| BuggyVault worked example | `experiments/fault_injections/BuggyVault.sol`, `experiments/fault_injections/buggy_vault.dsl`, `experiments/fault_injections/buggy_vault.mch` |
| Baseline verification summary | `verification/verification_report.md` |
| Benchmark table | `verification/benchmarks.csv` |
| Implementation test report | `verification/test_report.md` |
| Seeded-fault matrix | `experiments/fault_injections/seeded_faults_separated_report.md`, `experiments/fault_injections/prob_matrix_results_separated.csv` |
| Mutation campaign | `experiments/mutation_testing/mutation_results.csv`, `experiments/mutation_testing/survivor_inspection.md` |

## ERC20-Style Example

The ERC20-style example is intentionally simplified. It is used to exercise
accounting and nested-map behavior, not to represent a production token.

Relevant files:

- `Solidity/erc20_full.sol`
- `examples/erc20_full.dsl`
- `examples/erc20_full.mch`
- `examples/defensive/erc20_full.mch`

The model contains balances, nested allowances, total supply, `mint`,
`approve`, `transfer_from`, and the accounting invariant:

```text
total_supply == sum(balances)
```

## Fault and Mutation Evidence

The seeded-fault material is in `experiments/fault_injections/`. It includes
the BuggyVault example mentioned in the paper, ERC20 missing-supply-update
fault, escrow missing-positive-deposit-guard fault, and access-control
missing-value-guard fault.

The mutation material is in `experiments/mutation_testing/`. It includes:

- `mutation_results.csv`
- `survivor_inspection.md`
- `survivor_bound_analysis.csv`
- `survivor_max_steps_analysis.csv`
- `targeted_checks.csv`
- generated mutant DSL/B files under `generated/`

Solver side files such as `.prob` and `.out` are not included because they are
temporary local outputs.

## Limits of the Artifact

This artifact supports inspection of the paper evidence, but it is not:

- a public release of the full prototype implementation;
- a verified Solidity compiler;
- a full Solidity/EVM semantics;
- a proof that the Solidity references are production-safe.

The results should be read as bounded audit evidence over generated B machines.
