// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract ConditionalFee {
    uint256 public balance;
    uint256 public fee_pool;

    function deposit(uint256 amount) external {
        if (amount > 10) {
            balance += amount - 1;
            fee_pool += 1;
        } else {
            balance += amount;
        }
    }
}
