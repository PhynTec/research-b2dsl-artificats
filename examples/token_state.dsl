// Minimal fungible-token state with balances and total supply only.
contract "TokenState" {
    // Track balances together with the currently minted supply.
    state:
        balances: map(address -> int)
        total_supply: int

    // Keep the minimal token sound in the current subset.
    // A fuller owner->spender allowance model is deferred to a future
    // `erc20_full.dsl` once nested maps are available.
    invariants:
        total_supply == sum(balances);
        total_supply >= 0;
        forall addr . balances[addr] >= 0

    // Move tokens directly between two distinct accounts.
    event transfer(sender: address, receiver: address, amount: int) {
        where balances[sender] >= amount
        where amount > 0
        do:
            balances[sender] := balances[sender] - amount,
            balances[receiver] := balances[receiver] + amount
    }

    // Mint new tokens into an account and raise total supply.
    event mint(receiver: address, amount: int) {
        where amount > 0
        do:
            balances[receiver] := balances[receiver] + amount,
            total_supply := total_supply + amount
    }
}
