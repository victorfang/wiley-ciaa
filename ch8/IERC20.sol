// SPDX-License-Identifier: CC0-1.0
// Cryptocurrency Investigation with Agentic AI, Victor Fang, 2026
// Teaching contrast only: ERC-20 interface names/selectors with no deployable
// runtime. Not imported by BlacklistToken.sol; not required to compile the token.
pragma solidity >=0.7.0 <0.9.0;

interface IERC20 {
    function totalSupply() external view returns (uint256);
    function balanceOf(address account) external view returns (uint256);
    function transfer(address to, uint256 amount) external returns (bool);
    function allowance(address owner, address spender)
        external view returns (uint256);
    function approve(address spender, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount)
        external returns (bool);

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
}
