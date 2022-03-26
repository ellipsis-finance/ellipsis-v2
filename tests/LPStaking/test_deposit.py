import brownie
import pytest
from brownie import ZERO_ADDRESS, accounts, chain

# Vote for incentives on pools 1-5
# doesn't move past vote week
@pytest.fixture(scope="module")
def setup_gauges(voter, lp_tokens, pools, locker, alice, bob):
    for index in range(5):
        # bump past first week
        chain.mine(timedelta=86400 * 14)
        # set the pools on the lpToken
        lp_tokens[index].setMinter(pools[index])
        # create a vote for a gauge
        voter.createTokenApprovalVote(lp_tokens[index], {"from": alice})
        # vote
        voter.voteForTokenApproval(index, 2**256-1, {"from": alice})
        # assert the token was approved
        assert voter.isApproved(lp_tokens[index]) == True


# Alice and Bob get EPX and lock it for vote weight.
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


# no revert string here
def test_deposit_no_amount(lp_staker, alice, pools):
    with brownie.reverts():
        lp_staker.deposit(pools[0], 0, 1, {"from": alice})


# def test_deposit_unauthorized_depositor(lp_staker, lp_tokens, setup_gauges, alice, bob, pools):
#     amount = 10**19
#     lp_tokens[0].mint(alice, amount, {"from": alice})
#     lp_tokens[0].approve(lp_staker, amount, {"from": alice})
#     # deposit LP
#     lp_staker.deposit(lp_tokens[0], amount, 1, {"from": alice})
#     # bob blocks third party actions
#     lp_staker.setBlockThirdPartyActions(1, {"from": bob})
#     # alice tries to act on bob's behalf
#     with brownie.reverts("Cannot deposit on behalf of this account"):
#         lp_staker.deposit(lp_tokens[0], amount, 1, {"from": alice})


def test_deposit_not_a_pools(lp_staker, alice, pools):
    with brownie.reverts():
        lp_staker.deposit(pools[0], 10 ** 19, 1)


def test_deposit_insufficient_balance(lp_staker, pools, lp_tokens, alice, charlie):
    with brownie.reverts():
        # charlie has a zero balance
        lp_staker.deposit(lp_tokens[0], 10 ** 18, 1, {"from": charlie})

    with brownie.reverts():
        # alice has a balance, try to deposit too much
        lp_staker.deposit(lp_tokens[0], lp_tokens[0].balanceOf(alice) + 1, 1, {"from": alice})


def test_deposit(lp_staker, setup_gauges, lp_tokens, alice):
    # amount of LP that will be deposited and tested for
    amount = 10**19

    # user balance in staker
    user_bal0 = lp_staker.userInfo(lp_tokens[0], alice);
    # lp tokens in staker
    lp_staker_bal0 = lp_tokens[0].balanceOf(lp_staker);
    lp_tokens[0].mint(alice, amount, {"from": alice})
    lp_tokens[0].approve(lp_staker, amount, {"from": alice})

    # deposit LP
    lp_staker.deposit(lp_tokens[0], amount, 1, {"from": alice})

    # get pool info
    tx = lp_staker.poolInfo(lp_tokens[0])
    # user balance in staker
    user_bal1 = lp_staker.userInfo(lp_tokens[0], alice);
    # lp tokens in staker
    lp_staker_bal1 = lp_tokens[0].balanceOf(lp_staker);
 
    # assert tx[0] - lp_staker_bal0 == amount
    assert user_bal1[0] - user_bal0[0] == amount
    assert lp_staker_bal1 - lp_staker_bal0 == amount


def test_multi_deposit(lp_staker, setup_gauges, pools, lp_tokens, alice):
    lp_staker_bal0 = lp_tokens[0].balanceOf(lp_staker);
    amount = 10 ** 19
    for acct in accounts[:10]:
        lp_tokens[0].mint(acct, amount)
        lp_tokens[0].approve(lp_staker, amount, {"from": acct})
        lp_staker.deposit(lp_tokens[0], amount, 1, {"from": acct})

    lp_staker_bal1 = lp_tokens[0].balanceOf(lp_staker);
    assert lp_staker_bal1 - lp_staker_bal0 == amount * 10


def test_deposit_event(pools, setup_gauges, lp_staker, lp_tokens, alice):
    amount = 10 ** 19
    lp_tokens[0].mint(alice, amount, {"from": alice})
    lp_tokens[0].approve(lp_staker, amount, {"from": alice})
    tx = lp_staker.deposit(lp_tokens[0], amount, 1, {"from": alice})
    # assert tx.events["Deposit"]["caller"] == alice
    assert tx.events["Deposit"]["user"] == alice
    assert tx.events["Deposit"]["token"] == lp_tokens[0]
    assert tx.events["Deposit"]["amount"] == amount
