from brownie import Contract, ZERO_ADDRESS
from brownie import EllipsisToken2, FeeDistributor, IncentiveVoting, EllipsisLpStaking, TokenLocker


# epoch time that transfers of the new token are possible
START_TIME = 1649894400  # 00:00:00 Thursday, April 14, 2022

MIGRATION_RATIO = 88  # 88 EPS2 for 1 EPS
MAX_SUPPLY = 1_500_000_000 * 10 ** 18 * MIGRATION_RATIO  # increases the total supply by 50%
MAX_MINTABLE = MAX_SUPPLY // 2  # if we migrate at exactly one year
INITIAL_REWARDS_PER_SECOND = 2893518518518518518  # 7.5 million tokens over 30 days

MAX_LOCK_WEEKS = 52
QUORUM_PCT = 30

# list of initial pools that get EPS incentives immediately in the new system.
# important to consider that all non-factory pools that we handle this way will
# be unable to receive 3rd-party incentives. In some cases we should instead
# encourage liquidity to migrate.
INITIAL_POOLS = [
    "0xaF4dE8E872131AE328Ce21D909C74705d3Aaf452",   # 3EPS
    "0x2a435Ecb3fcC0E316492Dc1cdd62d0F189be5640",   # BTCEPS
]

EPS_V1 = "0xa7f552078dcc247c2684336020c03648500c6d9f"
EPS_STAKING_V1 = "0x4076CC26EFeE47825917D0feC3A79d0bB9a6bB5c"
FACTORY = "0xf65BEd27e96a367c61e0E06C54e14B16b84a5870"


def main():
    # brick the old system
    epsv1 = Contract(EPS_V1)
    stakingv1 = Contract("0x4076CC26EFeE47825917D0feC3A79d0bB9a6bB5c")
    stakingv1.addReward(ZERO_ADDRESS, ZERO_ADDRESS, {"from": stakingv1.owner()})

    factory = Contract(FACTORY)
    acct = factory.admin()

    # deploy the new contracts
    token = EllipsisToken2.deploy(START_TIME, MAX_SUPPLY, epsv1, MIGRATION_RATIO, {"from": acct})
    locker = TokenLocker.deploy(token, START_TIME, MAX_LOCK_WEEKS, {'from': acct})
    voter = IncentiveVoting.deploy(locker, INITIAL_REWARDS_PER_SECOND, QUORUM_PCT, {'from': acct})
    fee_distro = FeeDistributor.deploy(locker, {'from': acct})
    staking = EllipsisLpStaking.deploy(token, voter, locker, MAX_MINTABLE, INITIAL_POOLS, {'from': acct})

    # set addresses
    voter.setLpStaking(staking, {'from': acct})
    factory.set_fee_receiver(fee_distro, {'from': acct})
    token.setMinters([staking], {'from': acct})  # TODO merkle distributor is also a minter

    # for factory pools included in the initial rewards, set the deposit contract
    for pool in INITIAL_POOLS:
        pool = Contract(pool)
        if hasattr(pool, 'setDepositContract'):
            pool.setDepositContract(staking, True, {'from': acct})

    # TODO
    # - update RewardsToken implementation so that `staking` is a deposit contract by default
    # - create merkle for airdrop, deploy `MerkleDistributor`  (need a snapshot script)
