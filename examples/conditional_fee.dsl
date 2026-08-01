// Small example showcasing conditional substitutions.
contract "ConditionalFee" {
    state:
        balance: nat
        fee_pool: nat

    invariants:
        balance >= 0;
        fee_pool >= 0

    event deposit(amount: nat) {
        do:
            if amount > 10 then
                balance := balance + (amount - 1),
                fee_pool := fee_pool + 1
            else
                balance := balance + amount
            end
    }
}
