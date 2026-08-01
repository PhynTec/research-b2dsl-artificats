MACHINE SimpleVoting
DEFINITIONS
  MAX_AMOUNT == 100;
  MIN_AMOUNT == -MAX_AMOUNT;
  MAX_STEPS == 12
VARIABLES
  votes_A, votes_B, anim_steps_left
INVARIANT
  votes_A : INTEGER &
  votes_B : INTEGER &
  votes_A >= 0 &
  votes_B >= 0 &
  anim_steps_left : NATURAL &
  anim_steps_left <= MAX_STEPS
INITIALISATION
  votes_A := 0 || votes_B := 0 || anim_steps_left := MAX_STEPS
OPERATIONS
  vote(candidate) =
    PRE
      candidate : INTEGER &
      candidate : 1..2 &
      anim_steps_left > 0 &
      candidate >= 1 &
      candidate <= 2
    THEN
      votes_A := votes_A + 2 - candidate;
      votes_B := votes_B + candidate - 1;
      anim_steps_left := anim_steps_left - 1
    END
END