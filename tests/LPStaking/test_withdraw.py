import brownie
import pytest
from brownie import accounts, chain


@pytest.fixture(scope="module", autouse=True)
def setup(eps2, locker, voter, lp_tokens, lp_staker, alice, bob, start_time, pools):
    # hand out some eps
    for acct in [alice, bob]:
        eps2.mint(acct, 1500000 * 10 ** 18, {'from': alice})
        eps2.approve(locker, 2 ** 256 - 1, {"from": acct})
    # get the chain past the eps2 frozen time
    delta = start_time - chain.time()
    chain.mine(timedelta=delta)
    # lock some eps to have some vote weight
    locker.lock(alice, 100000 * 10 ** 18, 10, {"from": alice})
    locker.lock(bob, 200000 * 10 ** 18, 2, {"from": bob})

    amount = 10**19
    for index in range(5):
        # mint some lp tokens.
        lp_tokens[index].mint(alice, amount, {"from": alice})
        lp_tokens[index].approve(lp_staker, amount, {"from": alice})
        lp_tokens[index].mint(bob, amount, {"from": bob})
        lp_tokens[index].approve(lp_staker, amount, {"from": bob})
        # bump past first week
        chain.mine(timedelta=86400 * 14)
        # set the pool on the lpToken
        lp_tokens[index].setMinter(pools[index], {"from": alice})
        # create a vote for a gauge
        voter.createTokenApprovalVote(lp_tokens[index], {"from": alice})
        # vote
        voter.voteForTokenApproval(index, 2**256-1, {"from": alice})
        # assert the token was approved
        assert voter.isApproved(lp_tokens[index]) == True

    # deposit LP
    lp_staker.deposit(lp_tokens[0], amount, 1, {"from": alice})


def test_withdraw_unk_lp_tokens(lp_staker, pools, alice):
    with brownie.reverts(""):
        lp_staker.withdraw(pools[0], 10 ** 19, 1, {"from": alice})


def test_withdraw_zero(lp_staker, lp_tokens, charlie):
    with brownie.reverts("Cannot withdraw zero"):
        lp_staker.withdraw(lp_tokens[0], 0, 1, {"from": charlie})


def test_withdraw_insufficient_deposit(lp_staker, alice, lp_tokens):
    user_bal = lp_staker.userInfo(lp_tokens[0], alice);
    assert user_bal[0] == 10 ** 19
    with brownie.reverts("withdraw: not good"):
        lp_staker.withdraw(lp_tokens[0], 10 ** 19 + 1, 1, {"from": alice})


def test_withdraw(lp_staker, alice, lp_tokens):
    initial = lp_tokens[0].balanceOf(alice)
    # Alice makes a withdrawal
    lp_staker.withdraw(lp_tokens[0], 10 ** 19, 1, {"from": alice})
    pool_info = lp_staker.poolInfo(lp_tokens[0])
    user_bal1 = lp_staker.userInfo(lp_tokens[0], alice);

    # check Alice's balance
    assert lp_tokens[0].balanceOf(alice) == initial + 10 ** 19
    # lp staker total balance of lp_tokens[0]
    assert pool_info[0] == 0
    # lp staker alice's balance of lp_tokens[0]
    assert user_bal1[0] == 0


def test_withdraw_partial(lp_staker, alice, lp_tokens):
    alice_bal0 = lp_tokens[0].balanceOf(alice)
    pool_info0 = lp_tokens[0].balanceOf(lp_staker)

    # Alice makes a withdrawal she had 10**19, so should have 6 * 10**18 left staked
    lp_staker.withdraw(lp_tokens[0], 4 * 10**18, 1, {"from": alice})
    pool_info1 = lp_tokens[0].balanceOf(lp_staker)
    user_bal1 = lp_staker.userInfo(lp_tokens[0], alice);
    assert lp_tokens[0].balanceOf(alice) == alice_bal0 + 4 * 10**18

    # assert that the pool's lp balance and user's stake lp
    # balance are equal, and equal to 10**19 - 4 * 10**18
    assert pool_info1 == user_bal1[0] == 6 * 10**18


def test_multi_accounts_deposit_withdraw(lp_staker, lp_tokens):
    amount = 10 ** 19
    total_bal = 0
    for acct in accounts[:10]:
        lp_tokens[1].mint(acct, amount)
        lp_tokens[1].approve(lp_staker, amount, {"from": acct})
        lp_staker.deposit(lp_tokens[1], amount, 1, {"from": acct})
        user_bal = lp_staker.userInfo(lp_tokens[1], acct);
        total_bal += user_bal[0]

    assert total_bal == amount * 10

    total_bal = 0
    for acct in accounts[:10]:
        user_bal = lp_staker.userInfo(lp_tokens[1], acct);
        assert user_bal[0] == amount
        lp_staker.withdraw(lp_tokens[1], amount // 2, 1, {"from": acct})
        user_bal = lp_staker.userInfo(lp_tokens[1], acct);
        total_bal += user_bal[0]

    assert total_bal == amount * 5

    for acct in accounts[:10]:
        user_bal = lp_staker.userInfo(lp_tokens[1], acct);
        user_bal[0] == amount // 2


def test_withdraw_event(lp_staker, alice, lp_tokens):
    amount = 10 ** 19
    tx = lp_staker.withdraw(lp_tokens[0], amount, 1, {"from": alice})
    assert tx.events["Withdraw"]["user"] == alice
    assert tx.events["Withdraw"]["token"] == lp_tokens[0]
    assert tx.events["Withdraw"]["amount"] == amount
