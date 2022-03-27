import brownie
import pytest
from brownie import chain


@pytest.fixture(scope="module", autouse=True)
def setup(eps2, locker, lp_staker, alice, bob, charlie, start_time):
    for acct in [alice, bob, charlie]:
        eps2.mint(acct, 10 ** 18, {'from': alice})
        eps2.approve(locker, 2 ** 256 - 1, {"from": acct})
    delta = start_time - chain.time()
    chain.mine(timedelta=delta)


def test_streamable_balance(locker, eps2, alice):
    # make locks for ten weeks
    for i in range(1,10):
        locker.lock(alice, 1000, i, {"from": alice})
    # advance week by week and check streamable balance
    for i in range(1,10):
        chain.mine(timedelta=604800)
        assert locker.streamableBalance(alice) == 1000*i


def test_multiple_streamable_balance(locker, alice, bob, charlie):
    # make locks for ten weeks
    for i in range(1,10):
        locker.lock(alice, 1000, i, {"from": alice})
        locker.lock(bob, 3000, i, {"from": bob})
        locker.lock(charlie, 5000, i, {"from": charlie})
    
    # advance week by week and check streamable balance
    for i in range(1,10):
        chain.mine(timedelta=604800)
        assert locker.streamableBalance(alice) == 1000*i
        assert locker.streamableBalance(bob) == 3000*i
        assert locker.streamableBalance(charlie) == 5000*i

# 
def test_streaming_exit(locker, eps2, alice):
    # make locks for ten weeks
    for i in range(1,10):
        locker.lock(alice, 1000, i, {"from": alice})

    chain.mine(timedelta=6048000)
   
    # alice locked 9k tokens
    bal0 = eps2.balanceOf(alice)
    locker.initiateExitStream({"from": alice}) 
    # run a little check at the half-way mark
    chain.mine(timedelta=302400)
    assert locker.claimableExitStreamBalance(alice) - 4500 < 10
    chain.mine(timedelta=302400)
    locker.withdrawExitStream({"from": alice}) 
    assert bal0 + 9000 == eps2.balanceOf(alice)
    assert locker.claimableExitStreamBalance(alice) == 0


def test_streaming_exit_multi_withdraws(locker, eps2, alice):
    # make locks for ten weeks
    for i in range(1,10):
        locker.lock(alice, 1000, i, {"from": alice})
    # advance week by week and check streamable balance
    for i in range(1,10):
        chain.mine(timedelta=604800)
        assert locker.streamableBalance(alice) == 1000*i
    
    # alice locked 9k tokens
    bal0 = eps2.balanceOf(alice)
    locker.initiateExitStream({"from": alice}) 
    # do 20 claims
    for i in range(20):
        chain.mine(timedelta=30240)
        claimable = locker.claimableExitStreamBalance(alice)
        assert claimable - 450 < 10
        locker.withdrawExitStream({"from": alice}) 
        assert bal0 + claimable - eps2.balanceOf(alice) < 10

    assert bal0 + 9000 == eps2.balanceOf(alice)
    assert locker.claimableExitStreamBalance(alice) == 0



def test_multiple_streaming_exit(locker, eps2, alice, bob, charlie):
    # make locks for ten weeks
    locks = [1000, 3000, 9000]
    for i in range(1,10):
        locker.lock(alice, locks[0], i, {"from": alice})
        locker.lock(bob, locks[1], i, {"from": bob})
        locker.lock(charlie, locks[2], i, {"from": charlie})
    
    # advance week by week and check streamable balance
    chain.mine(timedelta=6048000)
    
    # alice locked 9k tokens
    bal = []
    bal.append(eps2.balanceOf(alice))
    bal.append(eps2.balanceOf(bob))
    bal.append(eps2.balanceOf(charlie))
    for acct in [alice, bob, charlie]:
        locker.initiateExitStream({"from": acct}) 

    # do 20 claims
    for i in range(20):
        chain.mine(timedelta=30240)
        acct_num = 0
        for acct in [alice, bob, charlie]:
            claimable = locker.claimableExitStreamBalance(acct)
            # players stakes 9 x locks[acct_num] and we're doing 20 claims:
            sub = locks[acct_num] * 9/20
            # sub is exact, contract comes in under:
            assert 0 <= sub - claimable <= 1
            # pull out claimable
            locker.withdrawExitStream({"from": acct}) 
            assert bal[acct_num] + claimable - eps2.balanceOf(acct) < 10
            acct_num += 1

    assert bal[0] + locks[0] * 9 == eps2.balanceOf(alice)
    assert bal[1] + locks[1] * 9 == eps2.balanceOf(bob)
    assert bal[2] + locks[2] * 9 == eps2.balanceOf(charlie)
    assert locker.claimableExitStreamBalance(alice) == 0
    assert locker.claimableExitStreamBalance(bob) == 0
    assert locker.claimableExitStreamBalance(charlie) == 0

# def test_aggregate_streams(locker, eps2, alice):
