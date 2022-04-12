from brownie import Contract, ZERO_ADDRESS
from brownie import EllipsisToken2, FeeDistributor, IncentiveVoting, EllipsisLpStaking, TokenLocker, MerkleDistributor


# epoch time that transfers of the new token are possible
TOKEN_TRANSFERS_TIME = 1649808000  # 00:00:00 Thursday, April 13, 2022

# epoch time of the start of the first week within the protocol
# this is earlier than token transfers are enabled, so that as soon as transfers
# live users may begin locking and voting for emissions in the following week
START_TIME = 1649289600  # 00:00:00 Thursday, April 7, 2022

MIGRATION_RATIO = 88  # 88 EPS2 for 1 EPS
MAX_SUPPLY = 1_500_000_000 * 10 ** 18 * MIGRATION_RATIO  # increases the total supply by 50%
MAX_MINTABLE = MAX_SUPPLY // 2  # if we migrate at exactly one year
INITIAL_REWARDS_PER_SECOND = 2893518518518518518 * MIGRATION_RATIO  # 7 million tokens over 28 days

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
    "0xaF4dE8E872131AE328Ce21D909C74705d3Aaf452",
    "0x5b5bD8913D766D005859CE002533D4838B0Ebbb5",
    "0xf71A0bCC3Ef8a8c5a28fc1BC245e394A8ce124ec",
    "0x3e33ec615eB41148785653c119835Bd224Fd2d1B",
    "0x6937A9C8Af919ebf756d56E715F4c8b9F1df3184",
    "0xD67625ad4104dA86c4D9CB054001E899B1b9061B",
    "0x13fe09F5D9BDBD09D875B51ba2f1E3f4544896bC",
    "0xEAaD1b47283aB31A7ae92Dc156c963584D35120D",
    "0x4084203AfBc9b20A3ECB9C80dc164a13C9A41eEb",
    "0x1B6E11c5DB9B15DE87714eA9934a6c52371CfEA9",
    "0xd6e049b3e8E19deC54834046e48C15AF9374467a",
    "0x82c8ce39d0fF337C6867Cdf26609a1728f9f1B58",
    "0x5dF71B9CB8EA13Dec57b63EA558B135aE06ac859",
    "0x8087a94FFE6bcF08DC4b4EBB3d28B4Ed75a792aC",
    "0xdC7f3E34C43f8700B0EB58890aDd03AA84F7B0e1",
    "0x5eE318b2AD8B45675Dc169C68A273CAf8fb26ee0",
    "0x4A96801f76DdfC182290105AeEb3E4719ff9A380",
    "0x5A81b0C7a43a5A39031A9926483A055F6355fEdf",
    "0x4CfAaBd5920021359BB22bB6924CCe708773b6AC",
    "0xF6be0F52Be5e68DF4Ed3ea7cCD569C16024C250D",
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
    locker = TokenLocker.deploy(token, stakingv1, START_TIME, MAX_LOCK_WEEKS, MIGRATION_RATIO, {'from': acct})
    voter = IncentiveVoting.deploy(locker, INITIAL_REWARDS_PER_SECOND, QUORUM_PCT, TOKEN_APPROVAL_WEIGHT, {'from': acct})
    fee_distro = FeeDistributor.deploy(locker, {'from': acct})
    staking = EllipsisLpStaking.deploy(token, voter, locker, MAX_MINTABLE, {'from': acct})
    merkle = MerkleDistributor.deploy(token, MERKLE_ROOT, {'from': acct})

    # set addresses
    voter.setLpStaking(staking, INITIAL_POOLS, {'from': acct})
    factory.set_fee_receiver(fee_distro, {'from': acct})
    token.addMinter(merkle, {'from': acct})
    token.addMinter(staking, {'from': acct})

    # for factory pools included in the initial rewards, set the deposit contract
    for pool in INITIAL_POOLS:
        pool = Contract(pool)
        if hasattr(pool, 'setDepositContract'):
            pool.setDepositContract(staking, True, {'from': acct})
