// Small NFT ownership registry keyed by token identifier.
contract "NFTRegistry" {
    // Map each minted token id to its current owner and record whether
    // the id has already been minted.
    state:
        owner: map(int -> address)
        minted: map(int -> bool)

    // Seed ownership for animation on fresh token ids only.
    event mint(token_id: int, to: address) {
        where not minted[token_id]
        do:
            owner[token_id] := to,
            minted[token_id] := true
    }

    // Transfer only when the supplied sender matches the recorded owner.
    event transfer(token_id: int, to: address, sender: address) {
        where owner[token_id] == sender
        do:
            owner[token_id] := to
    }
}
