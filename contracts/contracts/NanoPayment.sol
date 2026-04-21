// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract NanoPayment {
    mapping(address => uint256) public balances;

    event Deposit(address indexed agent, uint256 amount);
    event Payment(address indexed sender, address indexed recipient, uint256 amount);

    function deposit() public payable {
        require(msg.value > 0, "Deposit amount must be greater than 0");
        balances[msg.sender] += msg.value;
        emit Deposit(msg.sender, msg.value);
    }

    function pay(address recipient, uint256 amount) public {
        require(recipient != address(0), "Invalid recipient address");
        require(balances[msg.sender] >= amount, "Insufficient balance");
        require(amount > 0, "Payment amount must be greater than 0");

        balances[msg.sender] -= amount;
        balances[recipient] += amount;

        emit Payment(msg.sender, recipient, amount);
    }

    function getBalance(address agent) public view returns (uint256) {
        return balances[agent];
    }
}
