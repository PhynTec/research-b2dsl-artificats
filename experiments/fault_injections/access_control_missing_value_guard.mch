MACHINE AccessControlMissingValueGuard
SETS
  ADDRESS
DEFINITIONS
  MAX_AMOUNT == 100;
  MIN_AMOUNT == -MAX_AMOUNT;
  MAX_STEPS == 12
VARIABLES
  owner, secret_value, anim_steps_left
INVARIANT
  owner : ADDRESS &
  secret_value : INTEGER &
  secret_value >= 0 &
  anim_steps_left : NATURAL &
  anim_steps_left <= MAX_STEPS
INITIALISATION
  ANY owner_init WHERE
    owner_init : ADDRESS
  THEN
    owner := owner_init || secret_value := 0 || anim_steps_left := MAX_STEPS
  END
OPERATIONS
  update_secret(new_val, caller) =
    PRE
      new_val : INTEGER &
      caller : ADDRESS &
      new_val : MIN_AMOUNT..MAX_AMOUNT &
      anim_steps_left > 0 &
      caller = owner
    THEN
      secret_value := new_val;
      anim_steps_left := anim_steps_left - 1
    END
END