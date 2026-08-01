// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract SimpleVoting {
    int256 public votes_A;
    int256 public votes_B;

    function vote(int256 candidate) external {
        require(candidate >= 1, "candidate must be 1 or 2");
        require(candidate <= 2, "candidate must be 1 or 2");

        votes_A += 2 - candidate;
        votes_B += candidate - 1;
    }
}
