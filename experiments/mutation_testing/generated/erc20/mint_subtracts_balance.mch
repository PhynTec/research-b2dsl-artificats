MACHINE Erc20Full
SETS
  ADDRESS
DEFINITIONS
  MAX_AMOUNT == 100;
  MIN_AMOUNT == -MAX_AMOUNT;
  MAX_STEPS == 12
VARIABLES
  balances, allowances, total_supply, anim_steps_left
INVARIANT
  balances : ADDRESS +-> NATURAL &
  allowances : ADDRESS +-> (ADDRESS +-> NATURAL) &
  total_supply : NATURAL &
  total_supply = SIGMA(balances_k).(balances_k : dom(balances) | balances(balances_k)) &
  total_supply >= 0 &
  !holder.(holder : dom(balances) => balances(holder) >= 0) &
  !owner.(owner : dom(allowances) => (!spender.(spender : dom(({owner |-> {}} <+ allowances)(owner)) => allowances(owner)(spender) >= 0))) &
  anim_steps_left : NATURAL &
  anim_steps_left <= MAX_STEPS
INITIALISATION
  balances := {} || allowances := {} || total_supply := 0 || anim_steps_left := MAX_STEPS
OPERATIONS
  mint(receiver, amount) =
    PRE
      receiver : ADDRESS &
      amount : NATURAL &
      amount : 0..MAX_AMOUNT &
      anim_steps_left > 0
    THEN
      balances := balances <+ {receiver |-> ({receiver |-> 0} <+ balances)(receiver) - amount};
      total_supply := total_supply + amount;
      anim_steps_left := anim_steps_left - 1
    END;
  approve(owner, spender, amount) =
    PRE
      owner : ADDRESS &
      spender : ADDRESS &
      amount : NATURAL &
      amount : 0..MAX_AMOUNT &
      anim_steps_left > 0
    THEN
      allowances := allowances <+ {owner |-> (({owner |-> {}} <+ allowances)(owner) <+ {spender |-> amount})};
      anim_steps_left := anim_steps_left - 1
    END;
  transfer_from(owner, spender, receiver, amount) =
    PRE
      owner : ADDRESS &
      spender : ADDRESS &
      receiver : ADDRESS &
      amount : NATURAL &
      amount : 0..MAX_AMOUNT &
      anim_steps_left > 0 &
      owner : dom(allowances) &
      spender : dom(({owner |-> {}} <+ allowances)(owner)) &
      owner : dom(balances) &
      allowances(owner)(spender) >= amount &
      balances(owner) >= amount
    THEN
      allowances := allowances <+ {owner |-> (({owner |-> {}} <+ allowances)(owner) <+ {spender |-> ({spender |-> 0} <+ ({owner |-> {}} <+ allowances)(owner))(spender) - amount})};
      IF owner = receiver THEN
        balances := balances <+ {receiver |-> ({receiver |-> 0} <+ balances)(receiver)}
      ELSE
        balances := balances <+ {owner |-> ({owner |-> 0} <+ balances)(owner) - amount};
        balances := balances <+ {receiver |-> ({receiver |-> 0} <+ balances)(receiver) + amount}
      END;
      anim_steps_left := anim_steps_left - 1
    END
END