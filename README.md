# CRiSIS 2026 Artifact: Smart-Contract DSL to Classical B

This repository is the public artifact for the paper:

**From Smart-Contract Audit Rules to Classical B: A Typed DSL for Bounded Invariant Checking**

It contains the DSL models, generated Classical B machines, Solidity reference
examples, bounded verification reports, benchmark tables, test report, and the
prototype scripts/source needed to inspect the paper evidence.

## What Is Included

Most baseline examples have a corresponding simplified Solidity reference in
`Solidity/`. A few examples are DSL-only feature checks rather than
Solidity-derived contracts: `arithmetic_ops`, `context_access_control`, and
`loan_book`.

## What Is Included

```text
ARTIFACTS.md                     concise artifact index
manifest.csv                     table mapping paper examples to artifact files
manifest.json                    JSON version of the same manifest
docs/                            public design/semantics documentation
dsl/                             parser grammar, type checker, and B generator source
tests/                           pytest implementation tests
scripts/                         corpus regeneration helper
Solidity/                        simplified Solidity reference contracts
examples/                        DSL models and generated offensive B machines
examples/defensive/              generated defensive B machines
experiments/fault_injections/    seeded-fault models and result matrices
experiments/mutation_testing/    mutation campaign outputs and generated mutants
verification/                    verification scripts, reports, benchmark CSV, test report
```

## What Is Not Included

This artifact does not include private notes, local caches, temporary solver
side files, unrelated experiments, or the internal development history.

## ERC20-Style Case Study

The ERC20-style example in the paper is represented by:

- Solidity reference: `Solidity/erc20_full.sol`
- DSL model: `examples/erc20_full.dsl`
- offensive B machine: `examples/erc20_full.mch`
- defensive B machine: `examples/defensive/erc20_full.mch`

This is a simplified reference contract, not a production ERC20
implementation and not an OpenZeppelin contract.

## Main Paper Evidence

| Paper material | Artifact files |
| --- | --- |
| Artifact manifest | `manifest.csv`, `manifest.json` |
| DSL syntax and modeling scope | `docs/DSL_CORE_SPEC.md` |
| Map semantics, binder behavior, and definedness notes | `docs/DSL_CORE_SPEC.md`, `docs/b_style_comparison.md` |
| Solidity-to-DSL manual modeling rules | `docs/SOLIDITY_TO_DSL_CONVERSION_GUIDE.md` |
| Offensive and defensive B styles | `docs/b_style_comparison.md`, `examples/*.mch`, `examples/defensive/*.mch` |
| ERC20 nested-map case study | `Solidity/erc20_full.sol`, `examples/erc20_full.dsl`, `examples/erc20_full.mch` |
| BuggyVault worked example | `experiments/fault_injections/BuggyVault.sol`, `experiments/fault_injections/buggy_vault.dsl`, `experiments/fault_injections/buggy_vault.mch` |
| Baseline verification and benchmark results | `verification/verification_report.md`, `verification/benchmarks.csv`, `verification/test_report.md` |
| Prototype implementation checks | `dsl/`, `tests/`, `verification/test_report.md` |
| Seeded-fault matrix | `experiments/fault_injections/seeded_faults_separated_report.md`, `experiments/fault_injections/prob_matrix_results_separated.csv` |
| Mutation campaign | `experiments/mutation_testing/mutation_results.csv`, `experiments/mutation_testing/survivor_inspection.md`, `experiments/mutation_testing/generated/` |

## Result Interpretation

The verification results are bounded audit evidence. A clean bounded run means
that no violation was found under the configured bounds. It is not a proof of
deployment correctness.

The Solidity files are reference inputs used to explain the manual modeling
process. The paper and artifact do not claim full Solidity or EVM semantic
equivalence.

## Limitations

- The DSL is a semantic modeling language, not a full Solidity clone.
- Solidity-to-DSL modeling is manual for the paper claims.
- Translation correctness is tested and reviewed in the development prototype,
  but not mechanically proved in this artifact.
- Bounded ProB runs can be inconclusive under search, state, or time limits.
- Reentrancy, low-level calls, gas, event logs, inheritance details, arrays, and
  full EVM behavior are outside the implemented scope unless manually
  abstracted.
