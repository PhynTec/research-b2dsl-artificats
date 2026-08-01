// Two-candidate vote counter encoded with arithmetic updates.
contract "SimpleVoting" {
    // Store one counter per candidate.
    state:
        votes_A: int
        votes_B: int

    // Keep both tallies non-negative.
    invariants:
        votes_A >= 0;
        votes_B >= 0

    // Accept encoded candidate values 1 and 2 only.
    event vote(candidate: int) {
        // Encoding: candidate==1 increments votes_A by 1 and votes_B by 0
        //           candidate==2 increments votes_A by 0 and votes_B by 1
        //           This is a workaround for the absence of if/else in the
        //           current grammar.
        where candidate >= 1
        where candidate <= 2
        do:
            votes_A := votes_A + (2 - candidate),
            votes_B := votes_B + (candidate - 1)
    }
}
