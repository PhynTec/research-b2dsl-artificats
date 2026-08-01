MACHINE NFTRegistry
SETS
  ADDRESS
DEFINITIONS
  MAX_AMOUNT == 100;
  MIN_AMOUNT == -MAX_AMOUNT;
  MAX_STEPS == 12
VARIABLES
  owner, minted, anim_steps_left
INVARIANT
  owner : INTEGER +-> ADDRESS &
  minted : INTEGER +-> BOOL &
  anim_steps_left : NATURAL &
  anim_steps_left <= MAX_STEPS
INITIALISATION
  owner := {} || minted := {} || anim_steps_left := MAX_STEPS
OPERATIONS
  mint(token_id, to) =
    PRE
      token_id : INTEGER &
      to : ADDRESS &
      token_id : MIN_AMOUNT..MAX_AMOUNT &
      anim_steps_left > 0 &
      not(({token_id |-> FALSE} <+ minted)(token_id) = TRUE)
    THEN
      owner := owner <+ {token_id |-> to};
      minted := minted <+ {token_id |-> TRUE};
      anim_steps_left := anim_steps_left - 1
    END;
  transfer(token_id, to, sender) =
    PRE
      token_id : INTEGER &
      to : ADDRESS &
      sender : ADDRESS &
      token_id : MIN_AMOUNT..MAX_AMOUNT &
      anim_steps_left > 0
    THEN
      owner := owner <+ {token_id |-> to};
      anim_steps_left := anim_steps_left - 1
    END
END