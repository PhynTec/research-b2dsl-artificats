MACHINE LoanBook
SETS
  ADDRESS
DEFINITIONS
  MAX_AMOUNT == 100;
  MIN_AMOUNT == -MAX_AMOUNT;
  MAX_STEPS == 12
VARIABLES
  loans, anim_steps_left
INVARIANT
  loans : NATURAL +-> struct(borrower: ADDRESS, amount: NATURAL, deadline: NATURAL) &
  anim_steps_left : NATURAL &
  anim_steps_left <= MAX_STEPS
INITIALISATION
  loans := {} || anim_steps_left := MAX_STEPS
OPERATIONS
  issue(loan_id, borrower, amount, deadline) =
    PRE
      loan_id : NATURAL &
      borrower : ADDRESS &
      amount : NATURAL &
      deadline : NATURAL &
      loan_id : 0..MAX_AMOUNT &
      amount : 0..MAX_AMOUNT &
      deadline : 0..MAX_AMOUNT &
      anim_steps_left > 0 &
      amount > 0
    THEN
      loans := loans <+ {loan_id |-> rec(borrower: borrower, amount: amount, deadline: deadline)};
      anim_steps_left := anim_steps_left - 1
    END;
  close(loan_id, replacement) =
    PRE
      loan_id : NATURAL &
      replacement : struct(borrower: ADDRESS, amount: NATURAL, deadline: NATURAL) &
      loan_id : 0..MAX_AMOUNT &
      replacement'amount : 0..MAX_AMOUNT &
      replacement'deadline : 0..MAX_AMOUNT &
      anim_steps_left > 0 &
      loan_id : dom(loans) &
      loans(loan_id)'amount > 0
    THEN
      loans := loans <+ {loan_id |-> replacement};
      anim_steps_left := anim_steps_left - 1
    END
END