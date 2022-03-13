# ellipsis-v2

Staking and emissions contracts for Ellipsis Finance v2.

Used in combination with the Ellipsis [stableswap factory](https://github.com/ellipsis-finance/factory).

##  Contracts

### `EllipsisToken2`

Ellipsis v2 protocol token (EPX). Contains logic for the token migration from EPS to EPX.

### `TokenLocker`

Allows users to lock EPX for a given number of weeks. Locks are represented via a lock weight which is used for voting, emissions boosts and fee distribution.

### `IncentiveVoting`

Voting contract for EPX emissions. Allows users to assign lock weight toward individual LP tokens, which determines the percent of new emissions that each token receives.

### `LpStaking`

Staking contract for Ellipsis LP tokens, in order to receive EPX emissions.

### `FeeDistributor`

Distribution of protocol fees according to user lock weights.

### `MerkleDistributor`

One-time token distributor, used to airdrop EPX to users with locked EPS balances at the time of the migration.