MACHINE ConditionalFee
DEFINITIONS
  MAX_AMOUNT == 100;
  MIN_AMOUNT == -MAX_AMOUNT;
  MAX_STEPS == 12
VARIABLES
  balance, fee_pool, anim_steps_left
INVARIANT
  balance : NATURAL &
  fee_pool : NATURAL &
  balance >= 0 &
  fee_pool >= 0 &
  anim_steps_left : NATURAL &
  anim_steps_left <= MAX_STEPS
INITIALISATION
  balance := 0 || fee_pool := 0 || anim_steps_left := MAX_STEPS
OPERATIONS
  deposit(amount) =
    PRE
      amount : NATURAL &
      amount : 0..MAX_AMOUNT &
      anim_steps_left > 0
    THEN
      IF amount > 10 THEN
        balance := balance + amount - 1;
        fee_pool := fee_pool + 1
      ELSE
        balance := balance + amount
      END;
      anim_steps_left := anim_steps_left - 1
    END
END