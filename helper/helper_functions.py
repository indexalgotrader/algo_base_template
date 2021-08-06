import calendar

import pandas as pd
import pytz
import logging

from alice_blue import *
from datetime import datetime
from helper.elastic_helper import *

logging.basicConfig(level=logging.ERROR)
IST = pytz.timezone('Asia/Kolkata')

__user_name = os.getenv('AB_USER_NAME')
__pass_word = os.getenv('AB_USER_PASS')
__two_fa = os.getenv('AB_TWO_FA')
__api_secret = os.getenv('AB_API_SECRET')
__app_id = os.getenv('AB_APP_ID')

__data_feed_obj = None

__today = datetime.now(IST).date().strftime("%Y%m%d")

__market_start_hour = datetime.now(IST).replace(hour=9, minute=15, second=0, microsecond=0)
__market_end_hour = datetime.now(IST).replace(hour=15, minute=30, second=0, microsecond=0)

__trading_holidays = [
    '2021-01-21', '2021-03-11', '2021-03-29', '2021-04-02', '2021-04-14', '2021-04-21', '2021-05-13',
    '2021-07-21', '2021-08-19', '2021-09-10', '2021-10-15', '2021-11-04', '2021-11-05', '2021-11-19'
]


def __get_access_token():
    if es.exists(index=es_token_index_name, doc_type='_doc', id='data_feed_token'):
        data_feed_row = es.get(index=es_token_index_name, doc_type='_doc', id='data_feed_token')['_source']

        token = data_feed_row['token']
        expiry = data_feed_row['expiry']

        if int(datetime.now(IST).timestamp()) <= int(expiry):
            return token

    token = AliceBlue.login_and_get_access_token(username=__user_name, password=__pass_word, twoFA=__two_fa,
                                                 api_secret=__api_secret, app_id=__app_id)
    expiry = int(datetime.now(IST).replace(hour=23, minute=59, second=59).timestamp())

    es_data_feed_row = {'token': token, 'expiry': expiry, 'created': datetime.now(IST).replace(microsecond=0)}
    es.index(index=es_token_index_name, id='data_feed_token', body=es_data_feed_row)

    print("created new token")
    return token


def get_data_feed_object():
    global __data_feed_obj
    if __data_feed_obj is None:
        access_token = __get_access_token()
        __data_feed_obj = AliceBlue(username=__user_name, password=__pass_word, access_token=access_token,
                                    master_contracts_to_download=['NFO', 'NSE'])

    return __data_feed_obj


def between_market_hours():
    return __market_start_hour < datetime.now(IST) < __market_end_hour


def is_market_open():
    week_day = calendar.day_name[datetime.now(IST).weekday()]

    if week_day == 'Saturday' or week_day == 'Sunday' or str(datetime.now(IST).date()) in __trading_holidays:
        working_day = False
    else:
        working_day = between_market_hours()

    return working_day


def round_ltp(ltp, base=50):
    return base * round(ltp/base)


def round_to_decimals(ltp, base=0.05, decimals=2):
    return float(round(base * round(ltp / base), decimals))


def get_monthly_expiry(data_feed_object, symbol, expiry='current'):
    instruments = pd.DataFrame(data_feed_object.search_instruments('NFO', symbol))
    instruments = instruments.loc[instruments['symbol'].str.contains('FUT', regex=False)]
    instruments = instruments.loc[instruments['symbol'].str.startswith(symbol)]

    if expiry == 'current':
        return min(instruments.expiry)
    elif expiry == 'next':
        return max(instruments[instruments.expiry != max(instruments.expiry)].expiry)
    else:
        return max(instruments.expiry)


def get_weekly_expiry(alice, symbol, expiry='current'):
    instruments = pd.DataFrame(alice.search_instruments('NFO', symbol))
    instruments = instruments.loc[~instruments['symbol'].str.contains('FUT', regex=False)]
    instruments = instruments.loc[instruments['symbol'].str.startswith(symbol)]

    expiry_dates = instruments.sort_values(by='expiry', axis=0).expiry.unique()

    if expiry == 'current':
        return expiry_dates[0]
    elif expiry == 'next':
        return expiry_dates[1]
