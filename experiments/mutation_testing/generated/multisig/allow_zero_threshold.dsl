// Threshold wallet sketch with one approval slot per signer.
contract "MultisigWallet" {
    // Record approvals as 0 or 1, store the threshold, and remember
    // whether the wallet has already executed.
    state:
        approved: map(address -> int)
        required: int
        executed: bool

    // Keep the threshold non-negative.
    invariants:
        required >= 0

    // Set the approval threshold exactly once before any signing begins.
    event set_required(value: int) {
        where required == 0
        where value >= 0
        do:
            required := value
    }

    // Mark a signer as approved if they have not signed yet.
    event approve(signer: address) {
        where required > 0
        where not executed
        where approved[signer] == 0
        do:
            approved[signer] := 1
    }

    // Enable execution only after the approval sum reaches the threshold.
    event execute() {
        where required > 0
        where not executed
        where sum(approved) >= required
        do:
            executed := true
    }
}
