// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IERC20 {
    function transfer(address recipient, uint256 amount) external returns (bool);
    function transferFrom(address sender, address recipient, uint256 amount) external returns (bool);
}

contract AgentEscrowUSDC {
    IERC20 public immutable usdc;

    struct Escrow {
        address sender;
        address receiver;
        uint256 amount;
        bool released;
        bool refunded;
    }

    mapping(bytes32 => Escrow) public escrows;

    event EscrowLocked(bytes32 indexed escrowId, address indexed sender, address indexed receiver, uint256 amount);
    event EscrowReleased(bytes32 indexed escrowId, address indexed receiver, uint256 amount);
    event EscrowRefunded(bytes32 indexed escrowId, address indexed sender, uint256 amount);

    constructor(address usdcAddress) {
        require(usdcAddress != address(0), "invalid_usdc");
        usdc = IERC20(usdcAddress);
    }

    function lock(bytes32 escrowId, address receiver, uint256 amount) external {
        require(receiver != address(0), "invalid_receiver");
        require(amount > 0, "invalid_amount");
        Escrow storage escrow = escrows[escrowId];
        require(escrow.sender == address(0), "escrow_exists");
        require(usdc.transferFrom(msg.sender, address(this), amount), "transfer_failed");

        escrows[escrowId] = Escrow({
            sender: msg.sender,
            receiver: receiver,
            amount: amount,
            released: false,
            refunded: false
        });

        emit EscrowLocked(escrowId, msg.sender, receiver, amount);
    }

    function release(bytes32 escrowId) external {
        Escrow storage escrow = escrows[escrowId];
        require(escrow.sender != address(0), "missing_escrow");
        require(!escrow.released && !escrow.refunded, "escrow_closed");
        escrow.released = true;
        require(usdc.transfer(escrow.receiver, escrow.amount), "release_failed");
        emit EscrowReleased(escrowId, escrow.receiver, escrow.amount);
    }

    function refund(bytes32 escrowId) external {
        Escrow storage escrow = escrows[escrowId];
        require(escrow.sender != address(0), "missing_escrow");
        require(!escrow.released && !escrow.refunded, "escrow_closed");
        escrow.refunded = true;
        require(usdc.transfer(escrow.sender, escrow.amount), "refund_failed");
        emit EscrowRefunded(escrowId, escrow.sender, escrow.amount);
    }
}
