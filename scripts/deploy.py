from brownie import Contract, ZERO_ADDRESS
from brownie import EllipsisToken2, FeeDistributor, IncentiveVoting, EllipsisLpStaking, TokenLocker, MerkleDistributor


# epoch time that transfers of the new token are possible
TOKEN_TRANSFERS_TIME = 1649808000  # 00:00:00 Thursday, April 13, 2022

# epoch time of the start of the first week within the protocol
# this is earlier than token transfers are enabled, so that as sppm as transfers
# live users may begin locking and voting for emissions in the following week
START_TIME = 1649289600  # 00:00:00 Thursday, April 7, 2022

MIGRATION_RATIO = 88  # 88 EPS2 for 1 EPS
MAX_SUPPLY = 1_500_000_000 * 10 ** 18 * MIGRATION_RATIO  # increases the total supply by 50%
MAX_MINTABLE = MAX_SUPPLY // 2  # if we migrate at exactly one year
INITIAL_REWARDS_PER_SECOND = 2893518518518518518 * MIGRATION_RATIO  # 7.5 million tokens over 30 days

MAX_LOCK_WEEKS = 52
QUORUM_PCT = 30
#  at 20 cents per token (pre-migration) it takes ~$11k of locked for 52 weeks to make a vote
TOKEN_APPROVAL_WEIGHT = 250_000_000 * 10 ** 18

MERKLE_ROOT = ""  # TODO hash for airdrop proof, to distro EPX bricked in the old staking contract

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
    token = EllipsisToken2.deploy(TOKEN_TRANSFERS_TIME, MAX_SUPPLY, epsv1, MIGRATION_RATIO, {"from": acct})
    locker = TokenLocker.deploy(token, stakingv1, START_TIME, MAX_LOCK_WEEKS, {'from': acct})
    voter = IncentiveVoting.deploy(locker, INITIAL_REWARDS_PER_SECOND, QUORUM_PCT, TOKEN_APPROVAL_WEIGHT, {'from': acct})
    fee_distro = FeeDistributor.deploy(locker, {'from': acct})
    staking = EllipsisLpStaking.deploy(token, voter, locker, MAX_MINTABLE, {'from': acct})
    merkle = MerkleDistributor.deploy(token, MERKLE_ROOT, {'from': acct})

    # set addresses
    voter.setLpStaking(staking, INITIAL_POOLS, {'from': acct})
    factory.set_fee_receiver(fee_distro, {'from': acct})
    token.setMinters([staking, merkle], {'from': acct})

    # for factory pools included in the initial rewards, set the deposit contract
    for pool in INITIAL_POOLS:
        pool = Contract(pool)
        if hasattr(pool, 'setDepositContract'):
            pool.setDepositContract(staking, True, {'from': acct})

    # TODO update factory `RewardsToken` implementation so `staking` is a default deposit contract
