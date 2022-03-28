# ellipsis-v2

Staking and emissions contracts for Ellipsis Finance v2.

Used in combination with the Ellipsis [stableswap factory](https://github.com/ellipsis-finance/factory).

## Development Status

All core logic is considered final, however we are still performing internal reviews and additional testing. We do not expect any changes to public interfaces or control flow.

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

One-time token distributor, used to airdrop EPX to users with EPS balances that cannot be withdrawn from the v1 staker at the time of the migration.

## Audit

This codebase has been audited by Peckshield. The audit report is available [here](https://github.com/ellipsis-finance/ellipsis-audits/blob/master/PeckShield-Audit-Report-EllipsisV2Staking-v1.0.pdf).
