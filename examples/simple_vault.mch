MACHINE SimpleVault
SETS
  ADDRESS
DEFINITIONS
  MAX_AMOUNT == 100;
  MIN_AMOUNT == -MAX_AMOUNT;
  MAX_STEPS == 12
VARIABLES
  balances, total_deposited, owner, is_paused, anim_steps_left
INVARIANT
  balances : ADDRESS +-> NATURAL &
  total_deposited : NATURAL &
  owner : ADDRESS &
  is_paused : INTEGER &
  total_deposited = SIGMA(balances_k).(balances_k : dom(balances) | balances(balances_k)) &
  !addr.(addr : dom(balances) => balances(addr) >= 0) &
  is_paused >= 0 &
  is_paused <= 1 &
  anim_steps_left : NATURAL &
  anim_steps_left <= MAX_STEPS
INITIALISATION
  ANY owner_init WHERE
    owner_init : ADDRESS
  THEN
    balances := {} || total_deposited := 0 || owner := owner_init || is_paused := 0 || anim_steps_left := MAX_STEPS
  END
OPERATIONS
  deposit(amount, caller) =
    PRE
      amount : NATURAL &
      caller : ADDRESS &
      amount : 0..MAX_AMOUNT &
      anim_steps_left > 0 &
      is_paused = 0 &
      amount > 0
    THEN
      balances := balances <+ {caller |-> ({caller |-> 0} <+ balances)(caller) + amount};
      total_deposited := total_deposited + amount;
      anim_steps_left := anim_steps_left - 1
    END;
  withdraw(amount, caller) =
    PRE
      amount : NATURAL &
      caller : ADDRESS &
      amount : 0..MAX_AMOUNT &
      anim_steps_left > 0 &
      caller : dom(balances) &
      is_paused = 0 &
      balances(caller) >= amount
    THEN
      balances := balances <+ {caller |-> ({caller |-> 0} <+ balances)(caller) - amount};
      total_deposited := total_deposited - amount;
      anim_steps_left := anim_steps_left - 1
    END;
  toggle_pause(caller) =
    PRE
      caller : ADDRESS &
      anim_steps_left > 0 &
      caller = owner
    THEN
      IF is_paused = 0 THEN
        is_paused := 1
      ELSE
        is_paused := 0
      END;
      anim_steps_left := anim_steps_left - 1
    END
END