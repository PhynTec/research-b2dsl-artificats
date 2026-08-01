// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract Escrow {
    address public buyer;
    address public seller;
    address public broker;
    int256 public status;
    int256 public balance;

    constructor(address initialBuyer, address initialSeller, address initialBroker) {
        require(initialBuyer != initialSeller, "buyer and seller must differ");
        require(initialBuyer != initialBroker, "buyer and broker must differ");
        require(initialSeller != initialBroker, "seller and broker must differ");

        buyer = initialBuyer;
        seller = initialSeller;
        broker = initialBroker;
    }

    function deposit(address caller, int256 amount) external {
        require(caller == buyer, "only the buyer can deposit");
        require(amount > 0, "amount must be positive");
        require(status == 0, "escrow already funded");

        balance = amount;
        status = 1;
    }

    function approve_release(address caller) external {
        require(caller == buyer, "only the buyer can release");
        require(status == 1, "escrow is not funded");

        status = 2;
        balance = 0;
    }

    function refund(address caller) external {
        require(caller == broker, "only the broker can refund");
        require(status == 1, "escrow is not funded");

        balance = 0;
        status = 3;
    }
}
