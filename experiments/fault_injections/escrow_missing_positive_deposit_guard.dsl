// Fault injection: allow a funded escrow to be created with a negative balance.
contract "EscrowMissingPositiveDepositGuard" {
    enum Status { Pending, Funded, Released, Refunded }

    state:
        buyer: address
        seller: address
        broker: address
        status: Status
        balance: int

    invariants:
        buyer != seller;
        buyer != broker;
        seller != broker;
        balance >= 0

    event deposit(caller: address, amount: int) {
        where caller == buyer
        where status == Pending
        do:
            balance := amount,
            status := Funded
    }

    event approve_release(caller: address) {
        where caller == buyer
        where status == Funded
        do:
            status := Released,
            balance := 0
    }

    event refund(caller: address) {
        where caller == broker
        where status == Funded
        do:
            balance := 0,
            status := Refunded
    }
}
