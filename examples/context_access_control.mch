MACHINE ContextAccessControl
SETS
  ADDRESS
DEFINITIONS
  MAX_AMOUNT == 100;
  MIN_AMOUNT == -MAX_AMOUNT;
  MAX_STEPS == 12
VARIABLES
  owner, paused, last_update, anim_steps_left
INVARIANT
  owner : ADDRESS &
  paused : BOOL &
  last_update : NATURAL &
  anim_steps_left : NATURAL &
  anim_steps_left <= MAX_STEPS
INITIALISATION
  ANY owner_init WHERE
    owner_init : ADDRESS
  THEN
    owner := owner_init || paused := FALSE || last_update := 0 || anim_steps_left := MAX_STEPS
  END
OPERATIONS
  pause(msg_sender, block_timestamp) =
    PRE
      msg_sender : ADDRESS &
      block_timestamp : NATURAL &
      block_timestamp : 0..MAX_AMOUNT &
      anim_steps_left > 0 &
      msg_sender = owner
    THEN
      paused := TRUE;
      last_update := block_timestamp;
      anim_steps_left := anim_steps_left - 1
    END;
  unpause(msg_sender, block_timestamp) =
    PRE
      msg_sender : ADDRESS &
      block_timestamp : NATURAL &
      block_timestamp : 0..MAX_AMOUNT &
      anim_steps_left > 0 &
      msg_sender = owner
    THEN
      paused := FALSE;
      last_update := block_timestamp;
      anim_steps_left := anim_steps_left - 1
    END
END