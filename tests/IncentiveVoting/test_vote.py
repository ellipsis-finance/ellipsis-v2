import brownie
import pytest
from brownie import chain, ZERO_ADDRESS


def validate_total_weight(data, vote_count):
    assert len(data) == 2
    weight = sum(abs(i[1]) for i in data[1])
    print('weight', weight)
    assert weight == data[0]

def mint_epx_to_acct(eps, eps2, locker, amount, acct):
    eps._mint_for_testing(acct, amount)
    eps.approve(eps2, amount, {"from": acct})
    eps2.migrate(acct, amount, {"from": acct})
    eps2.approve(locker, amount, {"from": acct})
    assert eps2.balanceOf(acct) == amount * 88

@pytest.fixture(scope="module")
def setup_gauges(voter, lp_tokens, pools, locker, alice, bob):
    for index in range(5):
        # bump past first week
        chain.mine(timedelta=86400 * 14)
        # set the pool on the lpToken
        lp_tokens[index].addMinter(pools[index])
        # create a vote for a gauge
        voter.createTokenApprovalVote(lp_tokens[index], {"from": alice})
        # vote
        voter.voteForTokenApproval(index, 2**256-1, {"from": alice})
        # assert the token was approved
        assert voter.isApproved(lp_tokens[index]) == True


@pytest.fixture(scope="module", autouse=True)
def setup(eps, eps2, locker, voter, lp_tokens, pools, lp_staker, alice, bob, transfer_time):
    lp_tokens[0].setMinter(pools[0], {'from': alice})
    lp_tokens[1].setMinter(pools[1])

    for acct in [alice, bob]:
        mint_epx_to_acct(eps, eps2, locker, 17000000 * 10 ** 18, acct)
        
    delta = transfer_time - chain.time()
    chain.mine(timedelta=delta)
    print(locker.getWeek())
    locker.lock(alice, 15000000 * 10 ** 18, 30, {"from": alice})
    locker.lock(bob, 15000000 * 10 ** 18, 20, {"from": bob})


def test_available_vote_weight(voter, alice, bob):
    assert voter.availableVotes(alice) == 30 * 15000000
    assert voter.availableVotes(bob) == 20 * 15000000
    chain.mine(timedelta=86400 * 7)
    assert voter.availableVotes(alice) == 29 * 15000000
    assert voter.availableVotes(bob) == 19 * 15000000


# def test_locking_affects_available_immediately(voter, locker, alice):
#     locker.lock(alice, 10**18, 16, {'from': alice})
#     assert voter.availableVotes(alice) == 30 * 15000000 + 16



# def test_increase_vote(voter, alice, bob, lp_tokens, setup_gauges):
#     week = voter.getWeek()
#     voter.vote([lp_tokens[0]], [400], {'from': alice})
#     voter.vote([lp_tokens[0]], [600], {'from': bob})

#     assert voter.userVotes(alice, week) == 400
#     assert voter.tokenVotes(lp_tokens[0], week) == 1000

#     data = voter.getCurrentVotes()
#     # print(data)
#     # assert the total agrees with total voted above
#     assert data[0] == 1000
#     validate_total_weight(data, 1)


# def test_vote_lower(voter, alice, bob, lp_tokens, setup_gauges):
#     week = voter.getWeek()
#     voter.vote([lp_tokens[0]], [1000], {'from': alice})
#     voter.vote([lp_tokens[2]], [500], {'from': bob})

#     assert voter.userVotes(alice, week) == 1000
#     assert voter.userVotes(bob, week) == 500
#     assert voter.tokenVotes(lp_tokens[0], week) == 1000
#     assert voter.tokenVotes(lp_tokens[2], week) == 500

#     data = voter.getCurrentVotes()
#     assert data[1][2:5] == [(lp_tokens[0], 1000), (lp_tokens[1],0), (lp_tokens[2], 500)]
#     validate_total_weight(data, 2)


# def test_vote_higher(voter, alice, lp_tokens, setup_gauges):
#     voter.vote([lp_tokens[0]], [1000], {'from': alice})
#     voter.vote([lp_tokens[2]], [3000], {'from': alice})
#     data = voter.getCurrentVotes()

#     assert data[1][2:5] == [(lp_tokens[0], 1000), (lp_tokens[1],0), (lp_tokens[2], 3000)]
#     validate_total_weight(data, 2)


# def test_vote_higher_lower(voter, alice, bob, lp_tokens, setup_gauges):
#     week = voter.getWeek()
#     voter.vote([lp_tokens[0]], [1000], {'from': alice})
#     voter.vote([lp_tokens[2]], [3000], {'from': bob})
#     voter.vote([lp_tokens[1]], [500], {'from': alice})

#     assert voter.userVotes(alice, week) == 1500
#     assert voter.userVotes(bob, week) == 3000
#     assert voter.tokenVotes(lp_tokens[0], week) == 1000
#     assert voter.tokenVotes(lp_tokens[1], week) == 500
#     assert voter.tokenVotes(lp_tokens[2], week) == 3000

#     data = voter.getCurrentVotes()
#     assert data[1][2:5] == [
#         (lp_tokens[0], 1000),
#         (lp_tokens[1], 500),
#         (lp_tokens[2], 3000),
#     ]
#     validate_total_weight(data, 3)


# def test_vote_lower_higher(voter, alice, lp_tokens):
#     voter.vote([lp_tokens[0]], [1000], {'from': alice})
#     voter.vote([lp_tokens[1]], [500], {'from': alice})
#     voter.vote([lp_tokens[2]], [3000], {'from': alice})
#     data = voter.getCurrentVotes()

#     assert data[1][2:5] == [
#         (lp_tokens[0], 1000),
#         (lp_tokens[1], 500),
#         (lp_tokens[2], 3000)
#     ]
#     validate_total_weight(data, 3)


# def test_vote_multiple_same_call(voter, alice, lp_tokens):
#     voter.vote(
#         [lp_tokens[0], lp_tokens[1], lp_tokens[2]],
#         [1000, 500, 3000],
#         {'from': alice}
#     )
#     data = voter.getCurrentVotes()

#     assert data[1][2:5] == [
#         (lp_tokens[0], 1000),
#         (lp_tokens[1], 500),
#         (lp_tokens[2], 3000),
#     ]


# def test_vote_for_hardcoded_two(voter, alice, lp_tokens, setup_gauges):
#     voter.vote([lp_tokens[0]], [1000], {'from': alice})
#     voter.vote([setup_gauges[1]], [500], {'from': alice})
#     data = voter.getCurrentVotes()
#     print(data)
    # assert data == [
    #     (lp_tokens[0], -1000),
    #     (setup_gauges[1], 582),
    #     (setup_gauges[0], 82),
    #     (ZERO_ADDRESS, 0),
    # ]


# def test_vote_for_hardcoded_one(voter, alice, lp_tokens, setup_gauges):
#     voter.vote([lp_tokens[0]], [-500], {'from': alice})
#     voter.vote([setup_gauges[0]], [500], {'from': alice})
#     voter.vote([lp_tokens[2]], [500], {'from': alice})

#     data = voter.getCurrentVotes()
#     assert data == [
#         (lp_tokens[0], -500),
#         (setup_gauges[0], 582),
#         (lp_tokens[2], 500),
#         (ZERO_ADDRESS, 0),
#         (setup_gauges[1], 82),
#     ]


# def test_vote_for_hardcoded_both(voter, alice, lp_tokens, setup_gauges):
#     voter.vote([lp_tokens[0]], [-200], {'from': alice})
#     voter.vote([setup_gauges[0]], [500], {'from': alice})
#     voter.vote([setup_gauges[1]], [800], {'from': alice})

#     data = voter.getCurrentVotes()
#     assert data == [
#         (lp_tokens[0], -200),
#         (setup_gauges[0], 582),
#         (setup_gauges[1], 882),
#         (ZERO_ADDRESS, 0),
#         (ZERO_ADDRESS, 0),
#     ]


# def test_no_votes(voter, setup_gauges):
#     data = voter.getCurrentVotes()
#     assert data == [
#         (setup_gauges[0], 1),
#         (setup_gauges[1], 1),
#     ]



# def test_same_weight_increased(voter, alice, lp_tokens):
#     voter.vote([lp_tokens[0]], [100], {'from': alice})
#     voter.vote([lp_tokens[1]], [200], {'from': alice})
#     voter.vote([lp_tokens[2]], [200], {'from': alice})
#     voter.vote([lp_tokens[0]], [100], {'from': alice})
#     voter.vote([lp_tokens[3]], [200], {'from': alice})
#     voter.vote([lp_tokens[4]], [200], {'from': alice})
#     data = voter.getCurrentVotes()
#     print(data[1][2:7])
#     assert data[1][2:7] == [
#         (lp_tokens[0], 200),
#         (lp_tokens[1], 200),
#         (lp_tokens[2], 200),
#         (lp_tokens[3], 200),
#         (lp_tokens[4], 200),
#     ]


# def test_same_weight_decreased(voter, alice, lp_tokens):
#     voter.vote([lp_tokens[0]], [600], {'from': alice})
#     voter.vote([lp_tokens[1]], [600], {'from': alice})
#     voter.vote([lp_tokens[2]], [600], {'from': alice})
#     voter.vote([lp_tokens[1]], [400], {'from': alice})
#     voter.vote([lp_tokens[2]], [800], {'from': alice})
#     voter.vote([lp_tokens[0]], [400], {'from': alice})
#     data = voter.getCurrentVotes()
#     assert data[1][2:5] == [
#         (lp_tokens[0], 1000),
#         (lp_tokens[1], 1000),
#         (lp_tokens[2], 1400),
#     ]


# def test_same_weight_increased_multiple_votes_in_call(voter, alice, lp_tokens):
#     voter.vote([lp_tokens[0], lp_tokens[1], lp_tokens[2]], [100, 200, 200], {'from': alice})
#     voter.vote([lp_tokens[0], lp_tokens[3], lp_tokens[4]], [100, 200, 200], {'from': alice})
#     data = voter.getCurrentVotes()
#     assert data[1][2:7] == [
#         (lp_tokens[0], 200),
#         (lp_tokens[1], 200),
#         (lp_tokens[2], 200),
#         (lp_tokens[3], 200),
#         (lp_tokens[4], 200),
#     ]


# def test_same_weight_decreased_multiple_votes_in_call(voter, alice, lp_tokens):
#     voter.vote([lp_tokens[0], lp_tokens[1], lp_tokens[2]], [600, 600, 600], {'from': alice})
#     voter.vote([lp_tokens[1], lp_tokens[2], lp_tokens[0]], [450, 800, 500], {'from': alice})
#     data = voter.getCurrentVotes()
#     assert data[1][2:5] == [
#         (lp_tokens[0], 1100),
#         (lp_tokens[1], 1050),
#         (lp_tokens[2], 1400),
#     ]


# def test_vote_no_gauge(voter, alice):
#     with brownie.reverts("Not approved for incentives"):
#         voter.vote([alice], [1000], {'from': alice})


# def test_input_length_mismatch(voter, alice, lp_tokens):
#     with brownie.reverts("Input length mismatch"):
#         voter.vote([lp_tokens[0], lp_tokens[1]], [0], {'from': alice})



# def test_exceeds_available(voter, alice, lp_tokens):
#     with brownie.reverts("Available votes exceeded"):
#         voter.vote([lp_tokens[0]], [voter.availableVotes(alice)+1], {'from': alice})

#     voter.vote([lp_tokens[0]], [voter.availableVotes(alice)], {'from': alice})


# def test_exceeds_available_with_partial_vote(voter, alice, lp_tokens):
#     voter.vote([lp_tokens[0]], [voter.availableVotes(alice)-10], {'from': alice})
#     with brownie.reverts("Available votes exceeded"):
#         voter.vote([lp_tokens[0]], [11], {'from': alice})

#     voter.vote([lp_tokens[0]], [10], {'from': alice})


# def test_exceeds_available_with_max_vote(voter, alice, lp_tokens):
#     voter.vote([lp_tokens[0]], [voter.availableVotes(alice)], {'from': alice})
#     with brownie.reverts("Available votes exceeded"):
#         voter.vote([lp_tokens[0]], [1], {'from': alice})
