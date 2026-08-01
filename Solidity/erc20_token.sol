// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract StandardToken {
    mapping(address => uint256) public balances;
    mapping(address => mapping(address => uint256)) public allowances;
    uint256 public total_supply;

    function transfer(address sender, address receiver, uint256 amount) external {
        require(amount > 0, "amount must be positive");
        require(balances[sender] >= amount, "balance too low");

        balances[sender] -= amount;
        balances[receiver] += amount;
    }

    function approve(address owner, address spender, uint256 amount) external {
        allowances[owner][spender] = amount;
    }

    function transferFrom(
        address spender,
        address from,
        address to,
        uint256 amount
    ) external {
        require(amount > 0, "amount must be positive");
        require(balances[from] >= amount, "balance too low");
        require(allowances[from][spender] >= amount, "allowance too low");

        balances[from] -= amount;
        balances[to] += amount;
        allowances[from][spender] -= amount;
    }

    function mint(address receiver, uint256 amount) external {
        balances[receiver] += amount;
        total_supply += amount;
    }
}
