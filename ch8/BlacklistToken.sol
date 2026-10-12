// SPDX-License-Identifier: MIT
// Cryptocurrency Investigation with Agentic AI, Victor Fang, 2026
// Synthetic teaching token with a sender blacklist. Not an issuer contract.
// Standalone: does not import IERC20.sol (that file is a separate teaching contrast).
pragma solidity >=0.7.0 <0.9.0;

contract BlacklistToken {
    address public owner = msg.sender;
    mapping(address => uint256) public balanceOf;
    // Offline teaching map only; this lab never populates live blacklist data.
    mapping(address => bool) public blacklisted;

    modifier onlyOwner() { require(msg.sender == owner, "owner"); _; }

    function mint(address to, uint256 amount) external onlyOwner {
        balanceOf[to] += amount;
    }

    function setBlacklist(address who, bool value) external onlyOwner {
        blacklisted[who] = value;
    }

    function transfer(address to, uint256 amount) external {
        require(!blacklisted[msg.sender], "blacklisted");
        require(to != address(0), "zero");
        require(balanceOf[msg.sender] >= amount, "balance");
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
    }
}
