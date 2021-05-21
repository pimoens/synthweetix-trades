import cryptocompare
from datetime import datetime
from enum import Enum
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
import logging
from random import randint
from requests import RequestException
import time
from tweepy import API, OAuthHandler, TweepError

__author__ = 'Pieter Moens'
__email__ = "pieter@pietermoens.be"


# Emojis: https://apps.timwhitlock.info/emoji/tables/unicode


SYNTHETIX_SUBGRAPH_API_ENDPOINT = 'https://api.thegraph.com/subgraphs/name/synthetixio-team/synthetix-exchanges'
CURVE_SUBGRAPH_API_ENDPOINT = 'https://api.thegraph.com/subgraphs/name/blocklytics/curve'

EYE_CATCHERS = [
    '\U0001F6A8 Alert: A Whale has been spotted in the trading waters!',
    'We are not afraid of large numbers! \U0001F4B8',
    'Another million dollar deal! \U0001F4B8'
]


class ExchangeType(Enum):
    TRADES = 'Trades'
    SWAPS = 'Cross-asset Swaps on #Curve'


class SynthweetixBot:

    def __init__(self, key, secret, access_token, access_secret, debug=False):
        auth = OAuthHandler(key, secret)
        auth.set_access_token(access_token, access_secret)
        self.api = API(auth)

        transport = RequestsHTTPTransport(
            url=SYNTHETIX_SUBGRAPH_API_ENDPOINT, verify=True, retries=3,
        )
        self.gql_client_synthetix = Client(transport=transport, fetch_schema_from_transport=True)

        transport = RequestsHTTPTransport(
            url=CURVE_SUBGRAPH_API_ENDPOINT, verify=True, retries=3,
        )
        self.gql_client_curve = Client(transport=transport, fetch_schema_from_transport=True)

        self.timestamp_last_fetch = int(time.time())
        self.debug = debug

    def send_tweet(self, type_: ExchangeType, message):
        message = f'\U0001F4B0 #Synthetix High Roller {type_.value} \U0001F4B0\n' \
                  f'{message}'

        logging.warning(message)
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
        result = self.gql_client_synthetix.execute(query)
        self.timestamp_last_fetch = int(time.time())
        return result.get('synthExchanges')

    def fetch_curve_swaps(self):
        query = gql(
            f"""
            query swaps {{
                swaps (
                        where: {{ 
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
        self.timestamp_last_fetch = int(time.time())
        return result.get('swaps')

    def create_trades_tweets(self, trades):
        for trade in trades:
            print(trade)

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
            if to_amount_usd >= 1000000 or from_amount_usd >= 1000000:
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
            print(swap)

            transaction = swap.get('transaction').get('hash')

            from_token = swap.get('fromToken').get('symbol')
            from_token_amount = float(swap.get('fromTokenAmountDecimal'))
            from_token_amount_usd = swap.get('fromTokenAmountUSD')

            to_token = swap.get('toToken').get('symbol')
            to_token_amount = float(swap.get('toTokenAmountDecimal'))
            to_token_amount_usd = swap.get('toTokenAmountUSD')

            message = []
            if from_token_amount_usd >= 1000000 or to_token_amount_usd >= 1000000:
                r = randint(0, 2)
                message.append(EYE_CATCHERS[r])
            message.extend([
                'FROM {:,.2f} {} (${:,.2f})'.format(from_token_amount, from_token, from_token_amount_usd),
                'TO {:,.2f} {} (${:,.2f})'.format(to_token_amount, to_token, to_token_amount_usd),
                'https://etherscan.io/tx/{}'.format(transaction),
            ])

            self.send_tweet(ExchangeType.SWAPS, '\n'.join(message))

    def execute(self, threshold=100000):
        start = datetime.now()
        logging.info('Running SynthweetixBot')

        try:
            # Trades
            logging.info(f'Fetching trades from TheGraph at {self.gql_client_synthetix.transport}')
            whales = [trade for trade in self.fetch_trades() if float(trade.get('toAmountInUSD')) / 1e18 >= threshold]

            logging.info('Sending tweets for trades')
            self.create_trades_tweets(whales)

            # Cross-asset Swaps
            logging.info(f'Fetching cross-asset swaps from TheGraph at {self.gql_client_curve.transport}')
            swaps = self.fetch_curve_swaps()
            whales = []

            prices = {}
            for swap in swaps:
                from_token = swap.get('fromToken').get('symbol')
                if from_token not in prices.keys():
                    prices[from_token] = cryptocompare.get_price(from_token, currency='USD').get(from_token).get('USD')

                to_token = swap.get('toToken').get('symbol')
                if to_token not in prices.keys():
                    prices[to_token] = cryptocompare.get_price(to_token, currency='USD').get(to_token).get('USD')

                from_token_amount_usd = float(swap.get('fromTokenAmountDecimal')) * prices.get(from_token)
                to_token_amount_usd = float(swap.get('toTokenAmountDecimal')) * prices.get(to_token)
                if to_token_amount_usd >= threshold:
                    swap['fromTokenAmountUSD'] = from_token_amount_usd
                    swap['toTokenAmountUSD'] = to_token_amount_usd
                    whales.append(swap)

            logging.info('Sending tweets for trades')
            self.create_swaps_tweets([whales[-1]])
        except RequestException as e:
            logging.error(e)

        end = datetime.now()
        logging.info(f'Executed SynthweetixBot in {end - start}s')
