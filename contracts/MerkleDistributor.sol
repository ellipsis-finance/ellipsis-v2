// SPDX-License-Identifier: UNLICENSED
pragma solidity 0.8.12;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";


interface MintableToken {
    function mint(address _to, uint256 _value) external returns (bool);
}


contract MerkleDistributor is Ownable {

    bytes32 public root;
    MintableToken public immutable token;

    uint256 public minted;
    uint256 public maxMintable;

    mapping(address => bool) public isClaimed;

    event Claimed(
        address indexed account,
        address indexed receiver,
        uint256 amount,
        uint256 totalMinted
    );

    constructor(MintableToken _token) {
        token = _token;
    }

    function setParams(bytes32 _root, uint256 _maxMintable) external onlyOwner {
        root = _root;
        maxMintable = _maxMintable;
        renounceOwnership();
    }

    function claim(
        uint256 _amount,
        address _receiver,
        bytes32[] calldata _merkleProof
    ) external {
        require(root != 0x00, "Root not set");
        require(!isClaimed[msg.sender], "Already claimed");

        // Verify the merkle proof.
        bytes32 node = keccak256(abi.encodePacked(msg.sender, _amount));
        require(verify(_merkleProof, node), "Invalid proof");

        minted += _amount;
        require(minted <= maxMintable, "Exceeds mint limit");

        // Mark it claimed and send the token.
        isClaimed[msg.sender] = true;
        token.mint(_receiver, _amount);

        emit Claimed(msg.sender, _receiver, _amount, minted);
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
