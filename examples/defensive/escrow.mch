MACHINE Escrow
SETS
  ADDRESS;
  Status = {Pending, Funded, Released, Refunded}
DEFINITIONS
  MAX_AMOUNT == 100;
  MIN_AMOUNT == -MAX_AMOUNT;
  MAX_STEPS == 12
VARIABLES
  buyer, seller, broker, status, balance, anim_steps_left
INVARIANT
  buyer : ADDRESS &
  seller : ADDRESS &
  broker : ADDRESS &
  status : Status &
  balance : INTEGER &
  buyer /= seller &
  buyer /= broker &
  seller /= broker &
  balance >= 0 &
  anim_steps_left : NATURAL &
  anim_steps_left <= MAX_STEPS
INITIALISATION
  ANY buyer_init, seller_init, broker_init WHERE
    buyer_init : ADDRESS & seller_init : ADDRESS & broker_init : ADDRESS & buyer_init /= seller_init & buyer_init /= broker_init & seller_init /= broker_init
  THEN
    buyer := buyer_init || seller := seller_init || broker := broker_init || status := Pending || balance := 0 || anim_steps_left := MAX_STEPS
  END
OPERATIONS
  deposit(caller, amount) =
    PRE
      caller : ADDRESS &
      amount : INTEGER &
      amount : MIN_AMOUNT..MAX_AMOUNT &
      anim_steps_left > 0
    THEN
      IF caller = buyer &
         amount > 0 &
         status = Pending
      THEN
        balance := amount;
        status := Funded;
        anim_steps_left := anim_steps_left - 1
      END
    END;
  approve_release(caller) =
    PRE
      caller : ADDRESS &
      anim_steps_left > 0
    THEN
      IF caller = buyer &
         status = Funded
      THEN
        status := Released;
        balance := 0;
        anim_steps_left := anim_steps_left - 1
      END
    END;
  refund(caller) =
    PRE
      caller : ADDRESS &
      anim_steps_left > 0
    THEN
      IF caller = broker &
         status = Funded
      THEN
        balance := 0;
        status := Refunded;
        anim_steps_left := anim_steps_left - 1
      END
    END
END