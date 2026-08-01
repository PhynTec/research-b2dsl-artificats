MACHINE Auction
DEFINITIONS
  MAX_AMOUNT == 100;
  MIN_AMOUNT == -MAX_AMOUNT;
  MAX_STEPS == 12
VARIABLES
  highest_bid, deadline, current_time, anim_steps_left
INVARIANT
  highest_bid : INTEGER &
  deadline : INTEGER &
  current_time : INTEGER &
  highest_bid >= 0 &
  deadline >= 0 &
  current_time >= 0 &
  anim_steps_left : NATURAL &
  anim_steps_left <= MAX_STEPS
INITIALISATION
  highest_bid := 0 || deadline := 0 || current_time := 0 || anim_steps_left := MAX_STEPS
OPERATIONS
  open(duration) =
    PRE
      duration : INTEGER &
      duration : MIN_AMOUNT..MAX_AMOUNT &
      anim_steps_left > 0 &
      deadline = 0 &
      duration > 0
    THEN
      deadline := current_time + duration;
      anim_steps_left := anim_steps_left - 1
    END;
  bid(amount) =
    PRE
      amount : INTEGER &
      amount : MIN_AMOUNT..MAX_AMOUNT &
      anim_steps_left > 0 &
      amount > highest_bid &
      current_time < deadline
    THEN
      highest_bid := amount;
      anim_steps_left := anim_steps_left - 1
    END;
  tick =
    PRE
      anim_steps_left > 0 &
      current_time < deadline
    THEN
      current_time := current_time + 1;
      anim_steps_left := anim_steps_left - 1
    END
END