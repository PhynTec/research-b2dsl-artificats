// ERC20-style example exercising nested maps and multiple quantified variables.
contract "Erc20Full" {
    state:
        balances: map(address -> nat)
        allowances: map(address -> map(address -> nat))
        total_supply: nat

    invariants:
        total_supply == sum(balances);
        total_supply >= 0;
        forall holder . balances[holder] >= 0;
        forall owner, spender . allowances[owner][spender] >= 0

    event mint(receiver: address, amount: nat) {
        do:
            balances[receiver] := balances[receiver] + amount,
            total_supply := total_supply + amount
    }

    event approve(owner: address, spender: address, amount: nat) {
        do:
            allowances[owner][spender] := amount
    }

    event transfer_from(owner: address, spender: address, receiver: address, amount: nat) {
        where allowances[owner][spender] >= amount
        where balances[owner] >= amount
        do:
            allowances[owner][spender] := allowances[owner][spender] - amount,
            if owner == receiver then
                balances[receiver] := balances[receiver]
            else
                balances[owner] := balances[owner],
                balances[receiver] := balances[receiver] + amount
            end
    }
}
