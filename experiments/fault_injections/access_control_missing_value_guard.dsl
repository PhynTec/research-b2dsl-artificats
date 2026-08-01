// Fault injection: remove the non-negative value guard from access control.
contract "AccessControlMissingValueGuard" {
    state:
        owner: address
        secret_value: int

    invariants:
        secret_value >= 0

    event update_secret(new_val: int, caller: address) {
        where caller == owner
        do:
            secret_value := new_val
    }
}
