// Three-party escrow with buyer funding and broker-controlled recovery.
contract "Escrow" {
    enum Status { Pending, Funded, Released, Refunded }

    // Encode the parties, lifecycle status, and held funds.
    state:
        buyer: address
        seller: address
        broker: address
        status: Status
        balance: int

    // Keep the parties distinct and held balance non-negative.
    invariants:
        buyer != seller;
        buyer != broker;
        seller != broker;
        balance >= 0

    // Move from the initial state into the funded escrow state.
    event deposit(caller: address, amount: int) {
        where caller == buyer
        where amount > 0
        where status == Pending
        do:
            balance := 0 - amount,
            status := Funded
    }

    // Let the buyer authorize release of the funded escrow,
    // abstracting the seller payout by clearing the held balance.
    event approve_release(caller: address) {
        where caller == buyer
        where status == Funded
        do:
            status := Released,
            balance := 0
    }

    // Let the broker cancel the funded escrow and zero the balance.
    event refund(caller: address) {
        where caller == broker
        where status == Funded
        do:
            balance := 0,
            status := Refunded
    }
}
