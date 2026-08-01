// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract AccessControl {
    address public owner;
    int256 public secret_value;

    constructor(address initialOwner) {
        owner = initialOwner;
    }

    function update_secret(int256 new_val, address caller) external {
        require(caller == owner, "caller is not the owner");
        require(new_val >= 0, "new value must stay non-negative");

        secret_value = new_val;
    }
}
