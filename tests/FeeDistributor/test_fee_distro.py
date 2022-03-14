import brownie
import pytest
from brownie import chain


@pytest.fixture(scope="module", autouse=True)
def setup(eps2, incentive1, locker, fee_distro, lp_staker, start_time, alice, bob, charlie):
    # move ahead to when eps2 is transferrable
    delta = start_time - chain.time()
    chain.mine(timedelta=delta)
    # mint some EPS2 to lock
    for acct in [bob, charlie]:
        # alice is a minter
        eps2.mint(acct, 10 ** 18, {"from": alice})
        eps2.approve(locker, 2 ** 256 - 1, {"from": acct})
        locker.lock(acct, 10 ** 18, 10, {"from": acct})
    
    # setup rewards
    incentive1._mint_for_testing(alice, 1000000)
    incentive1.approve(fee_distro, 2 ** 256 - 1, {"from": alice})


def test_deposit_fee(fee_distro, incentive1, alice):
    fee_distro.depositFee(incentive1, 700000, {"from": alice})

    assert incentive1.balanceOf(fee_distro) == 700000
    assert incentive1.balanceOf(alice) == 300000
    assert fee_distro.weeklyFeeAmounts(incentive1, 0) == 700000


def test_deposit_fee_multiple(fee_distro, incentive1, alice):
    fee_distro.depositFee(incentive1, 700000, {"from": alice})
    fee_distro.depositFee(incentive1, 100000, {"from": alice})

    assert incentive1.balanceOf(fee_distro) == 800000
    assert incentive1.balanceOf(alice) == 200000
    assert fee_distro.weeklyFeeAmounts(incentive1, 0) == 800000


def test_deposit_fee_multiple_weeks(fee_distro, incentive1, alice):
    fee_distro.depositFee(incentive1, 400000, {"from": alice})
    chain.sleep(86400 * 7)
    fee_distro.depositFee(incentive1, 200000, {"from": alice})
    chain.sleep(86400 * 7)
    fee_distro.depositFee(incentive1, 100000, {"from": alice})

    assert incentive1.balanceOf(fee_distro) == 700000
    assert incentive1.balanceOf(alice) == 300000
    assert fee_distro.weeklyFeeAmounts(incentive1, 0) == 400000
    assert fee_distro.weeklyFeeAmounts(incentive1, 1) == 200000
    assert fee_distro.weeklyFeeAmounts(incentive1, 2) == 100000


def test_claimable(fee_distro, incentive1, alice, bob, charlie, locker):
    fee_distro.depositFee(incentive1, 1000000, {"from": alice})
    # start time is always the start of the current epoch week
    # so advance to day 6 and check no claimable:
    # we are currently advanced (chain.time() - fee_distro.startTime()) seconds
    # we want to be advanced 86400 * 6
    delta = (86400 * 6) - (chain.time() - fee_distro.startTime())
    chain.mine(timedelta=delta)
    assert fee_distro.claimable(bob, [incentive1]) == [0]

    last_claimable = 0
    for i in range(7):
        # had to use 86402, 86401 getWeek() reported week 1,
        # however claimable returned 0.
        chain.mine(timedelta=86402)
        claimable = fee_distro.claimable(bob, [incentive1])[0]
        assert 500000 > claimable > last_claimable
        last_claimable = claimable

    chain.mine(timedelta=86400)
    assert fee_distro.claimable(bob, [incentive1]) == [500000]


def test_claimable_multiple_weeks(fee_distro, incentive1, alice, bob, charlie):
    fee_distro.depositFee(incentive1, 500000, {"from": alice})
    delta = (86401 * 14) - (chain.time() - fee_distro.startTime())
    chain.mine(timedelta=delta)
    fee_distro.depositFee(incentive1, 500000, {"from": alice})
    chain.mine(timedelta=86401 * 6)

    last_claimable = fee_distro.claimable(bob, [incentive1])[0]
    assert last_claimable == 250000
    for i in range(7):
        chain.mine(timedelta=86401)
        claimable = fee_distro.claimable(bob, [incentive1])[0]
        assert 500000 > claimable > last_claimable
        last_claimable = claimable

    chain.mine(timedelta=86400)
    assert fee_distro.claimable(bob, [incentive1]) == [500000]

    chain.mine(timedelta=86401 * 7)
    assert fee_distro.claimable(bob, [incentive1]) == [500000]


def test_claim_across_single_week(fee_distro, incentive1, alice, bob, charlie):
    fee_distro.depositFee(incentive1, 1000000, {"from": alice})
    delta = (86400 * 6) - (chain.time() - fee_distro.startTime())
    chain.mine(timedelta=delta)
    assert fee_distro.claimable(bob, [incentive1]) == [0]

    last_balance = 0
    for i in range(7):
        chain.mine(timedelta=86402)
        fee_distro.claimable(bob, [incentive1])
        fee_distro.claim(bob, [incentive1])
        balance = incentive1.balanceOf(bob)
        assert 500000 > balance > last_balance
        last_balance = balance

    chain.mine(timedelta=86400)
    assert fee_distro.claimable(bob, [incentive1]) == [500000 - balance]


def test_claim_multiple_weeks(fee_distro, incentive1, alice, bob, charlie):
    fee_distro.depositFee(incentive1, 500000, {"from": alice})
    delta = (86401 * 14) - (chain.time() - fee_distro.startTime())
    chain.mine(timedelta=delta)
    fee_distro.depositFee(incentive1, 500000, {"from": alice})
    chain.mine(timedelta=86401 * 21)

    fee_distro.claim(bob, [incentive1], {"from": bob})
    assert incentive1.balanceOf(bob) == 500000


def test_claim_complex(fee_distro, incentive1, alice, bob, charlie):
    fee_distro.depositFee(incentive1, 500000, {"from": alice})
    delta = (86401 * 10) - (chain.time() - fee_distro.startTime())
    chain.mine(timedelta=delta)

    # claims a portion of the first week's fees
    fee_distro.claim(bob, [incentive1], {"from": bob})
    # deposit fees for week 2
    fee_distro.depositFee(incentive1, 300000, {"from": alice})

    chain.mine(timedelta=86401 * 7)
    # deposit fees for week 3
    fee_distro.depositFee(incentive1, 200000, {"from": alice})

    chain.mine(timedelta=86401 * 7)
    # claims the remainder of week 1, the full balance of week 2, and a portion of week 3
    fee_distro.claim(bob, [incentive1], {"from": bob})

    chain.mine(timedelta=86401 * 7)
    # claims the remainder of week 3
    fee_distro.claim(bob, [incentive1], {"from": bob})

    assert incentive1.balanceOf(bob) == 500000
