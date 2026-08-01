// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract Auction {
    int256 public highest_bid;
    int256 public deadline;
    int256 public current_time;

    function open(int256 duration) external {
        require(deadline == 0, "auction already opened");
        require(duration > 0, "duration must be positive");

        deadline = current_time + duration;
    }

    function bid(int256 amount) external {
        require(amount > highest_bid, "bid must improve the current best");
        require(current_time < deadline, "auction already closed");

        highest_bid = amount;
    }

    function tick() external {
        require(current_time < deadline, "auction already closed");

        current_time += 1;
    }
}
