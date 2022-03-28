import brownie
import pytest
from brownie import ZERO_ADDRESS, accounts, chain


# want to deposit to contract and get our boost numbers
def mint_epx_to_acct(eps, eps2, locker, amount, acct):
    eps._mint_for_testing(acct, amount)
    eps.approve(eps2, amount, {"from": acct})
    eps2.migrate(acct, amount, {"from": acct})
    eps2.approve(locker, amount, {"from": acct})
    assert eps2.balanceOf(acct) == amount * 88


@pytest.fixture(scope="module", autouse=True)
def setup(eps2, eps, locker, voter, lp_tokens, pools, lp_staker, alice, bob, charlie, dan, transfer_time):
    lp_tokens[0].setMinter(pools[0], {'from': alice})
    lp_tokens[1].setMinter(pools[1], {'from': alice})


    for acct in [alice, bob, charlie, dan]:
        mint_epx_to_acct(eps, eps2, locker, 15000000 * 10 ** 18, acct)
        lp_tokens[0].mint(acct, 100000 * 10 ** 18, {'from': acct})
        lp_tokens[0].approve(lp_staker, 2 ** 256 - 1, {"from": acct})

    # move ahead to allow tfer of EPS
    delta = transfer_time - chain.time()
    chain.mine(timedelta=delta)
    # lock EPS
    locker.lock(alice, 15000000 * 10 ** 18, 30, {"from": alice})
    locker.lock(bob, 15000000 * 10 ** 18, 30, {"from": bob})
    locker.lock(charlie, 15000000 * 10 ** 18, 30, {"from": charlie})

    # set Alice n Bob up to stake
    for index in range(1): # just doing one gauge for the moment
        # bump past first 2 weeks to be able to vote
        chain.mine(timedelta=86400 * 14)
        # set the minter/pools on the lpToken
        lp_tokens[index].setMinter(pools[index], {"from": alice})
        # create a vote for a gauge
        voter.createTokenApprovalVote(lp_tokens[index], {"from": alice})
        # vote
        voter.voteForTokenApproval(index, 2**256-1, {"from": alice})
        # assert the token was approved
        assert voter.isApproved(lp_tokens[index]) == True


def test_equal_rewards(lp_staker, lp_tokens, locker, eps2, voter, alice, bob, charlie, dan):
    # stake. then claim before any voting week to update each user's boost
    for acct in [alice, bob, charlie, dan]:
        lp_staker.deposit(lp_tokens[0], 100000 * 10 ** 18, 1, {"from": acct})

    for acct in [alice, bob, charlie, dan]:
        lp_staker.claim(acct, [lp_tokens[0]], {"from": acct})

    # move ahead to a votable week
    chain.mine(timedelta=86400 * 7)
    # Alice votes for a gauge to get emissions
    voter.vote([lp_tokens[0]], [voter.availableVotes(alice)], {"from": alice})
    # move ahead to rewards week
    chain.mine(timedelta=86400 * 7)

    # for nomalizing the gains.
    eps_alice0 = eps2.balanceOf(alice, {"from": alice})
    eps_bob0 = eps2.balanceOf(bob, {"from": bob})
    eps_charlie0 = eps2.balanceOf(charlie, {"from": charlie})
    eps_dan0 = eps2.balanceOf(dan, {"from": dan})

    # claim and then calculate the gains
    for acct in [alice, bob, charlie, dan]:
        lp_staker.claim(acct, [lp_tokens[0]], {"from": acct})

    eps_alice1 = eps2.balanceOf(alice, {"from": alice})
    eps_bob1 = eps2.balanceOf(bob, {"from": bob})
    eps_charlie1 = eps2.balanceOf(charlie, {"from": charlie})
    eps_dan1 = eps2.balanceOf(dan, {"from": dan})

    # print('Alice Gain', eps_alice1-eps_alice0)
    # print('Bob Gain', eps_bob1-eps_bob0)
    # print('Charlie Gain', eps_charlie1-eps_charlie0)
    # print('Dan Gain', eps_dan1-eps_dan0)

    assert (eps_alice1-eps_alice0) == (eps_bob1-eps_bob0) == (eps_charlie1-eps_charlie0)


# # Alice and Dan are locked, Alice has staked EPS however Dan has not. Poor Dan. 
# def test_boost_calculation_alice_versus_dan(lp_staker, lp_tokens, locker, eps2, voter, alice, bob, charlie, dan):
#     lp_staker.deposit(lp_tokens[0], 100000 * 10 ** 18, 1, {"from": alice})
#     lp_staker.deposit(lp_tokens[0], 100000 * 10 ** 18, 1, {"from": dan})
#     lp_staker.claim(alice, [lp_tokens[0]], {"from": alice})
#     lp_staker.claim(dan, [lp_tokens[0]], {"from": dan})

#     # move ahead to a votable week
#     chain.mine(timedelta=86400 * 7)
#     # print('Vote in week:', voter.getWeek())
#     voter.vote([lp_tokens[0]], [voter.availableVotes(alice)], {"from": alice})
#     # move ahead to rewards week
#     chain.mine(timedelta=86400 * 7)

#     eps_alice0 = eps2.balanceOf(alice, {"from": alice})
#     eps_dan0 = eps2.balanceOf(dan, {"from": dan})

#     lp_staker.claim(alice, [lp_tokens[0]], {"from": alice})
#     lp_staker.claim(dan, [lp_tokens[0]], {"from": dan})

#     eps_alice1 = eps2.balanceOf(alice, {"from": alice})
#     eps_dan1 = eps2.balanceOf(dan, {"from": dan})

#     alice_gain = eps_alice1-eps_alice0
#     dan_gain = eps_dan1-eps_dan0
#     alice_info = lp_staker.userInfo(lp_tokens[0], alice)
#     dan_info = lp_staker.userInfo(lp_tokens[0], dan)
#     alice_boost = alice_info[1]/alice_info[0]*2.5
#     dan_boost = dan_info[1]/dan_info[0]*2.5

#     assert alice_gain/dan_gain == alice_boost/dan_boost


# def test_boost_four_players(lp_staker, lp_tokens, locker, eps2, voter, alice, bob, charlie, dan):
#     for acct in [alice, bob, charlie, dan]:
#         lp_staker.deposit(lp_tokens[0], 100000 * 10 ** 18, 1, {"from": acct})

#     for acct in [alice, bob, charlie, dan]:
#         lp_staker.claim(acct, [lp_tokens[0]], {"from": acct})

#     # move ahead to a votable week
#     chain.mine(timedelta=86400 * 7)
#     # print('Vote in week:', voter.getWeek())
#     # print('locker.userWeight(alice):', locker.userWeight(alice))
#     voter.vote([lp_tokens[0]], [voter.availableVotes(alice)], {"from": alice})
#     # move ahead to rewards week
#     chain.mine(timedelta=86400 * 7)

#     eps_alice0 = eps2.balanceOf(alice, {"from": alice})
#     eps_bob0 = eps2.balanceOf(bob, {"from": bob})
#     eps_charlie0 = eps2.balanceOf(charlie, {"from": charlie})
#     eps_dan0 = eps2.balanceOf(dan, {"from": dan})

#     for acct in [alice, bob, charlie, dan]:
#         lp_staker.claim(acct, [lp_tokens[0]], {"from": acct})

#     eps_alice1 = eps2.balanceOf(alice, {"from": alice})
#     eps_bob1 = eps2.balanceOf(bob, {"from": bob})
#     eps_charlie1 = eps2.balanceOf(charlie, {"from": charlie})
#     eps_dan1 = eps2.balanceOf(dan, {"from": dan})

#     alice_gain = eps_alice1-eps_alice0
#     bob_gain = eps_bob1-eps_bob0
#     charlie_gain = eps_charlie1-eps_charlie0
#     dan_gain = eps_dan1-eps_dan0

#     alice_info = lp_staker.userInfo(lp_tokens[0], alice)
#     bob_info = lp_staker.userInfo(lp_tokens[0], bob)
#     charlie_info = lp_staker.userInfo(lp_tokens[0], charlie)
#     dan_info = lp_staker.userInfo(lp_tokens[0], dan)
#     alice_boost = alice_info[1]/alice_info[0]*2.5
#     bob_boost = bob_info[1]/bob_info[0]*2.5
#     charlie_boost = charlie_info[1]/charlie_info[0]*2.5
#     dan_boost = dan_info[1]/dan_info[0]*2.5
#     print(alice_boost, bob_boost, charlie_boost, dan_boost)
#     assert alice_gain/bob_gain == alice_boost/bob_boost
#     assert alice_gain/charlie_gain == alice_boost/charlie_boost
#     assert alice_gain/dan_gain == alice_boost/dan_boost

#     assert bob_gain/charlie_gain == bob_boost/charlie_boost
#     assert bob_gain/dan_gain == bob_boost/dan_boost

#     assert charlie_gain/dan_gain == charlie_boost/dan_boost
