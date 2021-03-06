# Synthweetix - Twitter Bot for Synthetix High Roller Trades

This project is a submission to the [Open DeFi Hackathon](https://gitcoin.co/issue/snxgrants/open-defi-hackathon/4/100025662).

## Challenge description

Build a Twitter bot that tweets when a Synthetix Protocol trade occurs over a certain value threshold.

Extra features:
- Include Cross-asset Swaps on Curve
- Include large short positions
- Insert your creative idea here!

## Solution

### Data collection

#### Trades

Concerning data collection, all data is queried from TheGraph API ([Synthethix Exchanges subgraph](https://thegraph.com/explorer/subgraph/synthetixio-team/synthetix-exchanges))
using the [gql](https://pypi.org/project/gql/). The query details can be found in the source code.

#### Cross-asset Swaps on Curve

For Cross-asset Swaps on Curve, the data is collected from TheGraph API ([Blocklytics Curve subgraph](https://thegraph.com/explorer/subgraph/blocklytics/curve)).
The prices are converted to USD using [cryptocompare](https://pypi.org/project/cryptocompare/).

The [EtherScan API](https://etherscan.io/apis) is used to validate that the retrieved Swaps (from the subgraph) are actual Cross-Asset Swaps.
This is done by matching the retrieved hashes to the [Vyper Contract](https://etherscan.io/address/0x58a3c68e2d3aaf316239c003779f71acb870ee47).

#### Short positions

For the Short positions, the data is collected from TheGraph API ([Synthethix Shorts subgraph](https://api.thegraph.com/subgraphs/name/synthetixio-team/synthetix-shorts)).
The prices are converted to USD using [cryptocompare](https://pypi.org/project/cryptocompare/) and [pycoingecko](https://github.com/man-c/pycoingecko) for sETH and sBTC.

### Twitter bot

I have opted to create a simple, well-structured Python solution using [tweepy](https://www.tweepy.org/). 
The bot is up and running at [https://twitter.com/synthweetix-trades](https://twitter.com/synthweetix). 

It queries TheGraph every 5min (can be easily configured) to fetch all exchanges since the last pull.
When the exchange value is larger than a set threshold (default is $250,000), a tweet is sent.
An additional threshold is introduced to optionally send an eye catcher line with the tweet (default is $1,000,000).

**Preview**

![trade](docs/example_trade_tweet.png)
![cross-asset swap](docs/example_crossassetswap_tweet.png)


## Deployment

### Configuration

#### Environment variables

| Name                           | Description                                                     | Default         |
| :-------------:                | :-------------:                                                 | :-----:         |
| CONFIGURATION                  | Configuration to run (`development`, `production` or `cronjob`) | `development`   |
| TWITTER_CONSUMER_KEY           | Twitter Consumer Key                                            | `''`            |
| TWITTER_CONSUMER_SECRET        | Twitter Consumer Secret                                         | `''`            |
| TWITTER_ACCESS_TOKEN           | Twitter OAuth Access Token                                      | `''`            |
| TWITTER_ACCESS_SECRET          | Twitter OAuth Access Secret                                     | `''`            |
| ETHERSCAN_API_KEY              | EtherScan API Key (used for Cross-Asset Swap validation)        | `''`            |
| TRADE_VALUE_THRESHOLD          | Trade Value Threshold (in USD)                                  | `250000`        |
| SHORT_POSITION_VALUE_THRESHOLD | Threshold used for Short Positions (in USD)                     | `100000`        |
| EYE_CATCHER_THRESHOLD          | Threshold (in USD) used to add additional eye catcher lines     | `1000000`       |

### Heroku

Application is deployed on [Heroku](https://heroku.com) using a CronJob

```
clock: python main.py
```

**Note:** Scale up the process when deploying for the first time using the Heroki CLI

```
heroku ps:scale clock=1
```

### Docker

Dockerfile has been included for deployment using Docker