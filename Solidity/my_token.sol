// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract MyToken {
    mapping(address => int256) public balances;
    int256 public total_supply;

    function transfer(address sender, address receiver, int256 amount) external {
        require(balances[sender] >= amount, "balance too low");
        require(amount > 0, "amount must be positive");

        balances[sender] -= amount;
        balances[receiver] += amount;
    }

    function mint(address receiver, int256 amount) external {
        require(amount > 0, "amount must be positive");

        balances[receiver] += amount;
        total_supply += amount;
    }

    function burn(address sender, int256 amount) external {
        require(balances[sender] >= amount, "balance too low");

        balances[sender] -= amount;
        total_supply -= amount;
    }
}
