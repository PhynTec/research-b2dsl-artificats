// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract MultisigWallet {
    mapping(address => int256) public approved;
    int256 public required;
    int256 public executed;
    int256 public approval_count;

    function set_required(int256 value) external {
        require(required == 0, "required value already set");
        require(value > 0, "required value must be positive");

        required = value;
    }

    function approve(address signer) external {
        require(required > 0, "required value not set");
        require(executed == 0, "wallet already executed");
        require(approved[signer] == 0, "signer already approved");

        approved[signer] = 1;
        approval_count += 1;
    }

    function execute() external {
        require(required > 0, "required value not set");
        require(executed == 0, "wallet already executed");
        require(approval_count >= required, "not enough approvals");

        executed = 1;
    }
}
