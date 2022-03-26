import brownie
import pytest
from brownie import ZERO_ADDRESS, accounts, chain


# set up user with LP tokens and vote weight
@pytest.fixture(scope="module", autouse=True)
def setup(eps2, locker, voter, lp_tokens, pools, lp_staker, alice, bob, start_time):
    lp_tokens[0].setMinter(pools[0], {'from': alice})
    lp_tokens[1].setMinter(pools[1])

    for acct in [alice, bob]:
        eps2.mint(acct, 15000000 * 10 ** 18, {'from': alice})
        eps2.approve(locker, 2 ** 256 - 1, {"from": acct})
    delta = start_time - chain.time()
    chain.mine(timedelta=delta)
    locker.lock(alice, 15000000 * 10 ** 18, 30, {"from": alice})
    locker.lock(bob, 15000000 * 10 ** 18, 30, {"from": bob})


def test_unauthorized_add_pool(lp_staker, alice, lp_tokens):
    with brownie.reverts("Sender not incentiveVoting"):
        lp_staker.addPool(lp_tokens[0], {"from": alice})


def test_add_pool_week_0_or_1_reverts_week_2_passes(locker, lp_tokens, voter, pools, alice):
    assert locker.getWeek() == 0
    lp_tokens[0].setMinter(pools[0])
    # create a vote for a gauge
    with brownie.reverts("Cannot make vote in first two weeks"):
        voter.createTokenApprovalVote(lp_tokens[0], {"from": alice})

    # bump past first week
    chain.mine(timedelta=86400 * 7)
    assert locker.getWeek() == 1

    with brownie.reverts("Cannot make vote in first two weeks"):
        voter.createTokenApprovalVote(lp_tokens[0], {"from": alice})

    # bump past first week
    chain.mine(timedelta=86400 * 7)
    assert locker.getWeek() == 2

    voter.createTokenApprovalVote(lp_tokens[0], {"from": alice})
    # End users can set as 2**256-1 to vote with all available weight.
    voter.voteForTokenApproval(0, 2**256-1, {"from": alice})
    assert voter.isApproved(lp_tokens[0]) == True


def test_add_pool_registered_tokens(lp_staker, lp_tokens, voter, pools, alice):
    num_pools0 = lp_staker.poolLength()
    for index in range(5):
        # bump past first week
        chain.mine(timedelta=86400 * 14)
        # set the pool on the lpToken
        lp_tokens[index].setMinter(pools[index])
        # create a vote for a gauge
        voter.createTokenApprovalVote(lp_tokens[index], {"from": alice})
        # vote
        voter.voteForTokenApproval(index, 2**256-1, {"from": alice})
        # assert the token was approved
        assert voter.isApproved(lp_tokens[index]) == True
    num_pools1 = lp_staker.poolLength()
    # check that we have added the tokens to registeredTokens
    assert num_pools1 - num_pools0 == 5


def test_add_pool_last_reward_time(lp_staker, lp_tokens, voter, pools, alice):
    for index in range(5):
        # bump past first week
        chain.mine(timedelta=86400 * 14)
        # set the pool on the lpToken
        lp_tokens[index].setMinter(pools[index])
        # create a vote for a gauge
        voter.createTokenApprovalVote(lp_tokens[index], {"from": alice})
        # vote
        voter.voteForTokenApproval(index, 2**256-1, {"from": alice})
        # assert the token was approved
        assert voter.isApproved(lp_tokens[index]) == True

    for index in range(5):
        pr = lp_staker.poolInfo(lp_tokens[index])
        assert pr[2] > 0
