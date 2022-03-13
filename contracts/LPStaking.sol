// SPDX-License-Identifier: MIT

pragma solidity 0.8.12;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";


interface IIncentiveVoting {
    function getRewardsPerSecond(address _pool, uint256 _week) external view returns (uint256);
    function startTime() external view returns (uint256);
}

interface IERC20Mintable {
    function mint(address _to, uint256 _value) external returns (bool);
    function minter() external view returns (address);
}

interface ITokenLocker {
    function userWeight(address _user) external view returns (uint256);
    function totalWeight() external view returns (uint256);
}

interface IStableSwap {
    function withdraw_admin_fees() external;
}


// based on the Sushi MasterChef
// https://github.com/sushiswap/sushiswap/blob/master/contracts/MasterChef.sol
contract EllipsisLpStaking {
    using SafeERC20 for IERC20;

    // Info of each user.
    struct UserInfo {
        uint256 depositAmount;  // The amount of tokens deposited into the contract.
        uint256 adjustedAmount; // The user's effective balance after boosting, used to calculate emission rates.
        uint256 rewardDebt;
    }
    // Info of each pool.
    struct PoolInfo {
        uint256 adjustedSupply;
        uint256 rewardsPerSecond;
        uint256 lastRewardTime; // Last second that reward distribution occurs.
        uint256 accRewardPerShare; // Accumulated rewards per share, times 1e12. See below.
    }

    uint256 public immutable maxMintableTokens;
    uint256 public mintedTokens;

    // Info of each pool.
    address[] public registeredTokens;
    mapping(address => PoolInfo) public poolInfo;

    // token => user => Info of each user that stakes LP tokens.
    mapping(address => mapping(address => UserInfo)) public userInfo;
    // user => base claimable balance
    mapping(address => uint256) public userBaseClaimable;
    // The timestamp when reward mining starts.
    uint256 public immutable startTime;

    // account earning rewards => receiver of rewards for this account
    // if receiver is set to address(0), rewards are paid to the earner
    // this is used to aid 3rd party contract integrations
    mapping (address => address) public claimReceiver;

    // when set to true, other accounts cannot call
    // `deposit` or `claim` on behalf of an account
    mapping(address => bool) public blockThirdPartyActions;

    mapping(address => uint256) public lastFeeClaim;

    IERC20Mintable public immutable rewardToken;
    IIncentiveVoting public immutable incentiveVoting;
    ITokenLocker public immutable tokenLocker;

    event Deposit(
        address indexed caller,
        address indexed receiver,
        address indexed token,
        uint256 amount
    );

    event Withdraw(
        address indexed caller,
        address indexed receiver,
        address indexed token,
        uint256 amount
    );

    event EmergencyWithdraw(
        address indexed token,
        address indexed user,
        uint256 amount
    );
    event FeeClaimSuccess(address pool);
    event FeeClaimRevert(address pool);

    constructor(
        IERC20Mintable _rewardToken,
        IIncentiveVoting _incentiveVoting,
        ITokenLocker _tokenLocker,
        uint256 _maxMintable,
        address[] memory _initialPools
    )
    {
        startTime = _incentiveVoting.startTime();
        rewardToken = _rewardToken;
        incentiveVoting = _incentiveVoting;
        tokenLocker = _tokenLocker;
        maxMintableTokens = _maxMintable;

        for (uint256 i = 0; i < _initialPools.length; i++) {
            address token = _initialPools[i];
            require(poolInfo[token].lastRewardTime == 0);
            registeredTokens.push(token);
            poolInfo[token].lastRewardTime = block.timestamp;
        }
    }

    function addPool(address _token) external returns (bool) {
        require(msg.sender == address(incentiveVoting));
        require(poolInfo[_token].lastRewardTime == 0);
        registeredTokens.push(_token);
        poolInfo[_token].lastRewardTime = block.timestamp;
        return true;
    }

    function setClaimReceiver(address _receiver) external {
        claimReceiver[msg.sender] = _receiver;
    }

    function setBlockThirdPartyActions(bool _block) external {
        blockThirdPartyActions[msg.sender] = _block;
    }

    function poolLength() external view returns (uint256) {
        return registeredTokens.length;
    }

    function claimableReward(address _user, address[] calldata _tokens)
        external
        view
        returns (uint256[] memory)
    {
        uint256[] memory claimable = new uint256[](_tokens.length);
        for (uint256 i = 0; i < _tokens.length; i++) {
            address token = _tokens[i];
            PoolInfo storage pool = poolInfo[token];
            UserInfo storage user = userInfo[token][_user];
            (uint256 accRewardPerShare,) = _getRewardData(token);
            accRewardPerShare = accRewardPerShare + pool.accRewardPerShare;
            claimable[i] = user.depositAmount * accRewardPerShare / 1e12 - user.rewardDebt;
        }
        return claimable;
    }

    function _getRewardData(address _token) internal view returns (uint256 accRewardPerShare, uint256 rewardsPerSecond) {
        PoolInfo storage pool = poolInfo[_token];
        uint256 lpSupply = pool.adjustedSupply;
        uint256 start = startTime;
        uint256 currentWeek = (block.timestamp - start) / 604800;

        if (lpSupply == 0) {
            return (0, incentiveVoting.getRewardsPerSecond(_token, currentWeek));
        }

        uint256 lastRewardTime = pool.lastRewardTime;
        uint256 rewardWeek = (lastRewardTime - start) / 604800;
        rewardsPerSecond = pool.rewardsPerSecond;
        uint256 reward;
        uint256 duration;
        if (rewardWeek < currentWeek) {
            while (rewardWeek < currentWeek) {
                uint256 nextRewardTime = (rewardWeek + 1) * 604800 + start;
                duration = nextRewardTime - lastRewardTime;
                reward = reward + duration * rewardsPerSecond;
                rewardWeek += 1;
                rewardsPerSecond = incentiveVoting.getRewardsPerSecond(_token, rewardWeek);
                lastRewardTime = nextRewardTime;
            }
        }

        duration = block.timestamp - lastRewardTime;
        reward = reward + duration * rewardsPerSecond;
        return (reward * 1e12 / lpSupply, rewardsPerSecond);
    }

    // Update reward variables of the given pool to be up-to-date.
    function _updatePool(address _token) internal returns (uint256 accRewardPerShare) {
        PoolInfo storage pool = poolInfo[_token];
        uint256 lastRewardTime = pool.lastRewardTime;
        require(lastRewardTime > 0);
        if (block.timestamp <= lastRewardTime) {
            return pool.accRewardPerShare;
        }
        (accRewardPerShare, pool.rewardsPerSecond) = _getRewardData(_token);
        pool.lastRewardTime = block.timestamp;
        if (accRewardPerShare == 0) return pool.accRewardPerShare;
        accRewardPerShare = accRewardPerShare + pool.accRewardPerShare;
        pool.accRewardPerShare = accRewardPerShare;
        return accRewardPerShare;
    }

    function _mint(address _user, uint256 _amount) internal {
        uint256 minted = mintedTokens;
        if (minted + _amount > maxMintableTokens) {
            _amount = maxMintableTokens - minted;
        }
        if (_amount > 0) {
            mintedTokens = minted + _amount;
            address receiver = claimReceiver[_user];
            if (receiver == address(0)) receiver = _user;
            rewardToken.mint(receiver, _amount);
        }
    }

    // calculate adjusted balance and total supply, used for boost
    function _updateLiquidityLimits(address _user, address _token, uint256 _depositAmount, uint256 _accRewardPerShare) internal {
        uint256 userWeight = tokenLocker.userWeight(_user);
        uint256 adjustedAmount = _depositAmount * 40 / 100;
        if (userWeight > 0) {
            uint256 lpSupply = IERC20(_token).balanceOf(address(this));
            uint256 totalWeight = tokenLocker.totalWeight();
            uint256 boost = lpSupply * userWeight / totalWeight * 60 / 100;
            adjustedAmount += boost;
            if (adjustedAmount > _depositAmount) {
                adjustedAmount = _depositAmount;
            }
        }
        UserInfo storage user = userInfo[_token][_user];
        uint256 newAdjustedSupply = poolInfo[_token].adjustedSupply - user.adjustedAmount;
        user.adjustedAmount = adjustedAmount;
        poolInfo[_token].adjustedSupply = newAdjustedSupply + adjustedAmount;
        user.rewardDebt = adjustedAmount * _accRewardPerShare / 1e12;
    }

    // Deposit LP tokens into the contract. Also triggers a claim.
    function deposit(address _receiver, address _token, uint256 _amount) external {
        require(_amount > 0, "Cannot deposit zero");
        if (msg.sender != _receiver) {
            require(!blockThirdPartyActions[_receiver], "Cannot deposit on behalf of this account");
        }
        uint256 accRewardPerShare = _updatePool(_token);
        UserInfo storage user = userInfo[_token][_receiver];
        if (user.adjustedAmount > 0) {
            uint256 pending = user.adjustedAmount * accRewardPerShare / 1e12 - user.rewardDebt;
            if (pending > 0) {
                userBaseClaimable[_receiver] += pending;
            }
        }
        IERC20(_token).safeTransferFrom(
            address(msg.sender),
            address(this),
            _amount
        );
        uint256 depositAmount = user.depositAmount + _amount;
        user.depositAmount = depositAmount;
        _updateLiquidityLimits(_receiver, _token, depositAmount, accRewardPerShare);
        emit Deposit(msg.sender, _receiver, _token, _amount);
    }

    // Withdraw LP tokens. Also triggers a claim.
    function withdraw(address _receiver, address _token, uint256 _amount) external {
        require(_amount > 0, "Cannot withdraw zero");
        uint256 accRewardPerShare = _updatePool(_token);
        UserInfo storage user = userInfo[_token][msg.sender];
        uint256 depositAmount = user.depositAmount;
        require(depositAmount >= _amount, "withdraw: not good");

        uint256 pending = user.adjustedAmount * accRewardPerShare / 1e12 - user.rewardDebt;
        if (pending > 0) {
            userBaseClaimable[msg.sender] = userBaseClaimable[msg.sender] + pending;
        }
        depositAmount -= _amount;
        user.depositAmount = depositAmount;
        _updateLiquidityLimits(msg.sender, _token, depositAmount, accRewardPerShare);
        IERC20(_token).safeTransfer(_receiver, _amount);
        emit Withdraw(msg.sender, _receiver, _token, _amount);
    }

    // Withdraw without caring about rewards. EMERGENCY ONLY.
    function emergencyWithdraw(address _token) external {
        UserInfo storage user = userInfo[_token][msg.sender];

        uint256 amount = user.depositAmount;
        delete userInfo[_token][msg.sender];
        IERC20(_token).safeTransfer(address(msg.sender), amount);
        emit EmergencyWithdraw(_token, msg.sender, amount);
    }

    // Claim pending rewards for one or more pools.
    // Rewards are not received directly, they are minted by the rewardMinter.
    function claim(address _user, address[] calldata _tokens) external {
        if (msg.sender != _user) {
            require(!blockThirdPartyActions[_user], "Cannot claim on behalf of this account");
        }
        uint256 pending = userBaseClaimable[_user];
        userBaseClaimable[_user] = 0;
        for (uint i = 0; i < _tokens.length; i++) {
            address token = _tokens[i];
            uint256 accRewardPerShare = _updatePool(token);
            UserInfo storage user = userInfo[token][_user];
            uint256 rewardDebt = user.adjustedAmount * accRewardPerShare / 1e12;
            pending += rewardDebt - user.rewardDebt;
            _updateLiquidityLimits(_user, token, user.depositAmount, accRewardPerShare);

            // claim admin fees for each pool once per day
            if (lastFeeClaim[token] + 86400 < block.timestamp) {
                address pool = IERC20Mintable(token).minter();
                try IStableSwap(pool).withdraw_admin_fees() {
                    emit FeeClaimSuccess(pool);
                } catch {
                    emit FeeClaimRevert(pool);
                }
                lastFeeClaim[token] = block.timestamp;
            }
        }
        _mint(_user, pending);
    }

    function updateUserBoosts(address _user, address[] calldata _tokens) external {
        for (uint i = 0; i < _tokens.length; i++) {
            address token = _tokens[i];
            uint256 accRewardPerShare = _updatePool(token);
            UserInfo storage user = userInfo[token][_user];
            if (user.adjustedAmount > 0) {
                uint256 pending = user.adjustedAmount * accRewardPerShare / 1e12 - user.rewardDebt;
                if (pending > 0) {
                    userBaseClaimable[_user] += pending;
                }
            }
            _updateLiquidityLimits(_user, token, user.depositAmount, accRewardPerShare);
        }
    }

}
