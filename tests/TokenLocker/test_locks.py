import brownie
import pytest
from brownie import chain


@pytest.fixture(scope="module", autouse=True)
def setup(eps2, locker, lp_staker, alice, bob, start_time):
    for acct in [alice, bob]:
        eps2.mint(acct, 10 ** 18, {'from': alice})
        eps2.approve(locker, 2 ** 256 - 1, {"from": acct})
    delta = start_time - chain.time()
    chain.mine(timedelta=delta)

# alice deposits coins into locker to create a new lock 
def test_new_lock(locker, eps2, alice):
    locker.lock(alice, 1000, 10, {"from": alice})
    assert eps2.balanceOf(alice) == 10 ** 18 - 1000
    assert eps2.balanceOf(locker) == 1000
    # lock weight = sum [num_tokens] * [weeks_until_unlock]
    assert locker.userWeight(alice) == 10 * 1000
    assert locker.totalWeight() == 10 * 1000
    assert locker.getActiveUserLocks(alice) == [(10, 1000)]


def test_multiple_new_locks(locker, eps2, alice):
    locker.lock(alice, 1000, 6, {"from": alice})
    chain.sleep(604800)
    locker.lock(alice, 1500, 9, {"from": alice})
    chain.sleep(604800)
    locker.lock(alice, 300, 52, {"from": alice})

    assert eps2.balanceOf(alice) == 10 ** 18 - (1000 + 1500 + 300)

    expected_weight = 1000 * (6 - 2) + 1500 * (9 - 1) + 300 * 52
    assert locker.userWeight(alice) == expected_weight
    assert locker.totalWeight() == expected_weight
    assert locker.getActiveUserLocks(alice) == [
        (4, 1000),
        (8, 1500),
        (52, 300),
    ]


def test_new_lock_different_receiver(locker, eps2, alice, bob):
    locker.lock(bob, 1000, 10, {"from": alice})
    assert eps2.balanceOf(alice) == 10 ** 18 - 1000
    assert eps2.balanceOf(bob) == 10 ** 18
    assert eps2.balanceOf(locker) == 1000

    assert locker.userWeight(alice) == 0
    assert locker.userWeight(bob) == 10 * 1000
    assert locker.totalWeight() == 10 * 1000


def test_increase_lock_amount(locker, eps2, alice):
    locker.lock(alice, 1000, 10, {"from": alice})
    locker.lock(alice, 4000, 10, {"from": alice})
    locker.lock(alice, 555, 10, {"from": alice})

    assert eps2.balanceOf(alice) == 10 ** 18 - 5555
    assert eps2.balanceOf(locker) == 5555
    assert locker.userWeight(alice) == 10 * 5555
    assert locker.totalWeight() == 10 * 5555


def test_increase_lock_amount_different_week(locker, eps2, alice):
    locker.lock(alice, 1000, 10, {"from": alice})
    chain.sleep(604800)
    locker.lock(alice, 4000, 9, {"from": alice})
    chain.sleep(604800)
    locker.lock(alice, 555, 8, {"from": alice})

    assert eps2.balanceOf(alice) == 10 ** 18 - 5555
    assert eps2.balanceOf(locker) == 5555
    assert locker.userWeight(alice) == 8 * 5555
    assert locker.totalWeight() == 8 * 5555


def test_lock_weight_decays(locker, eps2, alice):
    chain.sleep(86400 * 20)
    locker.lock(alice, 1000, 52, {"from": alice})

    for i in range(52, -1, -1):
        assert locker.userWeight(alice) == 1000 * i
        assert locker.totalWeight() == 1000 * i
        assert locker.getActiveUserLocks(alice) == ([(i, 1000)] if i else [])
        chain.mine(timedelta=86400 * 7)


def test_lock_weight_decays_multiple_users(locker, eps2, alice, bob):
    chain.sleep(86400 * 20)
    locker.lock(alice, 1000, 52, {"from": alice})
    locker.lock(bob, 3000, 12, {"from": bob})

    for i in range(52, -1, -1):
        assert locker.userWeight(alice) == 1000 * i
        assert locker.userWeight(bob) == 3000 * max(i - 40, 0)
        assert locker.totalWeight() == 1000 * i + 3000 * max(i - 40, 0)
        chain.mine(timedelta=86400 * 7)


def test_extend_lock(locker, eps2, alice):
    locker.lock(alice, 1000, 10, {"from": alice})
    locker.extendLock(1000, 10, 14, {"from": alice})
    assert eps2.balanceOf(alice) == 10 ** 18 - 1000
    assert eps2.balanceOf(locker) == 1000
    assert locker.userWeight(alice) == 14 * 1000
    assert locker.totalWeight() == 14 * 1000


def test_extend_lock_partial(locker, eps2, alice):
    locker.lock(alice, 1000, 10, {"from": alice})
    locker.extendLock(400, 10, 14, {"from": alice})
    assert eps2.balanceOf(alice) == 10 ** 18 - 1000
    assert eps2.balanceOf(locker) == 1000
    assert locker.userWeight(alice) == 10 * 600 + 14 * 400
    assert locker.totalWeight() == 10 * 600 + 14 * 400


def test_extend_lock_different_week(locker, eps2, alice):
    locker.lock(alice, 1000, 10, {"from": alice})
    chain.mine(timedelta=86400 * 7)
    locker.extendLock(400, 9, 15, {"from": alice})
    assert eps2.balanceOf(alice) == 10 ** 18 - 1000
    assert eps2.balanceOf(locker) == 1000
    assert locker.userWeight(alice) == 9 * 600 + 15 * 400
    assert locker.totalWeight() == 9 * 600 + 15 * 400


def test_lock_min_length(locker, eps2, alice):
    with brownie.reverts("Min 1 week"):
        locker.lock(alice, 1000, 0, {"from": alice})

    locker.lock(alice, 1000, 1, {"from": alice})


def test_lock_max_length(locker, eps2, alice):
    with brownie.reverts("Exceeds MAX_LOCK_WEEKS"):
        locker.lock(alice, 1000, 53, {"from": alice})

    locker.lock(alice, 1000, 52, {"from": alice})


def test_lock_zero(locker, eps2, alice):
    with brownie.reverts("Amount must be nonzero"):
        locker.lock(alice, 0, 10, {"from": alice})


def test_extend_min_length(locker, eps2, alice):
    with brownie.reverts("Min 1 week"):
        locker.extendLock(1000, 0, 10, {"from": alice})


def test_extend_max_length(locker, eps2, alice):
    locker.lock(alice, 1000, 10, {"from": alice})
    with brownie.reverts("Exceeds MAX_LOCK_WEEKS"):
        locker.extendLock(1000, 10, 53, {"from": alice})

    locker.extendLock(1000, 10, 52, {"from": alice})


@pytest.mark.parametrize("new_weeks", [0, 9, 10])
def test_extend_reduce_length(locker, eps2, alice, new_weeks):
    locker.lock(alice, 1000, 10, {"from": alice})
    with brownie.reverts("newWeeks must be greater than weeks"):
        locker.extendLock(1000, 10, new_weeks, {"from": alice})


def test_extend_zero(locker, eps2, alice):
    with brownie.reverts("Amount must be nonzero"):
        locker.extendLock(0, 10, 15, {"from": alice})


def test_extend_no_balance(locker, eps2, alice):
    with brownie.reverts():
        locker.extendLock(2000, 10, 13, {"from": alice})


def test_extend_insufficient_balance(locker, eps2, alice):
    locker.lock(alice, 1000, 10, {"from": alice})
    with brownie.reverts():
        locker.extendLock(2000, 10, 13, {"from": alice})


def test_extend_wrong_week(locker, eps2, alice):
    locker.lock(alice, 1000, 10, {"from": alice})
    with brownie.reverts():
        locker.extendLock(1000, 9, 13, {"from": alice})
