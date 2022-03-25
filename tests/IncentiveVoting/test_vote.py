import brownie
import pytest
from brownie import chain, ZERO_ADDRESS


def validate_total_weight(data, vote_count):
    assert len(data) == vote_count + 2
    weight = sum(abs(i[1]) for i in data[:-2])
    assert sum(abs(i[1]) for i in data) == weight + (weight * 11 // 200) * 2


@pytest.fixture(scope="module")
def setup_gauges(voter, lp_tokens, pools, locker, alice, bob):
    locker.lock(alice, 50000 * 10 ** 18, 52, {"from": alice})
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


@pytest.fixture(scope="module", autouse=True)
def setup(eps2, locker, voter, lp_tokens, pools, lp_staker, alice, bob, start_time):
    lp_tokens[0].setMinter(pools[0], {'from': alice})
    lp_tokens[1].setMinter(pools[1])

    for acct in [alice, bob]:
        eps2.mint(acct, 1500000 * 10 ** 18, {'from': alice})
        eps2.approve(locker, 2 ** 256 - 1, {"from": acct})
    delta = start_time - chain.time()
    chain.mine(timedelta=delta)
    locker.lock(alice, 100000 * 10 ** 18, 1, {"from": alice})
    locker.lock(bob, 200000 * 10 ** 18, 2, {"from": bob})


def test_available_vote_weight(voter, alice, bob):
    assert voter.availableVotes(alice) == 100000
    assert voter.availableVotes(bob) == 400000
    chain.mine(timedelta=86400 * 7)
    assert voter.availableVotes(alice) == 0
    assert voter.availableVotes(bob) == 200000


def test_locking_affects_available_immediately(voter, locker, alice):
    locker.lock(alice, 10**18, 16, {'from': alice})
    assert voter.availableVotes(alice) == 100016


# don't think we need getCurrentVotes
# def test_vote(voter, alice, pools, setup_gauges, lp_tokens):
#     tx = voter.voteForTokenApproval(pools[0], 1000, 2**256-1, {'from': alice})
#     week = voter.getWeek()
#     assert voter.userVotes(alice, week) == 1000
#     rem = voter.poolVotes(pools[0], week)
#     assert voter.poolVotes(pools[0], week) == 1000

#     data = voter.poolVotes()
#     assert data[0] == (pools[0], 1000)
#     validate_total_weight(data, 1)



# def test_increase_vote(voter, alice, regular_gauges, protected_gauges):
#     voter.voteForPool([regular_gauges[0]], [400], {'from': alice})
#     voter.voteForPool([regular_gauges[0]], [600], {'from': alice})

#     assert voter.userVotes(alice, 0) == 1000
#     assert voter.poolVotes(regular_gauges[0], 0) == 1000

#     data = voter.getCurrentVotes()
#     assert data[0] == (regular_gauges[0], 1000)
#     validate_total_weight(data, 1)


# def test_vote_lower(voter, alice, bob, regular_gauges, protected_gauges):
#     voter.voteForPool([regular_gauges[0]], [1000], {'from': alice})
#     voter.voteForPool([regular_gauges[2]], [500], {'from': bob})

#     assert voter.userVotes(alice, 0) == 1000
#     assert voter.userVotes(bob, 0) == 500
#     assert voter.poolVotes(regular_gauges[0], 0) == 1000
#     assert voter.poolVotes(regular_gauges[2], 0) == 500

#     data = voter.getCurrentVotes()
#     assert data[:-2] == [(regular_gauges[0], 1000), (regular_gauges[2], 500)]
#     validate_total_weight(data, 2)


# def test_vote_higher(voter, alice, regular_gauges, protected_gauges):
#     voter.voteForPool([regular_gauges[0]], [1000], {'from': alice})
#     voter.voteForPool([regular_gauges[2]], [3000], {'from': alice})
#     data = voter.getCurrentVotes()

#     assert data[:-2] == [(regular_gauges[0], 1000), (regular_gauges[2], 3000)]
#     validate_total_weight(data, 2)


# def test_vote_higher_lower(voter, alice, bob, regular_gauges, protected_gauges):
#     voter.voteForPool([regular_gauges[0]], [1000], {'from': alice})
#     voter.voteForPool([regular_gauges[2]], [-3000], {'from': bob})
#     voter.voteForPool([regular_gauges[1]], [500], {'from': alice})

#     assert voter.userVotes(alice, 0) == 1500
#     assert voter.userVotes(bob, 0) == 3000
#     assert voter.poolVotes(regular_gauges[0], 0) == 1000
#     assert voter.poolVotes(regular_gauges[1], 0) == 500
#     assert voter.poolVotes(regular_gauges[2], 0) == -3000

#     data = voter.getCurrentVotes()
#     assert data[:-2] == [
#         (regular_gauges[0], 1000),
#         (regular_gauges[2], -3000),
#         (regular_gauges[1], 500)
#     ]
#     validate_total_weight(data, 3)


# def test_vote_lower_higher(voter, alice, regular_gauges):
#     voter.voteForPool([regular_gauges[0]], [-1000], {'from': alice})
#     voter.voteForPool([regular_gauges[1]], [500], {'from': alice})
#     voter.voteForPool([regular_gauges[2]], [3000], {'from': alice})
#     data = voter.getCurrentVotes()

#     assert data[:-2] == [
#         (regular_gauges[0], -1000),
#         (regular_gauges[1], 500),
#         (regular_gauges[2], 3000)
#     ]
#     validate_total_weight(data, 3)


# def test_vote_multiple_same_call(voter, alice, regular_gauges):
#     voter.voteForPool(
#         [regular_gauges[0], regular_gauges[1], regular_gauges[2]],
#         [-1000, 500, 3000],
#         {'from': alice}
#     )
#     data = voter.getCurrentVotes()

#     assert data[:-2] == [
#         (regular_gauges[0], -1000),
#         (regular_gauges[1], 500),
#         (regular_gauges[2], 3000),
#     ]


# def test_vote_for_hardcoded_two(voter, alice, regular_gauges, protected_gauges):
#     voter.voteForPool([regular_gauges[0]], [-1000], {'from': alice})
#     voter.voteForPool([protected_gauges[1]], [500], {'from': alice})
#     data = voter.getCurrentVotes()
#     assert data == [
#         (regular_gauges[0], -1000),
#         (protected_gauges[1], 582),
#         (protected_gauges[0], 82),
#         (ZERO_ADDRESS, 0),
#     ]


# def test_vote_for_hardcoded_one(voter, alice, regular_gauges, protected_gauges):
#     voter.voteForPool([regular_gauges[0]], [-500], {'from': alice})
#     voter.voteForPool([protected_gauges[0]], [500], {'from': alice})
#     voter.voteForPool([regular_gauges[2]], [500], {'from': alice})

#     data = voter.getCurrentVotes()
#     assert data == [
#         (regular_gauges[0], -500),
#         (protected_gauges[0], 582),
#         (regular_gauges[2], 500),
#         (ZERO_ADDRESS, 0),
#         (protected_gauges[1], 82),
#     ]


# def test_vote_for_hardcoded_both(voter, alice, regular_gauges, protected_gauges):
#     voter.voteForPool([regular_gauges[0]], [-200], {'from': alice})
#     voter.voteForPool([protected_gauges[0]], [500], {'from': alice})
#     voter.voteForPool([protected_gauges[1]], [800], {'from': alice})

#     data = voter.getCurrentVotes()
#     assert data == [
#         (regular_gauges[0], -200),
#         (protected_gauges[0], 582),
#         (protected_gauges[1], 882),
#         (ZERO_ADDRESS, 0),
#         (ZERO_ADDRESS, 0),
#     ]


# def test_no_votes(voter, protected_gauges):
#     data = voter.getCurrentVotes()
#     assert data == [
#         (protected_gauges[0], 1),
#         (protected_gauges[1], 1),
#     ]


# def test_no_votes_this_week(voter, alice, regular_gauges, protected_gauges):
#     voter.voteForPool([regular_gauges[0]], [-200], {'from': alice})
#     chain.mine(timedelta=86400 * 7 + 1)
#     data = voter.getCurrentVotes()
#     assert data == [
#         (protected_gauges[0], 1),
#         (protected_gauges[1], 1),
#     ]


# def test_net_vote_weight_zero(voter, alice, regular_gauges, protected_gauges):
#     voter.voteForPool([regular_gauges[0]], [200], {'from': alice})
#     voter.voteForPool([regular_gauges[0]], [-200], {'from': alice})
#     data = voter.getCurrentVotes()
#     assert data == [
#         (protected_gauges[0], 1),
#         (protected_gauges[1], 1),
#     ]


# def test_net_vote_weight_zero_single_call(voter, alice, regular_gauges, protected_gauges):
#     voter.voteForPool([regular_gauges[0], regular_gauges[0]], [200, -200], {'from': alice})

#     assert voter.userVotes(alice, 0) == 400
#     assert voter.poolVotes(regular_gauges[0], 0) == 0

#     data = voter.getCurrentVotes()
#     assert data == [
#         (protected_gauges[0], 1),
#         (protected_gauges[1], 1),
#     ]


# def test_net_vote_weight_zero_shifts_other(voter, alice, regular_gauges, protected_gauges):
#     voter.voteForPool([regular_gauges[0]], [200], {'from': alice})
#     voter.voteForPool([regular_gauges[1]], [300], {'from': alice})
#     voter.voteForPool([regular_gauges[2]], [500], {'from': alice})
#     voter.voteForPool([regular_gauges[0]], [-200], {'from': alice})
#     data = voter.getCurrentVotes()
#     assert data[:-2] == [
#         (regular_gauges[2], 500),
#         (regular_gauges[1], 300),
#     ]


# def test_net_vote_weight_zero_shifts_other2(voter, alice, regular_gauges, protected_gauges):
#     voter.voteForPool([regular_gauges[0]], [200], {'from': alice})
#     voter.voteForPool([regular_gauges[1]], [300], {'from': alice})
#     voter.voteForPool([regular_gauges[2]], [500], {'from': alice})
#     voter.voteForPool([regular_gauges[0]], [-200], {'from': alice})
#     voter.voteForPool([regular_gauges[3]], [300], {'from': alice})
#     voter.voteForPool([regular_gauges[2]], [400], {'from': alice})
#     data = voter.getCurrentVotes()
#     assert data[:-2] == [
#         (regular_gauges[2], 900),
#         (regular_gauges[1], 300),
#         (regular_gauges[3], 300),
#     ]


# def test_same_weight_increased(voter, alice, regular_gauges):
#     voter.voteForPool([regular_gauges[0]], [100], {'from': alice})
#     voter.voteForPool([regular_gauges[1]], [200], {'from': alice})
#     voter.voteForPool([regular_gauges[2]], [200], {'from': alice})
#     voter.voteForPool([regular_gauges[0]], [100], {'from': alice})
#     voter.voteForPool([regular_gauges[3]], [-200], {'from': alice})
#     voter.voteForPool([regular_gauges[4]], [200], {'from': alice})
#     data = voter.getCurrentVotes()
#     assert data[:-2] == [
#         (regular_gauges[0], 200),
#         (regular_gauges[1], 200),
#         (regular_gauges[2], 200),
#         (regular_gauges[3], -200),
#         (regular_gauges[4], 200),
#     ]


# def test_same_weight_decreased(voter, alice, regular_gauges):
#     voter.voteForPool([regular_gauges[0]], [600], {'from': alice})
#     voter.voteForPool([regular_gauges[1]], [600], {'from': alice})
#     voter.voteForPool([regular_gauges[2]], [600], {'from': alice})
#     voter.voteForPool([regular_gauges[1]], [-400], {'from': alice})
#     voter.voteForPool([regular_gauges[2]], [-800], {'from': alice})
#     voter.voteForPool([regular_gauges[0]], [-400], {'from': alice})
#     data = voter.getCurrentVotes()
#     assert data[:-2] == [
#         (regular_gauges[0], 200),
#         (regular_gauges[1], 200),
#         (regular_gauges[2], -200),
#     ]


# def test_same_weight_increased_multiple_votes_in_call(voter, alice, regular_gauges):
#     voter.voteForPool([regular_gauges[0], regular_gauges[1], regular_gauges[2]], [100, 200, 200], {'from': alice})
#     voter.voteForPool([regular_gauges[0], regular_gauges[3], regular_gauges[4]], [100, -200, 200], {'from': alice})
#     data = voter.getCurrentVotes()
#     assert data[:-2] == [
#         (regular_gauges[0], 200),
#         (regular_gauges[1], 200),
#         (regular_gauges[2], 200),
#         (regular_gauges[3], -200),
#         (regular_gauges[4], 200),
#     ]


# def test_same_weight_decreased_multiple_votes_in_call(voter, alice, regular_gauges):
#     voter.voteForPool([regular_gauges[0], regular_gauges[1], regular_gauges[2]], [600, 600, 600], {'from': alice})
#     voter.voteForPool([regular_gauges[1], regular_gauges[2], regular_gauges[0]], [-400, -800, -400], {'from': alice})
#     data = voter.getCurrentVotes()
#     assert data[:-2] == [
#         (regular_gauges[0], 200),
#         (regular_gauges[1], 200),
#         (regular_gauges[2], -200),
#     ]


# def test_vote_no_gauge(voter, alice):
#     with brownie.reverts("Pool has no gauge"):
#         voter.voteForPool([alice], [1000], {'from': alice})


# def test_zero_vote(voter, alice, regular_gauges):
#     with brownie.reverts("Cannot vote zero"):
#         voter.voteForPool([regular_gauges[0]], [0], {'from': alice})


# def test_zero_vote_protected_gauge(voter, alice, protected_gauges):
#     with brownie.reverts("Cannot vote zero"):
#         voter.voteForPool([protected_gauges[0]], [0], {'from': alice})


# def test_zero_vote_nonzero_existing(voter, alice, regular_gauges):
#     voter.voteForPool([regular_gauges[0]], [1000], {'from': alice})
#     with brownie.reverts("Cannot vote zero"):
#         voter.voteForPool([regular_gauges[0]], [0], {'from': alice})


# def test_exceeds_available(voter, alice, regular_gauges):
#     with brownie.reverts("Available votes exceeded"):
#         voter.voteForPool([regular_gauges[0]], [100001], {'from': alice})

#     voter.voteForPool([regular_gauges[0]], [100000], {'from': alice})


# def test_exceeds_available_with_partial_vote(voter, alice, regular_gauges):
#     voter.voteForPool([regular_gauges[0]], [99000], {'from': alice})
#     with brownie.reverts("Available votes exceeded"):
#         voter.voteForPool([regular_gauges[0]], [1001], {'from': alice})

#     voter.voteForPool([regular_gauges[0]], [1000], {'from': alice})


# def test_exceeds_available_with_max_vote(voter, alice, regular_gauges):
#     voter.voteForPool([regular_gauges[0]], [100000], {'from': alice})
#     with brownie.reverts("Available votes exceeded"):
#         voter.voteForPool([regular_gauges[0]], [1], {'from': alice})
