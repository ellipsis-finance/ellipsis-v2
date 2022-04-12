# ellipsis-v2

Staking and emissions contracts for Ellipsis Finance v2.

Used in combination with the Ellipsis [stableswap factory](https://github.com/ellipsis-finance/factory).

##  Contracts

### `EllipsisToken2`

Ellipsis v2 protocol token (EPX). Contains logic for the token migration from EPS to EPX.

Deployment address: [`0xAf41054C1487b0e5E2B9250C0332eCBCe6CE9d71`](https://bscscan.com/address/0xAf41054C1487b0e5E2B9250C0332eCBCe6CE9d71#code)

### `TokenLocker`

Allows users to lock EPX for a given number of weeks. Locks are represented via a lock weight which is used for voting, emissions boosts and fee distribution.

Deployment address: [`0x22A93F53A0A3E6847D05Dd504283e8E296a49aAE`](https://bscscan.com/address/0x22A93F53A0A3E6847D05Dd504283e8E296a49aAE#code)

### `IncentiveVoting`

Voting contract for EPX emissions. Allows users to assign lock weight toward individual LP tokens, which determines the percent of new emissions that each token receives.

Deployment address: [`0x4695e50A38E33Ea09D1F623ba8A8dB24219bb06a`](https://bscscan.com/address/0x4695e50A38E33Ea09D1F623ba8A8dB24219bb06a#code)

### `LpStaking`

Staking contract for Ellipsis LP tokens, in order to receive EPX emissions.

Deployment address: [`0x5B74C99AA2356B4eAa7B85dC486843eDff8Dfdbe`](https://bscscan.com/address/0x5B74C99AA2356B4eAa7B85dC486843eDff8Dfdbe#code)

### `FeeDistributor`

Distribution of protocol fees according to user lock weights.

Deployment address: [`0x3670c10C6a4994EC8926eDCf54bF53092217EE1b`](https://bscscan.com/address/0x3670c10C6a4994EC8926eDCf54bF53092217EE1b#code)

### `MerkleDistributor`

One-time token distributor, used to airdrop EPX to users with EPS balances that cannot be withdrawn from the v1 staker at the time of the migration.

Deployment address: [`0xA7BD1fb19D0af2739431Dd1D318A8A04cd52b9Ff`](https://bscscan.com/address/0xA7BD1fb19D0af2739431Dd1D318A8A04cd52b9Ff#code)

## Audit

This codebase has been audited by Peckshield. The audit report is available [here](https://github.com/ellipsis-finance/ellipsis-audits/blob/master/PeckShield-Audit-Report-EllipsisV2Staking-v1.0.pdf).
