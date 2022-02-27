// SPDX-License-Identifier: UNLICENSED
pragma solidity 0.7.6;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";


interface MintableToken {
    function mint(address _to, uint256 _value) external returns (bool);
}


contract MerkleDistributor {

    mapping(address => bool) isClaimed;

    bytes32 public immutable root;
    MintableToken public immutable token;

    event Claimed(
        address indexed account,
        uint256 amount,
        address receiver
    );

    constructor(MintableToken _token, bytes32 _root) {
        token = _token;
        root = _root;
    }

    function claim(
        uint256 _amount,
        address _receiver,
        bytes32[] calldata _merkleProof
    ) external {
        require(!isClaimed[msg.sender], "Already claimed");

        // Verify the merkle proof.
        bytes32 node = keccak256(abi.encodePacked(msg.sender, _amount));
        require(verify(_merkleProof, node), "Invalid proof");

        // Mark it claimed and send the token.
        isClaimed[msg.sender] = true;
        token.mint(_receiver, _amount);

        emit Claimed(msg.sender, _amount, _receiver);
    }

    function verify(bytes32[] calldata _proof, bytes32 _leaf) internal view returns (bool) {
        bytes32 computedHash = _leaf;

        for (uint256 i = 0; i < _proof.length; i++) {
            bytes32 proofElement = _proof[i];

            if (computedHash <= proofElement) {
                // Hash(current computed hash + current element of the proof)
                computedHash = keccak256(abi.encodePacked(computedHash, proofElement));
            } else {
                // Hash(current element of the proof + current computed hash)
                computedHash = keccak256(abi.encodePacked(proofElement, computedHash));
            }
        }

        // Check if the computed hash (root) is equal to the provided root
        return computedHash == root;
    }

}
