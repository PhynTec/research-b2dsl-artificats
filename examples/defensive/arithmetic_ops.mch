MACHINE ArithmeticOps
DEFINITIONS
  MAX_AMOUNT == 100;
  MIN_AMOUNT == -MAX_AMOUNT;
  MAX_STEPS == 12
VARIABLES
  product, quotient, remainder, anim_steps_left
INVARIANT
  product : NATURAL &
  quotient : NATURAL &
  remainder : NATURAL &
  product >= 0 &
  quotient >= 0 &
  remainder >= 0 &
  anim_steps_left : NATURAL &
  anim_steps_left <= MAX_STEPS
INITIALISATION
  product := 0 || quotient := 0 || remainder := 0 || anim_steps_left := MAX_STEPS
OPERATIONS
  calculate(left, right, divisor) =
    PRE
      left : NATURAL &
      right : NATURAL &
      divisor : NATURAL &
      left : 0..MAX_AMOUNT &
      right : 0..MAX_AMOUNT &
      divisor : 0..MAX_AMOUNT &
      anim_steps_left > 0
    THEN
      IF divisor > 0
      THEN
        product := left * right;
        quotient := left / divisor;
        remainder := left mod divisor;
        anim_steps_left := anim_steps_left - 1
      END
    END
END