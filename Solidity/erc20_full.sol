// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract Erc20Full {
    mapping(address => uint256) public balances;
    mapping(address => mapping(address => uint256)) public allowances;
    uint256 public total_supply;

    function mint(address receiver, uint256 amount) external {
        balances[receiver] += amount;
        total_supply += amount;
    }

    function approve(address owner, address spender, uint256 amount) external {
        allowances[owner][spender] = amount;
    }

    function transfer_from(
        address owner,
        address spender,
        address receiver,
        uint256 amount
    ) external {
        require(allowances[owner][spender] >= amount, "allowance too low");
        require(balances[owner] >= amount, "balance too low");

        allowances[owner][spender] -= amount;
        if (owner != receiver) {
            balances[owner] -= amount;
            balances[receiver] += amount;
        }
    }
}
