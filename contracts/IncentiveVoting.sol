pragma solidity 0.8.12;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";


interface ITokenLocker {

    function userWeight(address _user) external view returns (uint256);
    function weeklyTotalWeight(uint256 _week) external view returns (uint256);
    function weeklyWeightOf(address _user, uint256 _week)
        external
        view
        returns (uint256);
    function startTime() external view returns (uint256);
}

interface ILpStaking {
    function poolInfo(address _pool) external view returns (uint256, uint256, uint256, uint256);
    function addPool(address _token) external returns (bool);
}

interface IStableSwap {
    function withdraw_admin_fees() external;
}

interface IERC20Mintable {
    function minter() external view returns (address);
}


contract IncentiveVoting is Ownable {

    struct TokenApprovalVote {
        address token;
        uint40 startTime;
        uint16 week;
        uint256 requiredVotes;
        uint256 givenVotes;
    }
    struct Vote {
        address token;
        uint256 votes;
    }

    // token -> week -> votes received
    mapping(address => uint256[65535]) public tokenVotes;

    // user -> week -> votes used
    mapping(address => uint256[65535]) public userVotes;

    // user -> token -> week -> votes for pool
    mapping(address => mapping(address => uint256[65535])) public userTokenVotes;

    // week -> total votes used
    uint256[65535] public totalVotes;

    // data about token approval votes
    TokenApprovalVote[] public tokenApprovalVotes;

    // voteId -> user -> supporting votes for token approval
    mapping(uint256 => mapping(address => uint256)) public userTokenApprovalVotes;

    // minimum support required in an approval vote, as a % out of 100
    uint256 public tokenApprovalQuorumPct;
    uint256 public pendingTokenApprovalQuorumPct;
    uint256 public pendingTokenApprovalQuorumTime;

    // user -> timestamp of last created token approval vote
    mapping(address => uint256) public lastVote;

    uint256 constant WEEK = 86400 * 7;
    uint256 public startTime;

    ITokenLocker public tokenLocker;
    ILpStaking public lpStaking;

    mapping(address => bool) public isApproved;
    address[] public approvedTokens;

    // The amount of EPX tokens minted each second in a given period.
    // Each item represents a 4 week epoch. New values are pushed onto
    // the array over time as users call `vote`.
    uint256[] public rewardsPerSecond;

    // Minimum weight to create a new token approval vote
    uint256 public immutable NEW_TOKEN_APPROVAL_VOTE_MIN_WEIGHT;

    event TokenApprovalVoteCreated(
        address indexed creator,
        address indexed token,
        uint256 startTime,
        uint256 week,
        uint256 requiredVotes,
        uint256 voteIndex
    );

    event VotedForTokenApproval(
        address indexed voter,
        uint256 indexed voteIndex,
        uint256 newVotes,
        uint256 totalVotes,
        uint256 requiredVotes,
        bool isApproved
    );

    event VotedForIncentives(
        address indexed voter,
        address[] tokens,
        uint256[] votes,
        uint256 userVotesUsed,
        uint256 totalUserVotes
    );

    event PendingApprovalQuorumSet(
        address caller,
        uint256 quorumPct,
        uint256 pendingQuorumPct
    );

    event ApprovalQuorumSet(
        address caller,
        uint256 previousQuorumPct,
        uint256 quorumPct
    );

    constructor(
        ITokenLocker _tokenLocker,
        uint256 _initialRewardsPerSecond,
        uint256 _quorumPct,
        uint256 _tokenApprovalMinWeight
    ) {
        require(_tokenApprovalMinWeight > 1e18, "Incorrect precision!");

        tokenApprovalQuorumPct = _quorumPct;
        NEW_TOKEN_APPROVAL_VOTE_MIN_WEIGHT = _tokenApprovalMinWeight;
        tokenLocker = _tokenLocker;
        startTime = _tokenLocker.startTime();

        rewardsPerSecond.push(_initialRewardsPerSecond);
    }

    function setLpStaking(ILpStaking _lpStaking, address[] memory _initialApprovedTokens) external {
        require(address(lpStaking) == address(0));
        lpStaking = _lpStaking;
        for (uint i = 0; i < _initialApprovedTokens.length; i++) {
            address token = _initialApprovedTokens[i];
            isApproved[token] = true;
            approvedTokens.push(token);
            _lpStaking.addPool(token);
        }
    }

    function tokenApprovalVotesLength() external view returns (uint256) {
        return tokenApprovalVotes.length;
    }

    function approvedTokensLength() external view returns (uint256) {
        return approvedTokens.length;
    }

    function getWeek() public view returns (uint256) {
        if (startTime >= block.timestamp) return 0;
        return (block.timestamp - startTime) / 604800;
    }

    /**
        @notice Get data on the current votes made in the active week
        @return _totalVotes Total number of votes this week for all pools
        @return _voteData Dynamic array of (token address, votes for token)
     */
    function getVotes(uint256 _week) external view returns (uint256 _totalVotes, Vote[] memory _voteData) {
        _voteData = new Vote[](approvedTokens.length);
        for (uint i = 0; i < _voteData.length; i++) {
            address token = approvedTokens[i];
            _voteData[i] = Vote({token: token, votes: tokenVotes[token][_week]});
        }
        return (totalVotes[_week], _voteData);
    }


    /**
        @notice Get data on current votes `_user` has made in the active week
        @return _totalVotes Total number of votes from `_user` this week for all pools
        @return _voteData Dynamic array of (token address, votes for token)
     */
    function getUserVotes(address _user, uint256 _week)
        external
        view
        returns (uint256 _totalVotes, Vote[] memory _voteData)
    {
        _voteData = new Vote[](approvedTokens.length);
        for (uint i = 0; i < _voteData.length; i++) {
            address token = approvedTokens[i];
            _voteData[i] = Vote({token: token, votes: userTokenVotes[_user][token][_week]});
        }
        return (userVotes[_user][_week], _voteData);
    }

    /**
        @notice Get the amount of unused votes for for the current week being voted on
        @param _user Address to query
        @return uint Amount of unused votes
     */
    function availableVotes(address _user) external view returns (uint256) {
        uint256 week = getWeek();
        uint256 usedVotes = userVotes[_user][week];
        uint256 totalVotes = tokenLocker.userWeight(_user) / 1e18;
        return totalVotes - usedVotes;
    }

    /**
        @notice Allocate votes toward LP tokens to receive emissions in the following week
        @dev A user may vote as many times as they like within a week, so long as their total
             available votes are not exceeded. If they receive additional votes by locking more
             tokens within `tokenLocker`, they can vote immediately.

             Votes can only be added - not modified or removed. Votes only apply to the
             following week - they do not carry over. A user must resubmit their vote each
             week.
        @param _tokens List of addresses of LP tokens to vote for
        @param _votes Votes to allocate to `_tokens`. Values are additive, they do
                        not include previous votes. For example, if you have already
                        allocated 100 votes and wish to allocate a total of 300,
                        the vote amount should be given as 200.
     */
    function vote(address[] calldata _tokens, uint256[] calldata _votes) external {
        require(_tokens.length == _votes.length, "Input length mismatch");

        // update rewards per second, if required
        uint256 week = getWeek();
        uint256 length = rewardsPerSecond.length;
        if (length <= week / 4) {
            uint256 perSecond = rewardsPerSecond[length-1];
            while (length <= week / 4) {
                perSecond = perSecond * 99 / 100;
                length += 1;
                rewardsPerSecond.push(perSecond);
            }
        }

        // update accounting for this week's votes
        uint256 usedVotes = userVotes[msg.sender][week];
        for (uint i = 0; i < _tokens.length; i++) {
            address token = _tokens[i];
            uint256 amount = _votes[i];
            require(isApproved[token], "Not approved for incentives");
            tokenVotes[token][week] += amount;
            totalVotes[week] += amount;
            userTokenVotes[msg.sender][token][week] += amount;
            usedVotes += amount;
        }

        // make sure user has not exceeded available votes
        uint256 totalVotes = tokenLocker.userWeight(msg.sender) / 1e18;
        require(usedVotes <= totalVotes, "Available votes exceeded");
        userVotes[msg.sender][week] = usedVotes;

        emit VotedForIncentives(
            msg.sender,
            _tokens,
            _votes,
            usedVotes,
            totalVotes
        );
    }

    /**
        @notice Create a new vote to enable protocol emissions on a given token
        @dev Emissions are only available to approved LP tokens. This prevents
             incentives being given to pools with malicious assets. We trust
             lockers to vote in the best longterm interests of the protocol :)
        @param _token Token address to create a vote for
        @return _voteIndex uint Index value used to reference the vote
     */
    function createTokenApprovalVote(address _token)
        external
        returns (uint256 _voteIndex)
    {
        require(!isApproved[_token], "Already approved");
        // wait 2 weeks to allow approval votes, to ensure sufficient locked balances
        uint256 week = getWeek();
        require(week > 1, "Cannot make vote in first two weeks");

        // verify that claiming admin fees works for the pool associated with
        // this LP token. we verify this behaviour now to avoid later isssues
        // in `EllipsisLpStaking.claim` if the token does not belong to a pool
        // or contains an incompatible asset.
        address pool = IERC20Mintable(_token).minter();
        IStableSwap(pool).withdraw_admin_fees();

        week -= 1;
        uint256 weight = tokenLocker.weeklyWeightOf(msg.sender, week);
        // minimum weight and max one vote per week to prevent spamming votes
        require(weight >= NEW_TOKEN_APPROVAL_VOTE_MIN_WEIGHT, "Not enough weight");
        require(lastVote[msg.sender] + WEEK <= block.timestamp, "One new vote per week");
        lastVote[msg.sender] = block.timestamp;

        uint256 required = tokenLocker.weeklyTotalWeight(week) * tokenApprovalQuorumPct / 100 / 1e18;
        tokenApprovalVotes.push(
            TokenApprovalVote({
                token: _token,
                startTime: uint40(block.timestamp),
                week: uint16(week),
                requiredVotes: required,
                givenVotes: 0
            })
        );

        uint256 voteIdx = tokenApprovalVotes.length - 1;
        emit TokenApprovalVoteCreated(
            msg.sender,
            _token,
            block.timestamp,
            week,
            required,
            voteIdx
        );
        return voteIdx;
    }

    function availableTokenApprovalVotes(address _user, uint256 _voteIndex)
        external
        view
        returns (uint256 _remainingVotes)
    {
        TokenApprovalVote storage vote = tokenApprovalVotes[_voteIndex];
        if (vote.startTime <= block.timestamp - WEEK) return 0;
        uint256 totalVotes = tokenLocker.weeklyWeightOf(_user, vote.week) / 1e18;
        return totalVotes - userTokenApprovalVotes[_voteIndex][_user];
    }

    /**
        @notice Vote in favor of approving a new token for protocol emissions
        @dev Votes last for one week. Weight for voting is based on the last
             completed week at the time the vote was created. A vote passes
             once the percent of weight given exceeds `tokenApprovalQuorumPct`.
             It is not possible to vote against a proposed token, users who
             wish to do so should instead abstain from voting.
        @param _voteIndex Array index referencing the vote
        @param _yesVotes Number of votes to cast in favor. End users can set as
                         2**256-1 to vote with all available weight. Integragors
                         may wish to vote with only a portion of their available
                         weight, in order to more accurately reflect a sub-vote
                         within their userbase.
     */
    function voteForTokenApproval(uint256 _voteIndex, uint256 _yesVotes) external {
        TokenApprovalVote storage vote = tokenApprovalVotes[_voteIndex];
        require(vote.startTime > block.timestamp - WEEK, "Vote has ended");
        require(!isApproved[vote.token], "Already approved");

        uint256 totalVotes = tokenLocker.weeklyWeightOf(msg.sender, vote.week) / 1e18;
        uint256 usedVotes = userTokenApprovalVotes[_voteIndex][msg.sender];
        if (_yesVotes == type(uint256).max) {
            _yesVotes = totalVotes - usedVotes;
        }
        usedVotes += _yesVotes;
        require(usedVotes <= totalVotes, "Exceeds available votes");

        userTokenApprovalVotes[_voteIndex][msg.sender] = usedVotes;
        vote.givenVotes += _yesVotes;

        if (vote.givenVotes >= vote.requiredVotes) {
            isApproved[vote.token] = true;
            approvedTokens.push(vote.token);
            lpStaking.addPool(vote.token);
        }

        emit VotedForTokenApproval(
            msg.sender,
            _voteIndex,
            _yesVotes,
            vote.givenVotes,
            vote.requiredVotes,
            isApproved[vote.token]
        );
    }

    /**
        @dev Calculate and return the rewards per second for a given LP token.
             Called by `EllipsisLpStaker` when determining the emissions that each
             pool is entitled to.
     */
    function getRewardsPerSecond(address _token, uint256 _week) external view returns (uint256) {
        if (_week == 0) return 0;
        // weekly rewards are calculated based on the previous week's votes
        _week -= 1;

        uint256 votes = tokenVotes[_token][_week];
        if (votes == 0) return 0;

        return rewardsPerSecond[_week / 4] * votes / totalVotes[_week];
    }

    /**
        @notice Commit a change to the required quorum for token approval votes.
        @dev Quorum can only be modified within a defined range of 10-50%. A three day
             delay is required between commiting and applying the change, in order to
             discourge malicious actions from the contract owner.
     */
    function commitTokenApprovalQuorum(uint256 _quorumPct) external onlyOwner {
        require(_quorumPct >= 10 && _quorumPct <= 50, "Invalid parameter");
        pendingTokenApprovalQuorumPct = _quorumPct;
        pendingTokenApprovalQuorumTime = block.timestamp + 86400 * 3;
        emit PendingApprovalQuorumSet(msg.sender, tokenApprovalQuorumPct, _quorumPct);
    }

    /**
        @notice Apply a change to the required quorum for token approval votes
     */
    function applyTokenApprovalQuorum() external {
        uint256 quorum = pendingTokenApprovalQuorumPct;
        require(quorum > 0, "No pending value set");
        require(pendingTokenApprovalQuorumTime < block.timestamp, "Delay has not passed");
        pendingTokenApprovalQuorumPct = 0;
        pendingTokenApprovalQuorumTime = 0;

        emit ApprovalQuorumSet(msg.sender, tokenApprovalQuorumPct, quorum);
        tokenApprovalQuorumPct = quorum;
    }

    /**
        @notice Modify the approval for a token to receive incentives.
        @dev This can only be called on tokens that were already voted in, it cannot
        be used to bypass the voting process. It is intended to block emissions in
        case of an exploit or act of maliciousness from a token within an approved pool.
     */
    function setTokenApproval(address _token, bool _isApproved) external onlyOwner {
        if (!isApproved[_token]) {
            (,,uint256 lastRewardTime,) = lpStaking.poolInfo(_token);
            require(lastRewardTime != 0, "Token must be voted in");
        }
        isApproved[_token] = _isApproved;
    }

}
