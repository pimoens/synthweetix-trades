from datetime import datetime
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


eye_catchers = [
    '\U0001F6A8 Alert: A Whale has been spotted in the trading waters!',
    'We are not afraid of large numbers! \U0001F4B8',
    'Another million dollar deal! \U0001F4B8'
]


class SynthweetixBot:

    def __init__(self, key, secret, access_token, access_secret, subgraph_endpoint, debug=False):
        auth = OAuthHandler(key, secret)
        auth.set_access_token(access_token, access_secret)
        self.api = API(auth)

        transport = RequestsHTTPTransport(
            url=subgraph_endpoint, verify=True, retries=3,
        )
        self.gql_client = Client(transport=transport, fetch_schema_from_transport=True)

        self.timestamp_last_fetch = int(time.time())
        self.debug = debug

    def send_tweet(self, message):
        message = f'\U0001F4B0 #Synthetix High Roller Trades \U0001F4B0\n' \
                  f'{message}'

        logging.warning(message)
        if not self.debug:
            try:
                self.api.update_status(message)
            except TweepError as e:
                logging.warning(e)

    def fetch_trades(self,):
        query = gql(
            f"""
            query getSynthExchanges {{
                synthExchanges (
                        where: {{ 
                            timestamp_gte: {self.timestamp_last_fetch}
                        }}, orderBy: timestamp, orderDirection: desc) 
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
        result = self.gql_client.execute(query)
        self.timestamp_last_fetch = int(time.time())
        return result.get('synthExchanges')

    def create_tweets(self, whales):
        for trade in whales:
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
                message.append(eye_catchers[r])
            message.extend([
                'FROM {:,.2f} {} (${:,.2f})'.format(from_amount, from_currency, from_amount_usd),
                'TO {:,.2f} {} (${:,.2f})'.format(to_amount, to_currency, to_amount_usd),
                'FEES = {:,.2f}'.format(fees_usd),
                'https://etherscan.io/address/{}'.format(account),
            ])

            self.send_tweet('\n'.join(message))

    def execute(self, threshold=100000):
        start = datetime.now()
        logging.info('Running SynthweetixBot')

        try:
            logging.info(f'Fetching trades from TheGraph at {self.gql_client.transport}')
            whales = [trade for trade in self.fetch_trades() if float(trade.get('fromAmountInUSD')) / 1e18 >= threshold]

            logging.info('Sending tweets')
            self.create_tweets(whales)
        except RequestException as e:
            logging.error(e)

        end = datetime.now()
        logging.info(f'Executed SynthweetixBot in {end - start}s')
