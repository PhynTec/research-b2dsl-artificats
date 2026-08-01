contract "SimpleVault" {

    state:
        balances: map(address -> nat)
        total_deposited: nat
        owner: address
        is_paused: int // Booleans modeled as int (0=false, 1=true) per Section 8.5

    invariants:
        // Accounting invariant: sum of all balances must equal total_deposited
        total_deposited == sum(balances);
        
        // Safety invariant: no balance can ever be negative
        forall addr . balances[addr] >= 0;
        
        // State invariant: pause flag must be binary
        is_paused >= 0;
        is_paused <= 1

    event deposit(amount: nat, caller: address) {
        where is_paused == 0
        where amount > 0
        do:
            balances[caller] := balances[caller] + amount,
            total_deposited := total_deposited
    }

    event withdraw(amount: nat, caller: address) {
        where is_paused == 0
        where balances[caller] >= amount
        do:
            balances[caller] := balances[caller] - amount,
            total_deposited := total_deposited - amount
    }

    event toggle_pause(caller: address) {
        where caller == owner
        do:
            if is_paused == 0 then
                is_paused := 1
            else
                is_paused := 0
            end
    }
}
