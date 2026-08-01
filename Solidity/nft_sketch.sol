// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract NFTRegistry {
    mapping(int256 => address) public owner;
    mapping(int256 => bool) public minted;

    function mint(int256 token_id, address to) external {
        require(!minted[token_id], "token already minted");

        owner[token_id] = to;
        minted[token_id] = true;
    }

    function transfer(int256 token_id, address to, address sender) external {
        require(owner[token_id] == sender, "sender is not the owner");

        owner[token_id] = to;
    }
}
