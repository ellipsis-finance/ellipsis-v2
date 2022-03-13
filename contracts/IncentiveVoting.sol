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
    function poolInfo(address _pool) external view returns (uint256, uint256, uint256);
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
        uint256 requiredWeight;
        uint256 givenWeight;
    }

    // token -> week -> weight allocated
    mapping(address => mapping(uint256 => uint256)) public tokenVotes;

    // user -> week -> weight used
    mapping(address => mapping(uint256 => uint256)) public userVotes;

    // week -> total weight allocated
    mapping(uint256 => uint256) public totalVotes;

    // token -> last week rewards were distributed
    mapping(address => uint256) public lastRewardedWeek;

    // data about token approval votes
    TokenApprovalVote[] public tokenApprovalVotes;

    // voteId -> token -> has voted for token approval?
    mapping(uint256 => mapping (address =>bool)) hasVoted;

    // minimum support required in an approval vote, as a % out of 100
    uint256 public tokenApprovalQuorumPct;

    // user -> timestamp of last created token approval vote
    mapping(address => uint256) public lastVote;

    uint256 constant WEEK = 86400 * 7;
    uint256 public startTime;

    ITokenLocker public tokenLocker;
    ILpStaking public lpStaking;

    mapping(address => bool) approvedTokens;

    // Total amount of the protocol token distributed each week.
    // Each week a new value is pushed onto the array.
    uint256[] public rewardsPerSecond;

    event TokenApprovalVoteCreated(
        address indexed creator,
        address indexed token,
        uint256 startTime,
        uint256 week,
        uint256 requiredWeight,
        uint256 voteIndex
    );

    event VotedForTokenApproval(
        address indexed voter,
        uint256 indexed voteIndex,
        uint256 votedWeight,
        uint256 givenWeight,
        uint256 requiredWeight,
        bool isApproved
    );

    event VotedForIncentives(
        address indexed voter,
        address[] tokens,
        uint256[] weights,
        uint256 usedWeight,
        uint256 totalWeight
    );

    event ApprovalQuorumSet(
        address caller,
        uint256 oldQuorumPct,
        uint256 newQuorumPct
    );

    constructor(
        ITokenLocker _tokenLocker,
        uint256 _initialRewardsPerSecond,
        uint256 _quorumPct
    ) {
        tokenApprovalQuorumPct = _quorumPct;
        tokenLocker = _tokenLocker;
        // start at +1 week to handle the default value in `lastRewardedWeek`
        // without this, tokens would not receive emissions in the first week
        startTime = _tokenLocker.startTime() - WEEK;

        rewardsPerSecond.push(_initialRewardsPerSecond);
    }

    function setLpStaking(ILpStaking _lpStaking) external {
        require(address(lpStaking) == address(0));
        lpStaking = _lpStaking;
    }

    function tokenApprovalVotesLength() external view returns (uint256) {
        return tokenApprovalVotes.length;
    }

    function getWeek() public view returns (uint256) {
        if (startTime >= block.timestamp) return 0;
        return (block.timestamp - startTime) / 604800;
    }

    /**
        @notice Get the amount of unused weight for for the current week being voted on
        @param _user Address to query
        @return uint Amount of unused weight
     */
    function availableVoteWeight(address _user)
        external
        view
        returns (uint256)
    {
        uint256 week = getWeek();
        uint256 usedWeight = userVotes[_user][week];
        uint256 totalWeight = tokenLocker.userWeight(_user);
        return totalWeight - usedWeight;
    }

    /**
        @notice Allocate weight toward LP tokens to receive emissions in the following week
        @dev A user may vote as many times as they like within a week, so long as their total
             available weight is not exceeded. If they receive additional weight by locking more
             tokens within `tokenLocker`, they can vote immediately.

             Vote weight can only be added - not modified or removed. Votes only apply to the
             following week - they do not carry over. A user must resubmit their vote each
             week.
        @param _tokens List of addresses of LP tokens to vote for
        @param _weights Weight to allocate to `_tokens`. Values are additive, they do
                        not include previous votes. For example, if you have already
                        allocated a weight of 100 and wish to allocated a total of 300,
                        `_weight` should be given as 200.
     */
    function vote(address[] calldata _tokens, uint256[] calldata _weights) external {
        require(_tokens.length == _weights.length, "Input length mismatch");

        // update rewards per second, if required
        uint256 week = getWeek();
        uint256 length = rewardsPerSecond.length;
        if (length < week / 4) {
            uint256 perSecond = rewardsPerSecond[length-1];
            while (length < week / 4) {
                perSecond = perSecond * 99 / 100;
                length += 1;
                rewardsPerSecond.push(perSecond);
            }
        }

        // make sure user has not exceeded available weight
        uint256 usedWeight = userVotes[msg.sender][week];

        // update accounting for this week's votes
        for (uint i = 0; i < _tokens.length; i++) {
            address token = _tokens[i];
            uint256 weight = _weights[i];
            require(approvedTokens[token], "Not approved for incentives");
            tokenVotes[token][week] += weight;
            totalVotes[week] += weight;
            usedWeight += weight;
        }

        uint256 totalWeight = tokenLocker.userWeight(msg.sender);
        require(usedWeight <= totalWeight, "Available weight exceeded");
        userVotes[msg.sender][week] = usedWeight;

        emit VotedForIncentives(
            msg.sender,
            _tokens,
            _weights,
            usedWeight,
            totalWeight
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
        require(!approvedTokens[_token], "Already approved");
        uint256 week = getWeek();
        require(week > 1, "Cannot make vote in first week");

        // verify that claiming admin fees works for the pool associated with
        // this LP token. if the call does not work, the token is likely not
        // an LP token or contains an incompatible asset.
        address pool = IERC20Mintable(_token).minter();
        IStableSwap(pool).withdraw_admin_fees();

        week -= 2;
        uint256 weight = tokenLocker.weeklyWeightOf(msg.sender, week);

        // minimum weight of 50,000 and max one vote per week to prevent spamming votes
        require(weight >= 50000 * 10**18, "Not enough weight");
        require(
            lastVote[msg.sender] + WEEK <= block.timestamp,
            "One new vote per week"
        );
        lastVote[msg.sender] = block.timestamp;

        uint256 required = tokenLocker.weeklyTotalWeight(week) * tokenApprovalQuorumPct / 100;
        tokenApprovalVotes.push(
            TokenApprovalVote({
                token: _token,
                startTime: uint40(block.timestamp),
                week: uint16(week),
                requiredWeight: required,
                givenWeight: 0
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

    /**
        @notice Vote in favor of approving a new token for protocol emissions
        @dev Votes last for one week. Weight for voting is based on the last
             completed week at the time the vote was created. A vote passes
             once the percent of weight given exceeds `tokenApprovalQuorumPct`.
             It is not possible to vote against a proposed token, users who
             wish to do so should instead abstain from voting.
        @param _voteIndex Array index referencing the vote
     */
    function voteForTokenApproval(uint256 _voteIndex) external {
        TokenApprovalVote storage vote = tokenApprovalVotes[_voteIndex];
        require(!hasVoted[_voteIndex][msg.sender], "Already voted");
        require(vote.startTime > block.timestamp - WEEK, "Vote has ended");
        require(!approvedTokens[vote.token], "Already approved");

        hasVoted[_voteIndex][msg.sender] = true;
        uint256 weight = tokenLocker.weeklyWeightOf(msg.sender, vote.week);
        vote.givenWeight = vote.givenWeight + weight;

        bool isApproved = vote.givenWeight >= vote.requiredWeight;
        if (isApproved) {
            approvedTokens[vote.token] = true;
            lpStaking.addPool(vote.token);
        }

        emit VotedForTokenApproval(
            msg.sender,
            _voteIndex,
            weight,
            vote.givenWeight,
            vote.requiredWeight,
            isApproved
        );
    }

    function getPoolRewardsPerSecond(address _token, uint256 _week) external view returns (uint256) {
        uint256 votes = tokenVotes[_token][_week];
        if (votes == 0) return 0;
        return rewardsPerSecond[_week / 4] * votes / totalVotes[_week];
    }

    /**
        @dev Modify the required quorum for token approval votes.
        Hopefully this is never needed.
     */
    function setTokenApprovalQuorum(uint256 _quorumPct) external onlyOwner {
        emit ApprovalQuorumSet(msg.sender, tokenApprovalQuorumPct, _quorumPct);
        tokenApprovalQuorumPct = _quorumPct;
    }


    /**
        @dev Modify the approval for a token to receive incentives.
        This can only be called on tokens that were already voted in, it cannot
        be used to bypass the voting process. It is intended to block emissions in
        case of an exploit or act of maliciousness from a token within an approved pool.
     */

    function setTokenApproval(address _token, bool _isApproved) external onlyOwner {
        if (!approvedTokens[_token]) {
            (,uint256 lastRewardTime,) = lpStaking.poolInfo(_token);
            require(lastRewardTime != 0, "Token must be voted in");
        }
        approvedTokens[_token] = _isApproved;
    }

}
