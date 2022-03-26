import brownie
import pytest
from brownie import chain, ZERO_ADDRESS

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


def test_create_token_approval_vote(voter, locker, alice, lp_tokens):
    chain.mine(timedelta=86400 * 14)
    tx = voter.createTokenApprovalVote(lp_tokens[0], {"from": alice})
    assert tx.events['TokenApprovalVoteCreated']['token'] == lp_tokens[0]


def test_fails_first_week(voter, alice, lp_tokens):
    with brownie.reverts("Cannot make vote in first two weeks"):
        voter.createTokenApprovalVote(lp_tokens[0], {"from": alice})


def test_fails_not_enough_weight(voter, charlie, lp_tokens):
    chain.mine(timedelta=86400 * 14)
    with brownie.reverts("Not enough weight"):
        voter.createTokenApprovalVote(lp_tokens[0], {"from": charlie})


def test_fails_more_than_one_vote_per_week(voter, alice, lp_tokens):
    chain.mine(timedelta=86400 * 14)
    voter.createTokenApprovalVote(lp_tokens[0], {"from": alice})
    with brownie.reverts("One new vote per week"):
        voter.createTokenApprovalVote(lp_tokens[1], {"from": alice})


def test_token_approval_votes(voter, alice, lp_tokens):
    chain.mine(timedelta=86400 * 14)
    num0 = voter.tokenApprovalVotesLength()
    # asserting here should anyting in the setup ever change this
    assert num0 == 0
    tx = voter.createTokenApprovalVote(lp_tokens[0], {"from": alice})
    assert tx.events['TokenApprovalVoteCreated']['token'] == lp_tokens[0]
    num1 = voter.tokenApprovalVotesLength()
    assert num1 == 1
    tav = voter.tokenApprovalVotes(0)
    assert tav[0] == lp_tokens[0]


def test_multiple_token_approval_votes(voter, alice, bob, lp_tokens):
    chain.mine(timedelta=86400 * 14)
    num0 = voter.tokenApprovalVotesLength()
    # asserting here should anyting in the setup ever change this
    assert num0 == 0
    tx = voter.createTokenApprovalVote(lp_tokens[0], {"from": alice})
    tx2 = voter.createTokenApprovalVote(lp_tokens[1], {"from": bob})
    assert tx.events['TokenApprovalVoteCreated']['token'] == lp_tokens[0]
    assert tx2.events['TokenApprovalVoteCreated']['token'] == lp_tokens[1]
    num1 = voter.tokenApprovalVotesLength()
    assert num1 == 2
    tav = voter.tokenApprovalVotes(0)
    assert tav[0] == lp_tokens[0]
    tav2 = voter.tokenApprovalVotes(1)
    assert tav2[0] == lp_tokens[1]


# send lp token for approval
def test_vote_same_token_twice_for_approval_vote(voter, lp_tokens, alice, bob):
    chain.mine(timedelta=86400 * 14)
    # first vote
    voter.createTokenApprovalVote(lp_tokens[0], {"from": alice})
    voter.voteForTokenApproval(0, 2**256-1, {"from": alice})

    chain.mine(timedelta=86400 * 14)
    assert voter.isApproved(lp_tokens[0]) == True

    with brownie.reverts("Already approved"):
        voter.createTokenApprovalVote(lp_tokens[0], {"from": alice})


# this doesn't return a revert msg
def test_vote_for_non_lp_token(voter, alice, pools):
    chain.mine(timedelta=86400 * 14)
    with brownie.reverts():
        voter.createTokenApprovalVote(pools[0], {"from": alice})
