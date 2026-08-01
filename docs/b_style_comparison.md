# Defensive vs Offensive B Generation

## Purpose

The artifact contains both classical B generation styles that show
up in the project papers:

- offensive style, where contract guards live in the `PRE` clause
- defensive style, where contract guards move into a top-level
  `IF ... THEN ... END` inside the operation body

Both encodings are valid classical B. The main tradeoff is what happens
when a caller proposes parameters that do not satisfy the contract
guard. Offensive style makes the operation unavailable. Defensive style
keeps the operation callable for well-typed parameters, but turns the
step into an explicit no-op when the guard is false.

## Side-by-side transfer example

The `TokenState` example is a good comparison point because its
`transfer` event has the usual token guard structure: well-typed
participants, a positive amount, and a sufficient-balance check.

### Offensive style

```b
transfer(sender, receiver, amount) =
  PRE
    sender : ADDRESS &
    receiver : ADDRESS &
    amount : INTEGER &
    amount : MIN_AMOUNT..MAX_AMOUNT &
    anim_steps_left > 0 &
    sender /= receiver &
    sender : dom(balances) &
    balances(sender) >= amount &
    amount > 0
  THEN
    balances := balances <+ {sender |-> ({sender |-> 0} <+ balances)(sender) - amount};
    balances := balances <+ {receiver |-> ({receiver |-> 0} <+ balances)(receiver) + amount};
    anim_steps_left := anim_steps_left - 1
  END
```

### Defensive style

```b
transfer(sender, receiver, amount) =
  PRE
    sender : ADDRESS &
    receiver : ADDRESS &
    amount : INTEGER &
    amount : MIN_AMOUNT..MAX_AMOUNT &
    anim_steps_left > 0 &
    sender /= receiver
  THEN
    IF sender : dom(balances) &
       balances(sender) >= amount &
       amount > 0
    THEN
      balances := balances <+ {sender |-> ({sender |-> 0} <+ balances)(sender) - amount};
      balances := balances <+ {receiver |-> ({receiver |-> 0} <+ balances)(receiver) + amount};
      anim_steps_left := anim_steps_left - 1
    END
  END
```

## What changed mechanically

The new `--defensive` flag only changes how contract guards are placed.
The generated machine still keeps:

- typed parameters in the `PRE` clause
- finite numeric parameter bounds used for ProB execution
- the animation-step budget guard used to keep the corpus finite

The contract-specific conditions from DSL `where` clauses move into the
body-level `IF`, together with any inferred domain checks needed to make
map reads well-defined. That means a bad balance check or a non-positive
amount no longer causes a `PRE` failure in defensive mode; the body
simply does nothing.

## Behavioral difference during analysis

In offensive style, disabled operations are easy to inspect because the
whole contract guard is visible as the operation precondition. That is
useful when the downstream tool or proof workflow reasons directly about
operation enablement. It also matches the usual classical-B reading of
"this operation may only execute when these predicates hold."

In defensive style, the machine is often friendlier to workflows that
want totalized operations or explicit no-op behavior. A caller can still
propose a well-typed operation instance even when the semantic guard is
false, and the resulting machine step is just inert. This is closer to
how some defensive smart-contract encodings are presented in the
literature, where failed runtime checks are modeled as benign stuttering
instead of as precondition violations.

That difference matters during verification and animation. In offensive
style, a rejected call is absent from the enabled-transition set, so the
analysis question is "when is this operation enabled?" In defensive
style, the call may still appear as a well-typed step, but its effect is
`skip` when the semantic guard is false, so the analysis question becomes
"when does this step actually change state?" Neither encoding is more
correct in the abstract; they simply expose different proof and
inspection viewpoints.

## Verification impact on this repo

The defensive corpus generated under `examples/defensive/` still passes
the repository's ProB verification workflow. That gives us confidence
that the style switch preserves the safety intent of the checked-in
examples while changing only the guard-placement strategy.

## Which style fits which goal

Offensive style fits proof-oriented downstream work best when we want
operation enablement to express the contract's semantic admissibility as
directly as possible. Defensive style fits execution-oriented or
comparison-oriented downstream work better when we want rejected cases
to remain explicit no-ops inside the transition system. The artifact keeps both
styles: offensive style remains the clearest default for reading and proof
inspection, while defensive style supports comparison against the paper's
encoding strategy and confirms that the same corpus still behaves well under
totalized operation bodies.
