// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

// Fault-injection demo contract: withdraw forgets to update total_deposited,
// breaking the intended accounting property total_deposited == sum(balances).
// Used to compare Slither detector output against the DSL-to-B pipeline.
contract BuggyVault {
    mapping(address => uint256) public balances;
    uint256 public total_deposited;
    address public owner;
    bool public is_paused;

    constructor() {
        owner = msg.sender;
    }

    function deposit(uint256 amount) external {
        require(!is_paused, "vault is paused");
        require(amount > 0, "amount must be positive");
        balances[msg.sender] += amount;
        total_deposited += amount;
    }

    function withdraw(uint256 amount) external {
        require(!is_paused, "vault is paused");
        require(balances[msg.sender] >= amount, "insufficient balance");
        balances[msg.sender] -= amount;
        // fault: "total_deposited -= amount;" removed
    }

    function toggle_pause() external {
        require(msg.sender == owner, "only owner");
        is_paused = !is_paused;
    }
}
