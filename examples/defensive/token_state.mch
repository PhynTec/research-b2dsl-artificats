MACHINE TokenState
SETS
  ADDRESS
DEFINITIONS
  MAX_AMOUNT == 100;
  MIN_AMOUNT == -MAX_AMOUNT;
  MAX_STEPS == 12
VARIABLES
  balances, total_supply, anim_steps_left
INVARIANT
  balances : ADDRESS +-> INTEGER &
  total_supply : INTEGER &
  total_supply = SIGMA(balances_k).(balances_k : dom(balances) | balances(balances_k)) &
  total_supply >= 0 &
  !addr.(addr : dom(balances) => balances(addr) >= 0) &
  anim_steps_left : NATURAL &
  anim_steps_left <= MAX_STEPS
INITIALISATION
  balances := {} || total_supply := 0 || anim_steps_left := MAX_STEPS
OPERATIONS
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
    END;
  mint(receiver, amount) =
    PRE
      receiver : ADDRESS &
      amount : INTEGER &
      amount : MIN_AMOUNT..MAX_AMOUNT &
      anim_steps_left > 0
    THEN
      IF amount > 0
      THEN
        balances := balances <+ {receiver |-> ({receiver |-> 0} <+ balances)(receiver) + amount};
        total_supply := total_supply + amount;
        anim_steps_left := anim_steps_left - 1
      END
    END
END