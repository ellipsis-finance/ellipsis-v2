pragma solidity 0.7.6;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/SafeERC20.sol";
import "@openzeppelin/contracts/math/SafeMath.sol";


contract EllipsisToken2 is IERC20 {

    using SafeMath for uint256;

    string public constant symbol = "EPS2";
    string public constant name = "Ellipsis 2";
    uint8 public constant decimals = 18;
    uint256 public override totalSupply;
    uint256 public immutable maxTotalSupply;
    uint256 public immutable startTime;
    address public minter;

    IERC20 public immutable oldToken;
    uint256 public immutable migrationRatio;
    uint256 public totalMigrated;

    mapping(address => uint256) public override balanceOf;
    mapping(address => mapping(address => uint256)) public override allowance;

    event TokensMigrated(
        address indexed user,
        uint256 oldAmount,
        uint256 newAmount
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

    function setAddresses(address _lpStaking) external {
        require(minter == address(0));
        minter = _lpStaking;
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
        balanceOf[_from] = balanceOf[_from].sub(_value);
        balanceOf[_to] = balanceOf[_to].add(_value);
        emit Transfer(_from, _to, _value);
    }

    /**
        @notice Transfer tokens to a specified address
        @param _to The address to transfer to
        @param _value The amount to be transferred
        @return Success boolean
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
        @return Success boolean
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
        if (allowed != uint(-1)) {
            allowance[_from][msg.sender] = allowed.sub(_value);
        }
        _transfer(_from, _to, _value);
        return true;
    }

    function mint(address _to, uint256 _value) external returns (bool) {
        require(msg.sender == minter);
        balanceOf[_to] = balanceOf[_to].add(_value);
        totalSupply = totalSupply.add(_value);
        require(maxTotalSupply >= totalSupply);
        emit Transfer(address(0), _to, _value);
        return true;
    }

    function migrate(uint256 _amount) external returns (bool) {
        oldToken.transferFrom(msg.sender, address(0), _amount);
        uint256 newAmount = _amount.mul(migrationRatio);
        balanceOf[msg.sender] = balanceOf[msg.sender].add(newAmount);
        emit Transfer(address(0), msg.sender, newAmount);
        emit TokensMigrated(msg.sender, _amount, newAmount);
    }

}
