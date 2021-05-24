import json

import cryptocompare
from datetime import datetime
from enum import Enum
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
import logging
from pycoingecko import CoinGeckoAPI
from random import randint
import requests
import time
from tweepy import API, OAuthHandler, TweepError

__author__ = 'Pieter Moens'
__email__ = "pieter@pietermoens.be"

# Emojis: https://apps.timwhitlock.info/emoji/tables/unicode

# TheGraph endpoints
EXCHANGE_SUBGRAPH_API_ENDPOINT = 'https://api.thegraph.com/subgraphs/name/synthetixio-team/synthetix-exchanges'
CURVE_SUBGRAPH_API_ENDPOINT = 'https://api.thegraph.com/subgraphs/name/blocklytics/curve'
SHORTS_SUBGRAPH_API_ENDPOINT = 'https://api.thegraph.com/subgraphs/name/synthetixio-team/synthetix-shorts'

# EtherScan Vyper Contract
ETHERSCAN_VYPER_CONTRACT = '0x58A3c68e2D3aAf316239c003779F71aCb870Ee47'

EYE_CATCHERS = [
    '\U0001F6A8 Alert: A Whale has been spotted in the trading waters!',
    'We are not afraid of large numbers! \U0001F4B8',
    'Another million dollar deal! \U0001F4B8'
]


class ExchangeType(Enum):
    TRADES = 'Trades'
    SWAPS = 'Cross-asset Swaps on #Curve'
    SHORTS = 'Short Positions'


class SynthweetixBot:

    def __init__(self, key, secret, access_token, access_secret, etherscan_api_key,
                 trade_value_threshold=250000, eye_catcher_threshold=1000000,
                 debug=False):
        auth = OAuthHandler(key, secret)
        auth.set_access_token(access_token, access_secret)
        self.api = API(auth)

        self.etherscan_api_key = etherscan_api_key

        # Trades
        transport = RequestsHTTPTransport(
            url=EXCHANGE_SUBGRAPH_API_ENDPOINT, verify=True, retries=3,
        )
        self.gql_client_synthetix_exchanges = Client(transport=transport, fetch_schema_from_transport=True)

        # Cross-asset Swaps
        transport = RequestsHTTPTransport(
            url=CURVE_SUBGRAPH_API_ENDPOINT, verify=True, retries=3,
        )
        self.gql_client_curve = Client(transport=transport, fetch_schema_from_transport=True)

        # Short positions
        transport = RequestsHTTPTransport(
            url=SHORTS_SUBGRAPH_API_ENDPOINT, verify=True, retries=3,
        )
        self.gql_client_synthetix_shorts = Client(transport=transport, fetch_schema_from_transport=True)

        # CoinGecko
        self.cg = CoinGeckoAPI()

        self.trade_value_threshold = trade_value_threshold
        self.eye_catcher_threshold = eye_catcher_threshold

        self.timestamp_last_fetch = int(time.time())
        self.debug = debug

    def send_tweet(self, type_: ExchangeType, message):
        message = f'\U0001F4B0 #Synthetix High Roller {type_.value} \U0001F4B0\n' \
                  f'{message}'

        logging.info(message)
        if not self.debug:
            try:
                self.api.update_status(message)
            except TweepError as e:
                logging.warning(e)

    def fetch_trades(self):
        query = gql(
            f"""
            query getSynthExchanges {{
                synthExchanges (
                        where: {{ 
                            timestamp_gte: {self.timestamp_last_fetch}
                        }}, orderBy: timestamp, orderDirection: asc) 
                {{
                    id
                    account
                    from
                    fromCurrencyKey
                    fromAmount
                    fromAmountInUSD
                    toCurrencyKey
                    toAmount
                    toAmountInUSD
                    feesInUSD
                    timestamp
                }}
            }}
            """
        )
        result = self.gql_client_synthetix_exchanges.execute(query)
        return result.get('synthExchanges')

    def fetch_vyper_transactions(self):
        start_block = int(json.loads(requests.get(
            f'https://api.etherscan.io/api?module=block&action=getblocknobytime&timestamp={self.timestamp_last_fetch}&closest=after&apikey={self.etherscan_api_key}'
        ).text)['result'])

        txs = json.loads(requests.get(
            f'https://api.etherscan.io/api?module=account&action=txlist&address={ETHERSCAN_VYPER_CONTRACT}&startblock={start_block}&sort=asc&apikey={self.etherscan_api_key}'
        ).text)['result']
        return txs

    def fetch_curve_swaps(self):
        query = gql(
            f"""
            query swaps {{
                swaps (
                        where: {{ 
                            timestamp_gte: {self.timestamp_last_fetch}
                        }}, orderBy: timestamp, orderDirection: asc) 
                {{
                    fromToken {{
                      symbol
                    }}
                    fromTokenAmountDecimal
                    toToken {{
                      symbol
                    }}
                    toTokenAmountDecimal
                    underlyingPrice
                    timestamp
                    transaction {{
                      hash
                    }}
                }}
            }}
            """
        )
        result = self.gql_client_curve.execute(query)
        return result.get('swaps')

    def fetch_shorts(self):
        query = gql(
            f"""
            query shorts {{
                shorts (
                        where: {{ 
                            isOpen: true,
                            createdAt_gte: {self.timestamp_last_fetch}
                        }}, orderBy: createdAt, orderDirection: asc) 
                {{
                    id
                    txHash
                    account
                    collateralLocked
                    collateralLockedAmount
                    synthBorrowed
                    synthBorrowedAmount
                    createdAt
                }}
            }}
            """
        )
        result = self.gql_client_synthetix_shorts.execute(query)
        return result.get('shorts')

    def create_trades_tweets(self, trades):
        for trade in trades:
            account = trade.get('account')

            from_ = trade.get('from')
            from_amount = float(trade.get('fromAmount')) / 1e18
            from_currency = bytes.fromhex(trade.get('fromCurrencyKey')[2:10]).decode('utf-8')
            from_amount_usd = float(trade.get('fromAmountInUSD')) / 1e18

            to_ = trade.get('to')
            to_amount = float(trade.get('toAmount')) / 1e18
            to_currency = bytes.fromhex(trade.get('toCurrencyKey')[2:10]).decode('utf-8')
            to_amount_usd = float(trade.get('toAmountInUSD')) / 1e18

            fees_usd = float(trade.get('feesInUSD')) / 1e18

            message = []
            if to_amount_usd >= self.eye_catcher_threshold or from_amount_usd >= self.eye_catcher_threshold:
                r = randint(0, 2)
                message.append(EYE_CATCHERS[r])
            message.extend([
                'FROM {:,.2f} {} (${:,.2f})'.format(from_amount, from_currency, from_amount_usd),
                'TO {:,.2f} {} (${:,.2f})'.format(to_amount, to_currency, to_amount_usd),
                'FEES = {:,.2f}'.format(fees_usd),
                'https://etherscan.io/address/{}'.format(account),
            ])

            self.send_tweet(ExchangeType.TRADES, '\n'.join(message))

    def create_swaps_tweets(self, swaps):
        for swap in swaps:
            transaction = swap.get('transaction').get('hash')

            from_token = swap.get('fromToken').get('symbol')
            from_token_amount = float(swap.get('fromTokenAmountDecimal'))
            from_token_amount_usd = swap.get('fromTokenAmountUSD')

            to_token = swap.get('toToken').get('symbol')
            to_token_amount = float(swap.get('toTokenAmountDecimal'))
            to_token_amount_usd = swap.get('toTokenAmountUSD')

            message = []
            if from_token_amount_usd >= self.eye_catcher_threshold or to_token_amount_usd >= self.eye_catcher_threshold:
                r = randint(0, 2)
                message.append(EYE_CATCHERS[r])
            message.extend([
                'FROM {:,.2f} {} (${:,.2f})'.format(from_token_amount, from_token, from_token_amount_usd),
                'TO {:,.2f} {} (${:,.2f})'.format(to_token_amount, to_token, to_token_amount_usd),
                'https://etherscan.io/tx/{}'.format(transaction),
            ])

            self.send_tweet(ExchangeType.SWAPS, '\n'.join(message))

    def create_shorts_tweets(self, shorts):
        for short in shorts:
            tx_hash = short.get('txHash')

            synth_borrowed = short.get('synthBorrowed')
            synth_borrowed_amount = short.get('synthBorrowedAmount')
            synth_borrowed_amount_usd = short.get('synthBorrowedAmountUSD')

            collateral_locked = short.get('collateralLocked')
            collateral_locked_amount = short.get('collateralLockedAmount')
            collateral_locked_amount_usd = short.get('collateralLockedAmountUSD')

            message = []
            if synth_borrowed_amount_usd >= self.eye_catcher_threshold:
                r = randint(0, 2)
                message.append(EYE_CATCHERS[r])
            message.extend([
                'SYNTH BORROWED {:,.2f} {} (${:,.2f})'.format(synth_borrowed_amount, synth_borrowed,
                                                              synth_borrowed_amount_usd),
                'COLLATERAL LOCKED {:,.2f} {} (${:,.2f})'.format(collateral_locked_amount, collateral_locked,
                                                                 collateral_locked_amount_usd),
                'https://etherscan.io/tx/{}'.format(tx_hash),
            ])

            self.send_tweet(ExchangeType.SHORTS, '\n'.join(message))

    def execute(self):
        start = datetime.now()
        logging.info('Running SynthweetixBot')

        try:
            prices = {}

            # Trades
            logging.info(f'Fetching trades from TheGraph at {self.gql_client_synthetix_exchanges.transport}')
            whales = [trade for trade in self.fetch_trades()
                      if float(trade.get('toAmountInUSD')) / 1e18 >= self.trade_value_threshold]

            logging.info('Sending tweets for trades')
            self.create_trades_tweets(whales)

            # Cross-asset Swaps
            logging.info(f'Fetching cross-asset swaps from TheGraph at {self.gql_client_curve.transport}')
            swaps = self.fetch_curve_swaps()
            whales = []

            txs = self.fetch_vyper_transactions()

            for swap in swaps:
                if swap.get('transaction').get('hash') in txs:  # Check if swap is an actual Cross-Asset Swap
                    from_token = swap.get('fromToken').get('symbol')
                    if from_token not in prices.keys():
                        prices[from_token] = cryptocompare.get_price(from_token, currency='usd') \
                            .get(from_token.upper()).get('USD')

                    to_token = swap.get('toToken').get('symbol')
                    if to_token not in prices.keys():
                        prices[to_token] = cryptocompare.get_price(to_token, currency='usd') \
                            .get(to_token.upper()).get('USD')

                    from_token_amount_usd = float(swap.get('fromTokenAmountDecimal')) * prices.get(from_token)
                    to_token_amount_usd = float(swap.get('toTokenAmountDecimal')) * prices.get(to_token)
                    if to_token_amount_usd >= self.trade_value_threshold:
                        swap['fromTokenAmountUSD'] = from_token_amount_usd
                        swap['toTokenAmountUSD'] = to_token_amount_usd
                        whales.append(swap)

            logging.info('Sending tweets for cross-asset swaps')
            self.create_swaps_tweets(whales)

            # Short positions
            logging.info(f'Fetching short positions from TheGraph at {self.gql_client_synthetix_shorts.transport}')
            shorts = self.fetch_shorts()
            whales = []

            for short in shorts:
                synth_token = bytes.fromhex(short.get('synthBorrowed')[2:10]).decode('utf-8')
                if synth_token not in prices.keys():
                    prices[synth_token] = self.cg.get_price(ids=synth_token, vs_currencies='usd') \
                        .get(synth_token.lower()).get('usd')

                collateral_token = bytes.fromhex(short.get('collateralLocked')[2:10]).decode('utf-8')
                if collateral_token not in prices.keys():
                    prices[collateral_token] = cryptocompare.get_price(collateral_token, currency='usd') \
                        .get(collateral_token.upper()).get('USD')

                synth_borrowed_amount = float(short.get('synthBorrowedAmount')) / 1e18
                synth_borrowed_amount_usd = synth_borrowed_amount * prices.get(synth_token)

                collateral_locked_amount = float(short.get('collateralLockedAmount')) / 1e18
                collateral_locked_amount_usd = collateral_locked_amount * prices.get(collateral_token)

                if synth_borrowed_amount_usd >= self.trade_value_threshold:
                    short['synthBorrowed'] = synth_token
                    short['synthBorrowedAmount'] = synth_borrowed_amount
                    short['synthBorrowedAmountUSD'] = synth_borrowed_amount_usd

                    short['collateralLocked'] = collateral_token
                    short['collateralLockedAmount'] = collateral_locked_amount
                    short['collateralLockedAmountUSD'] = collateral_locked_amount_usd
                    whales.append(short)

            logging.info('Sending tweets for short positions')
            self.create_shorts_tweets(whales)

            self.timestamp_last_fetch = int(time.time())
        except requests.RequestException as e:
            logging.error(e)

        end = datetime.now()
        logging.info(f'Executed SynthweetixBot in {end - start}s')
