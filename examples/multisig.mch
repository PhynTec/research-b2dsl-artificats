MACHINE MultisigWallet
SETS
  ADDRESS
DEFINITIONS
  MAX_AMOUNT == 100;
  MIN_AMOUNT == -MAX_AMOUNT;
  MAX_STEPS == 12
VARIABLES
  approved, required, executed, anim_steps_left
INVARIANT
  approved : ADDRESS +-> INTEGER &
  required : INTEGER &
  executed : BOOL &
  required >= 0 &
  anim_steps_left : NATURAL &
  anim_steps_left <= MAX_STEPS
INITIALISATION
  approved := {} || required := 0 || executed := FALSE || anim_steps_left := MAX_STEPS
OPERATIONS
  set_required(value) =
    PRE
      value : INTEGER &
      value : MIN_AMOUNT..MAX_AMOUNT &
      anim_steps_left > 0 &
      required = 0 &
      value > 0
    THEN
      required := value;
      anim_steps_left := anim_steps_left - 1
    END;
  approve(signer) =
    PRE
      signer : ADDRESS &
      anim_steps_left > 0 &
      required > 0 &
      not(executed = TRUE) &
      ({signer |-> 0} <+ approved)(signer) = 0
    THEN
      approved := approved <+ {signer |-> 1};
      anim_steps_left := anim_steps_left - 1
    END;
  execute =
    PRE
      anim_steps_left > 0 &
      required > 0 &
      not(executed = TRUE) &
      SIGMA(approved_k).(approved_k : dom(approved) | approved(approved_k)) >= required
    THEN
      executed := TRUE;
      anim_steps_left := anim_steps_left - 1
    END
END