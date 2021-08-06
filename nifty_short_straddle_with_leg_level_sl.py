import time

from helper.helper_functions import *
from helper.elastic_helper import *

__time_format = '%H:%M:%S'
__date_key = datetime.now(IST).date().__str__().replace("-", "_").split('+')[0]

__data_feed_socket_opened_1 = False
__data_feed_socket_opened_2 = False

__strategy_config = {
    'instrument_name': 'Nifty 50',
    'symbol_key': 'NIFTY',
    'symbol_spot_key': 'Nifty 50',
    'strategy_name': 'Nifty Short Straddle - Leg Level Stop Loss',
    'strategy_code': '101',
    'entry_time': '09:20:00',
    'exit_time': '15:00:00',
    'ce_stop_loss': 1.25,
    'pe_stop_loss': 1.25,
    'max_pnl_stop_loss': 3000
}

__data_feed_obj = get_data_feed_object()
__index_data = {}
__main_index_key = __strategy_config['strategy_code'] + '_' + __date_key


def __data_callback_1():
    global __data_feed_socket_opened_1
    __data_feed_socket_opened_1 = True


def __data_callback_2():
    global __data_feed_socket_opened_2
    __data_feed_socket_opened_2 = True


def __data_handler(data_feed):
    # print(f"quote update - {datetime.now(IST).time()} - {data_feed}")

    if 'entry_underlying_price' not in __index_data:
        __index_data['entry_underlying_price'] = float(data_feed['ltp'])
        __index_data['entry_time_stamp'] = data_feed['exchange_time_stamp']
        __index_data['entry_date'] = str(datetime.fromtimestamp(data_feed['exchange_time_stamp'], tz=IST).date())
        __index_data['entry_time'] = str(datetime.fromtimestamp(data_feed['exchange_time_stamp'], tz=IST).time())
        __index_data['atm_strike'] = round_ltp(data_feed['ltp'], base=100)
        __index_data['legs'] = []


def __update_status(data_feed, exit_reason):
    for leg_details in __index_data['legs']:
        if leg_details['position_open'] and data_feed['token'] == leg_details['strike_token']:
            leg_details['pnl_points'] = round_to_decimals(leg_details['entry_price'] - float(data_feed['ltp']))
            leg_details['pnl'] = round_to_decimals((leg_details['entry_price'] - float(data_feed['ltp'])) * float(leg_details['lot_size']))
            leg_details['position_open'] = False
            leg_details['exit_price'] = float(data_feed['ltp'])
            leg_details['exit_timestamp'] = data_feed['exchange_time_stamp']
            leg_details['exit_reason'] = exit_reason


def __manage_positions(data_feed, leg_details):
    if 'entry_price' not in leg_details:
        __index_data['trade_active'] = True

        leg_details['entry_price'] = float(data_feed['ltp'])
        leg_details['entry_timestamp'] = data_feed['exchange_time_stamp']
        leg_details['position_open'] = True

        if leg_details['option_type'] == 'CE':
            leg_details['position_stop_loss'] = round_to_decimals(float(data_feed['ltp']) * float(__strategy_config['ce_stop_loss']))
        elif leg_details['option_type'] == 'PE':
            leg_details['position_stop_loss'] = round_to_decimals(float(data_feed['ltp']) * float(__strategy_config['pe_stop_loss']))

    elif leg_details['position_open']:
        leg_details['ltp'] = float(data_feed['ltp'])
        leg_details['pnl_points'] = round_to_decimals(leg_details['entry_price'] - float(data_feed['ltp']))
        leg_details['pnl'] = round_to_decimals((leg_details['entry_price'] - float(data_feed['ltp'])) * float(leg_details['lot_size']))

        if float(data_feed['ltp']) > leg_details['position_stop_loss']:
            leg_details['position_open'] = False
            leg_details['exit_price'] = float(data_feed['ltp'])
            leg_details['exit_timestamp'] = data_feed['exchange_time_stamp']
            leg_details['exit_reason'] = 'Stop Loss Hit'


def __data_handler_2(data_feed):
    print(f"quote update 2 - {datetime.now(IST).time()} - {data_feed}")

    try:
        total_pnl = 0
        ce_pnl = 0
        pe_pnl = 0
        ce_open = True
        pe_open = True

        for leg_details in __index_data['legs']:
            if data_feed['token'] == leg_details['strike_token']:
                __manage_positions(data_feed, leg_details)

            if leg_details['option_type'] == 'CE':
                ce_pnl = leg_details['pnl']
                ce_open = leg_details['position_open']
            elif leg_details['option_type'] == 'PE':
                pe_pnl = leg_details['pnl']
                pe_open = leg_details['position_open']

            total_pnl = total_pnl + leg_details['pnl']

        __index_data['total_pnl'] = total_pnl
        __index_data['timestamp'] = data_feed['exchange_time_stamp']

        if __strategy_config['max_pnl_stop_loss'] < __index_data['total_pnl']:
            __update_status(data_feed, 'Max Loss Hit')

        if datetime.now(IST).time() > datetime.strptime(__strategy_config['exit_time'], '%H:%M:%S').time():
            __update_status(data_feed, 'Exit Time Triggered')

        trade_active = None
        for leg_details in __index_data['legs']:
            if trade_active is None:
                trade_active = leg_details['position_open']
            else:
                trade_active = trade_active or leg_details['position_open']

        __index_data['trade_active'] = trade_active

        current_time = str(datetime.fromtimestamp(data_feed['exchange_time_stamp'], tz=IST).replace(microsecond=0).time())
        print(f'Time = {current_time}, CE PNL = {ce_pnl}, PE PNL = {pe_pnl}, Total PNL = {total_pnl}, CE Position Open = {ce_open}, PE Position Open = {pe_open}')

        es.index(index=es_trade_details_index_name, id=__main_index_key, body=__index_data)
    except Exception as e:
        print(e)


def __get_option_strikes():
    index_spot_instrument = __data_feed_obj.get_instrument_by_symbol(exchange='NSE', symbol=__strategy_config['symbol_spot_key'])
    # print(f'index_spot_instrument = {index_spot_instrument}')

    __data_feed_obj.start_websocket(subscribe_callback=__data_handler, socket_open_callback=__data_callback_1, run_in_background=True)

    while not __data_feed_socket_opened_1:
        pass

    __data_feed_obj.subscribe(index_spot_instrument, LiveFeedType.COMPACT)

    time.sleep(3)

    # print('unsubscribe')
    __data_feed_obj.unsubscribe(index_spot_instrument, LiveFeedType.COMPACT)


def __start_options_data_feed():
    weekly_expiry = datetime.strptime(__index_data['weekly_expiry'], '%Y-%m-%d').date()

    call_strike = __data_feed_obj.get_instrument_for_fno(symbol=__strategy_config['symbol_key'], expiry_date=weekly_expiry, is_fut=False, strike=__index_data['atm_strike'], is_CE=True)
    put_strike = __data_feed_obj.get_instrument_for_fno(symbol=__strategy_config['symbol_key'], expiry_date=weekly_expiry, is_fut=False, strike=__index_data['atm_strike'], is_CE=False)

    # print(f'call_strike = {call_strike}')
    # print(f'put_strike = {put_strike}')

    if len(__index_data['legs']) == 0:
        __index_data['legs'] = [{
            'counter': 1,
            'symbol': call_strike.symbol,
            'lot_size': call_strike.lot_size,
            'option_type': 'CE',
            'strike_token': call_strike.token,
            'pnl': 0.0
        }, {
            'counter': 2,
            'symbol': put_strike.symbol,
            'lot_size': put_strike.lot_size,
            'option_type': 'PE',
            'strike_token': put_strike.token,
            'pnl': 0.0
        }]

    print(__index_data)

    __data_feed_obj.start_websocket(subscribe_callback=__data_handler_2, socket_open_callback=__data_callback_2, run_in_background=True)

    while not __data_feed_socket_opened_2:
        pass

    __data_feed_obj.subscribe(call_strike, LiveFeedType.COMPACT)
    __data_feed_obj.subscribe(put_strike, LiveFeedType.COMPACT)

    exit_time = datetime.now(IST).replace(hour=15, minute=5, second=0, microsecond=0)
    timestamp = exit_time.timestamp() - datetime.now(IST).timestamp()

    # TODO: terminate web socket once the positions get exited

    time.sleep(timestamp)

    print('unsubscribe ' + str(datetime.now(IST).time()))
    __data_feed_obj.unsubscribe(call_strike, LiveFeedType.COMPACT)
    __data_feed_obj.unsubscribe(put_strike, LiveFeedType.COMPACT)


# noinspection PyBroadException
def __get_strategy_counter():
    counter = 0
    result = None

    try:
        result = es.search(index=es_trade_details_index_name, body={"query": {"match": {"strategy_code": __strategy_config['strategy_code']}}}, sort=['counter:desc'], size=1)['hits']['hits']
    except:
        pass

    if result is not None and len(result) == 1:
        counter = result[0]['_source']['counter']

    return counter + 1


def __run_job():
    global __index_data

    weekly_expiry = get_weekly_expiry(__data_feed_obj, symbol=__strategy_config['symbol_key'], expiry='current')

    if es.exists(index=es_trade_details_index_name, id=__main_index_key):
        __index_data = es.get(index=es_trade_details_index_name, id=__main_index_key)['_source']
    else:
        counter = __get_strategy_counter()

        __index_data['instrument'] = __strategy_config['instrument_name']
        __index_data['strategy_name'] = __strategy_config['strategy_name']
        __index_data['strategy_code'] = __strategy_config['strategy_code']
        __index_data['weekly_expiry'] = str(weekly_expiry)
        __index_data['counter'] = counter
        # print(__index_data)

        # TODO: handle entry time and wait conditions

        __get_option_strikes()
        # print(__index_data)

        es.index(index=es_trade_details_index_name, id=__main_index_key, body=__index_data)

    __start_options_data_feed()
    print(__index_data)

    es.indices.forcemerge(index='_all', only_expunge_deletes=True)


if __name__ == '__main__':
    if is_market_open():
        __run_job()
