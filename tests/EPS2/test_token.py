from operator import lt
import brownie
import pytest
from brownie import ZERO_ADDRESS, accounts, chain
from brownie.test import given, strategy

# @pytest.fixture(scope="module", autouse=True)
# def setup(eps2, eps, lp_staker, alice):
#     eps2.addMinter(lp_staker, {"from": alice})

# basic tests for now, can be broken up into
# other tests once built out more

def test_is_minter_set(eps2, lp_staker, alice):
    assert eps2.minters(lp_staker) == True


def test_migrate(eps2, eps, alice):
    alice_bal0 = eps2.balanceOf(alice)
    amount = 100 * 10 ** 18
    eps._mint_for_testing(alice, amount)
    eps.approve(eps2, amount, {"from": alice})
    eps2.migrate(alice, amount, {"from": alice})
    alice_bal1 = eps2.balanceOf(alice)
    alice_after = alice_bal0 - alice_bal1
    migration_ratio = eps2.migrationRatio()
    assert alice_bal1 - alice_bal0 == amount * migration_ratio


# should fail in the transfer
def test_migrate_too_many(eps2, eps, alice):
    amount = 100 * 10 ** 18
    eps._mint_for_testing(alice, amount)
    eps.approve(eps2, amount+10, {"from": alice})
    with brownie.reverts():
        eps2.migrate(alice, amount+10, {"from": alice})


def test_mint_non_minter(eps2, alice):
    with brownie.reverts("Not a minter"):
        eps2.mint(alice, 10000000, {"from": alice})


def test_transfer_before_starttime(eps2, eps, alice, bob):
    amount = 100 * 10 ** 18
    eps._mint_for_testing(alice, amount)
    eps.approve(eps2, amount, {"from": alice})
    eps2.migrate(alice, amount, {"from": alice})
    with brownie.reverts("Transfers not yet enabled"):
        eps2.transfer(bob, 5, {"from": alice})


def test_transfer_after_starttime(eps2, eps, alice, bob, transfer_time):
    bob_bal0 = eps2.balanceOf(bob)
    amount = 100 * 10 ** 18
    eps._mint_for_testing(alice, amount)
    eps.approve(eps2, amount, {"from": alice})
    eps2.migrate(alice, amount, {"from": alice})
    delta = transfer_time - chain.time()
    chain.mine(timedelta=delta)
    eps2.transfer(bob, 5)
    bob_bal1 = eps2.balanceOf(bob)
    assert bob_bal1 - bob_bal0 == 5


