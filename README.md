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

Concerning data collection, all data is queried from TheGraph API ([Synthethix Exchanges subgraph](https://thegraph.com/explorer/subgraph/synthetixio-team/synthetix-exchanges))
using the [gql](https://pypi.org/project/gql/). The query details can be found in the source code.


### Twitter bot

I have opted to create a simple, well-structured Python solution using [tweepy](https://www.tweepy.org/). 
The bot is up and running at [https://twitter.com/synthweetix-trades](https://twitter.com/synthweetix). 

It queries TheGraph every 5min (can be easily configured) to fetch all exchanges since the last pull.
When the exchange value is larger than a set threshold (default is $100,000), a tweet is sent.

**Preview**

![preview](docs/example_trades_tweet.png)


## Deployment

### Configuration

#### Environment variables

| Name                      | Description                                                     | Default                                                                        |
| :-------------:           | :-------------:                                                 | :-----:                                                                        |
| CONFIGURATION             | Configuration to run (`development`, `production` or `cronjob`) | `development`                                                                  |
| TWITTER_CONSUMER_KEY      | Twitter Consumer Key                                            | `''`                                                                           |
| TWITTER_CONSUMER_SECRET   | Twitter Consumer Secret                                         | `''`                                                                           |
| TWITTER_ACCESS_TOKEN      | Twitter OAuth Access Token                                      | `''`                                                                           |
| TWITTER_ACCESS_SECRET     | Twitter OAuth Access Secret                                     | `''`                                                                           |
| SUBGRAPH_API_ENDPOINT     | API Endpoint of the Synthetix Exchanges subgraph                | `https://api.thegraph.com/subgraphs/name/synthetixio-team/synthetix-exchanges` |
| THRESHOLD                 | Threshold (in USD)                                              | `100000`                                                                       |

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