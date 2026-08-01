// Minimal auction sketch with a current best bid and a closing time.
contract "Auction" {
    // Track the best accepted bid, the closing time, and a monotonic clock.
    state:
        highest_bid: int
        deadline: int
        current_time: int

    // Keep the numeric state in a sensible range for animation.
    invariants:
        highest_bid >= 0;
        deadline >= 0;
        current_time >= 0

    // Open the auction once by choosing a positive bidding window.
    event open(duration: int) {
        where deadline == 0
        where duration > 0
        do:
            deadline := current_time + duration
    }

    // Accept only improving bids that arrive before the deadline.
    event bid(amount: int) {
        where amount >= 0
        where current_time < deadline
        do:
            highest_bid := amount
    }

    // Advance the auction clock one step at a time until closing.
    event tick() {
        where current_time < deadline
        do:
            current_time := current_time + 1
    }
}
