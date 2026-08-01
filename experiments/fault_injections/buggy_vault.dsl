// Defense demo: SimpleVault with one injected bug.
// The withdraw event updates the caller balance but FORGETS to decrement
// total_deposited, breaking the accounting invariant
// total_deposited == sum(balances). ProB finds a minimal 3-step trace:
// INITIALISATION -> deposit(1, a) -> withdraw(1, a).
contract "BuggyVault" {

    state:
        balances: map(address -> nat)
        total_deposited: nat
        owner: address
        is_paused: int

    invariants:
        total_deposited == sum(balances);
        forall addr . balances[addr] >= 0;
        is_paused >= 0;
        is_paused <= 1

    event deposit(amount: nat, caller: address) {
        where is_paused == 0
        where amount > 0
        do:
            balances[caller] := balances[caller] + amount,
            total_deposited := total_deposited + amount
    }

    // BUG: missing "total_deposited := total_deposited - amount"
    event withdraw(amount: nat, caller: address) {
        where is_paused == 0
        where balances[caller] >= amount
        do:
            balances[caller] := balances[caller] - amount
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
