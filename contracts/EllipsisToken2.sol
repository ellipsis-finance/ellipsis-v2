pragma solidity 0.8.12;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";


contract EllipsisToken2 is IERC20 {

    string public constant symbol = "EPX";
    string public constant name = "Ellipsis X";
    uint8 public constant decimals = 18;
    uint256 public override totalSupply;
    uint256 public immutable maxTotalSupply;
    uint256 public immutable startTime;

    IERC20 public immutable oldToken;
    uint256 public immutable migrationRatio;
    uint256 public totalMigrated;

    mapping(address => uint256) public override balanceOf;
    mapping(address => mapping(address => uint256)) public override allowance;

    mapping(address => bool) public minters;
    bool isMinterSet;

    event TokensMigrated(
        address indexed sender,
        address indexed receiver,
        uint256 oldAmount,
        uint256 newAmount
    );
    event MintersSet(
        address indexed caller,
        address[] minters
    );

    constructor(
        uint256 _startTime,
        uint256 _maxTotalSupply,
        IERC20 _oldToken,
        uint256 _migrationRatio
    ) {
        startTime = _startTime;
        maxTotalSupply = _maxTotalSupply;
        oldToken = _oldToken;
        migrationRatio = _migrationRatio;
        emit Transfer(address(0), msg.sender, 0);
    }

    /**
        @dev Minter rights must be given to `EllipsisLpStaking` and `MerkleDistributor`
     */
    function setMinters(address[] calldata _minters) external {
        require(!isMinterSet);
        isMinterSet = true;
        for (uint256 i = 0; i < _minters.length; i++) {
            minters[_minters[i]] = true;
        }
        emit MintersSet(msg.sender, _minters);
    }

    function mint(address _to, uint256 _value) external returns (bool) {
        require(minters[msg.sender], "Not a minter");
        balanceOf[_to] += _value;
        totalSupply += _value;
        require(maxTotalSupply >= totalSupply, "Max supply");
        emit Transfer(address(0), _to, _value);
        return true;
    }

    /**
        @notice Burn EPS tokens in order to receive EPX
        @dev This function may be called immediately, however EPX tokens
             cannot be transferred prior to `startTime`.
        @param _receiver Address to mint the new EPX balance to
        @param _amount Amount of EPS tokens to burn for EPX
        @return bool success
     */
    function migrate(address _receiver, uint256 _amount) external returns (bool) {
        oldToken.transferFrom(msg.sender, address(0), _amount);
        totalMigrated += _amount;
        uint256 newAmount = _amount * migrationRatio;
        balanceOf[_receiver] += newAmount;
        emit Transfer(address(0), _receiver, newAmount);
        emit TokensMigrated(msg.sender, _receiver, _amount, newAmount);
        return true;
    }

    function approve(address _spender, uint256 _value) external override returns (bool) {
        allowance[msg.sender][_spender] = _value;
        emit Approval(msg.sender, _spender, _value);
        return true;
    }

    /** shared logic for transfer and transferFrom */
    function _transfer(address _from, address _to, uint256 _value) internal {
        require(block.timestamp >= startTime, "Transfers not yet enabled");
        require(balanceOf[_from] >= _value, "Insufficient balance");
        balanceOf[_from] -= _value;
        balanceOf[_to] += _value;
        emit Transfer(_from, _to, _value);
    }

    /**
        @notice Transfer tokens to a specified address
        @param _to The address to transfer to
        @param _value The amount to be transferred
        @return bool success
     */
    function transfer(address _to, uint256 _value) public override returns (bool) {
        _transfer(msg.sender, _to, _value);
        return true;
    }

    /**
        @notice Transfer tokens from one address to another
        @param _from The address which you want to send tokens from
        @param _to The address which you want to transfer to
        @param _value The amount of tokens to be transferred
        @return bool success
     */
    function transferFrom(
        address _from,
        address _to,
        uint256 _value
    )
        public
        override
        returns (bool)
    {
        uint256 allowed = allowance[_from][msg.sender];
        require(allowed >= _value, "Insufficient allowance");
        if (allowed != type(uint256).max) {
            allowance[_from][msg.sender] = allowed - _value;
        }
        _transfer(_from, _to, _value);
        return true;
    }
}
