// Single-owner update gate for a protected integer value.
contract "AccessControl" {
    // Store the controlling account and the protected state.
    state:
        owner: address
        secret_value: int

    // Keep the protected value in the non-negative range.
    invariants:
        secret_value >= 0

    // Allow updates only when the supplied caller is the owner.
    event update_secret(new_val: int, caller: address) {
        where caller == owner
        do:
            secret_value := new_val
    }
}
