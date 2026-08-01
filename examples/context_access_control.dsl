contract "ContextAccessControl" {
    state:
        owner: address
        paused: bool
        last_update: nat

    event pause() {
        where msg_sender == owner
        do:
            paused := true,
            last_update := block_timestamp
    }

    event unpause() {
        where msg_sender == owner
        do:
            paused := false,
            last_update := block_timestamp
    }
}
