import pytest
from brownie import ZERO_ADDRESS, accounts, chain
from brownie_tokens import ERC20

# epoch time that transfers of the new token are possible
TOKEN_TRANSFERS_TIME = 1649808000  # 00:00:00 Thursday, April 13, 2022

START_TIME =    1649289600  # 00:00:00 Thursday, April 7, 2022
START_GAUGE_VOTING = START_TIME + (604800*2)
MIGRATION_RATIO = 88  # 88 EPS2 for 1 EPS
MAX_SUPPLY = 1_500_000_000 * 10 ** 18 * MIGRATION_RATIO  # increases the total supply by 50%
MAX_MINTABLE = MAX_SUPPLY // 2  # if we migrate at exactly one year
INITIAL_REWARDS_PER_SECOND = 2893518518518518518  # 7.5 million tokens over 30 days

MAX_LOCK_WEEKS = 52
QUORUM_PCT = 30
#  at 20 cents per token (pre-migration) it takes ~$11k of locked for 52 weeks to make a vote
TOKEN_APPROVAL_WEIGHT = 250_000_000 * 10 ** 18

# might need to mock these or just test on a fork
INITIAL_POOLS = [
    "0xaF4dE8E872131AE328Ce21D909C74705d3Aaf452",   # 3EPS
    "0x2a435Ecb3fcC0E316492Dc1cdd62d0F189be5640",   # BTCEPS
]


@pytest.fixture(autouse=True)
def isolate(fn_isolation):
    pass

# session scope

@pytest.fixture(scope="session")
def max_supply():
    return MAX_SUPPLY


@pytest.fixture(scope="session")
def start_time():
    return START_TIME


@pytest.fixture(scope="session")
def transfer_time():
    return TOKEN_TRANSFERS_TIME


@pytest.fixture(scope="session")
def start_gauge_voting():
    return START_GAUGE_VOTING


@pytest.fixture(scope="session")
def migration_ratio():
    return MIGRATION_RATIO


@pytest.fixture(scope="session")
def alice():
    return accounts[0]


@pytest.fixture(scope="session")
def bob():
    return accounts[1]


@pytest.fixture(scope="session")
def charlie():
    return accounts[2]


@pytest.fixture(scope="session")
def dan():
    return accounts[3]


@pytest.fixture(scope="module")
def eps(alice):
    return ERC20({'from': alice})


@pytest.fixture(scope="module")
def initial_pools():
    return INITIAL_POOLS


@pytest.fixture(scope="module")
def incentive1():
    return ERC20({'from': alice})


@pytest.fixture(scope="module")
def incentive2():
    return ERC20({'from': alice})

@pytest.fixture(scope="module")
def v1_staker_mock():
    return ERC20({'from': alice})


@pytest.fixture(scope="module")
def lp_tokens(RewardsToken, alice):
    ret = []
    for i in range(10):
        ret.append(RewardsToken.deploy({'from': alice}))
    return ret


@pytest.fixture(scope="module")
def pools(Pool, alice):
    ret = []
    for i in range(10):
        ret.append(Pool.deploy({'from': alice}))
    return ret

@pytest.fixture(scope="session")
def setup_gauges():
    return INITIAL_POOLS
    # ret = []
    # for i in INITIAL_POOLS:
    #     ret.append(Pool.deploy({'from': alice}))



# ellipsis contracts

@pytest.fixture(scope="module")
def eps2(EllipsisToken2, eps, alice):
    token = EllipsisToken2.deploy(TOKEN_TRANSFERS_TIME, MAX_SUPPLY, eps, MIGRATION_RATIO, {'from': alice})
    return token


@pytest.fixture(scope="module")
def locker(TokenLocker, eps2, alice):
    locker = TokenLocker.deploy(eps2, "0x2a435Ecb3fcC0E316492Dc1cdd62d0F189be5640", START_TIME, MAX_LOCK_WEEKS, MIGRATION_RATIO, {'from': alice})
    return locker


@pytest.fixture(scope="module")
def voter(IncentiveVoting, locker, alice):
    voter = IncentiveVoting.deploy(locker, INITIAL_REWARDS_PER_SECOND, QUORUM_PCT, TOKEN_APPROVAL_WEIGHT, {'from': alice})
    return voter


@pytest.fixture(scope="module")
def fee_distro(FeeDistributor, locker, alice):
    fee_distro = FeeDistributor.deploy(locker, {'from': alice})
    return fee_distro


@pytest.fixture(scope="module")
def fee_distro_tester(FeeDistributorTester, alice):
    fee_distro_tester = FeeDistributorTester.deploy({'from': alice})
    return fee_distro_tester


# note INITIAL_POOLS is not set up.
@pytest.fixture(scope="module")
def lp_staker(EllipsisLpStaking, eps2, locker, voter, alice):
    staking = EllipsisLpStaking.deploy(eps2, voter, locker, MAX_MINTABLE, {'from': alice})
    voter.setLpStaking(staking, INITIAL_POOLS, {"from": alice})
    eps2.addMinter(staking, {"from": alice})
    return staking
