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
    locker.lock(alice, 100000, 1, {"from": alice})
    locker.lock(alice, 200000, 2, {"from": alice})

    # sleep for 1 week, this way every test begins with one expired lock
    chain.mine(timedelta=86400 * 7)


def test_new_stream(locker, alice):
    locker.initiateExitStream({"from": alice})
    assert locker.exitStream(alice)["amount"] == 100000
    assert locker.exitStream(alice)["start"] == chain[-1].timestamp


def test_new_stream_multiple_expired_weeks(locker, alice):
    chain.sleep(86400 * 7)
    locker.initiateExitStream({"from": alice})

    assert locker.exitStream(alice)["amount"] == 300000
    assert locker.exitStream(alice)["start"] == chain[-1].timestamp


def test_new_stream_twice(locker, alice):
    locker.initiateExitStream({"from": alice})
    chain.sleep(86400 * 7)
    locker.initiateExitStream({"from": alice})

    assert locker.exitStream(alice)["amount"] == 300000
    assert locker.exitStream(alice)["start"] == chain[-1].timestamp


def test_new_stream_partially_claimed_existing_stream(locker, eps2, alice):
    initial = eps2.balanceOf(alice)
    locker.initiateExitStream({"from": alice})

    # half way through the stream, make a claim and record the amount received
    chain.sleep(86400 * 3)
    locker.withdrawExitStream({"from": alice})
    received = eps2.balanceOf(alice) - initial

    # once the stream is expired, do NOT claim prior to starting a new stream
    chain.mine(timedelta=86400 * 5)
    streamable = locker.claimableExitStreamBalance(alice)
    locker.initiateExitStream({"from": alice})

    assert locker.exitStream(alice)["amount"] == 200000 + streamable
    assert locker.exitStream(alice)["start"] == chain[-1].timestamp
    assert locker.exitStream(alice)["amount"] + received == 300000


def test_new_stream_unclaimed_existing_stream(locker, eps2, alice):
    locker.initiateExitStream({"from": alice})

    # once the stream is expired, do NOT claim prior to starting a new stream
    chain.mine(timedelta=86400 * 8)
    locker.initiateExitStream({"from": alice})

    assert locker.exitStream(alice)["amount"] == 300000
    assert locker.exitStream(alice)["start"] == chain[-1].timestamp


def test_cannot_stream_twice_same_week(locker, alice):
    locker.initiateExitStream({"from": alice})
    with brownie.reverts("No withdrawable balance"):
        locker.initiateExitStream({"from": alice})


def test_withdraw(locker, eps2, alice):
    initial = eps2.balanceOf(alice)
    locker.initiateExitStream({"from": alice})
    chain.sleep(86400 * 7)
    locker.withdrawExitStream({"from": alice})

    assert eps2.balanceOf(alice) == initial + 100000


def test_withdraw_partial(locker, eps2, alice):
    initial_balance = eps2.balanceOf(alice)
    locker.initiateExitStream({"from": alice})

    # every ~day, withdraw from the partially completed stream and check the received balance
    for i in range(7):
        chain.mine(timedelta=86000)
        duration = chain[-1].timestamp - chain[-2].timestamp
        expected = 100000 * duration // (86400 * 7)
        assert abs(locker.claimableExitStreamBalance(alice) - expected) < 2

        balance = eps2.balanceOf(alice)
        locker.withdrawExitStream({"from": alice})
        assert 0.999 < expected / (eps2.balanceOf(alice) - balance) <= 1

    # final withdrawal once the stream is complete, we should now have the full balance
    chain.mine(timedelta=86400)
    locker.withdrawExitStream({"from": alice})
    assert eps2.balanceOf(alice) == initial_balance + 100000
