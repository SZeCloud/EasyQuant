"""
okex现货
https://www.okex.com/docs/zh/#spot-README
Author: Gary-Hertel
Date:   2020/10/27
email: easyquant@foxmail.com
"""

import time
from easyquant.exchange.okex import spot_api as okexspot
from easyquant.config import config
from easyquant.exceptions import *
from easyquant.time import utctime_str_to_mts
from easyquant.exchange.util import requests


class OKEXSPOT:

    def __init__(self, access_key, secret_key, passphrase, instrument_id):
        """
        okex现货
        :param access_key:
        :param secret_key:
        :param passphrase:
        :param instrument_id:例如："ETC-USDT"
        """
        self.__access_key = access_key
        self.__secret_key = secret_key
        self.__passphrase = passphrase
        self.__instrument_id = instrument_id
        self.__okex_spot = okexspot.SpotAPI(self.__access_key, self.__secret_key, self.__passphrase)

    def buy(self, price=None, quantity=None, order_type=None, **kwargs):
        order_type = "LIMIT" or order_type
        type = order_type.lower()
        try:
            if order_type == "LIMIT":
                result = self.__okex_spot.take_order(instrument_id=self.__instrument_id,
                                                     side="buy",
                                                     type=type,
                                                     price=price,
                                                     size=quantity)
            else:
                result = self.__okex_spot.take_order(instrument_id=self.__instrument_id,
                                                     side="buy",
                                                     type=type,
                                                     size=quantity,
                                                     notional=kwargs.get('notional'))
        except Exception as e:
            raise SendOrderError(e)
        try:
            order_info = self.get_order_info(order_id=result['order_id'])  # 下单后查询一次订单状态
        except:
            raise SendOrderError(result['error_message'])
        if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
            return order_info
        # 如果订单状态不是"完全成交"或者"失败"
        if config.price_cancellation:  # 选择了价格撤单时，如果最新价超过委托价一定幅度，撤单重发，返回下单结果
            if order_info["订单状态"] == "等待成交":
                if float(self.get_ticker()['last']) >= price * (1 + config.price_cancellation_amplitude):
                    try:
                        self.revoke_order(order_id=result['order_id'])
                        state = self.get_order_info(order_id=result['order_id'])
                        if state['订单状态'] == "撤单成功":
                            return self.buy(float(self.get_ticker()['last']) * (1 + config.reissue_order), quantity - state["已成交数量"])
                    except: # 如撤单失败，则说明已经完全成交，此时再查询一次订单状态然后返回下单结果
                        order_info = self.get_order_info(order_id=result['order_id'])  # 下单后查询一次订单状态
                        if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
                            return order_info
            if order_info["订单状态"] == "部分成交":    # 部分成交时撤单然后重发委托，下单数量为原下单数量减去已成交数量
                if float(self.get_ticker()['last']) >= price * (1 + config.price_cancellation_amplitude):
                    try:
                        self.revoke_order(order_id=result['order_id'])
                        state = self.get_order_info(order_id=result['order_id'])
                        if state['订单状态'] == "撤单成功":
                            return self.buy(float(self.get_ticker()['last']) * (1 + config.reissue_order), quantity - state["已成交数量"])
                    except: # 如撤单失败，则说明已经完全成交，此时再查询一次订单状态然后返回下单结果
                        order_info = self.get_order_info(order_id=result['order_id'])  # 下单后查询一次订单状态
                        if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
                            return order_info
        if config.time_cancellation:  # 选择了时间撤单时，如果委托单发出多少秒后不成交，撤单重发，直至完全成交，返回成交结果
            time.sleep(config.time_cancellation_seconds)
            order_info = self.get_order_info(order_id=result['order_id'])
            if order_info["订单状态"] == "等待成交":
                try:
                    self.revoke_order(order_id=result['order_id'])
                    state = self.get_order_info(order_id=result['order_id'])
                    if state['订单状态'] == "撤单成功":
                        return self.buy(float(self.get_ticker()['last']) * (1 + config.reissue_order), quantity - state["已成交数量"])
                except:  # 如撤单失败，则说明已经完全成交，此时再查询一次订单状态然后返回下单结果
                    order_info = self.get_order_info(order_id=result['order_id'])  # 下单后查询一次订单状态
                    if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
                        return order_info
            if order_info["订单状态"] == "部分成交":    # 部分成交时撤单然后重发委托，下单数量为原下单数量减去已成交数量
                if float(self.get_ticker()['last']) >= price * (1 + config.price_cancellation_amplitude):
                    try:
                        self.revoke_order(order_id=result['order_id'])
                        state = self.get_order_info(order_id=result['order_id'])
                        if state['订单状态'] == "撤单成功":
                            return self.buy(float(self.get_ticker()['last']) * (1 + config.reissue_order), quantity - state["已成交数量"])
                    except: # 如撤单失败，则说明已经完全成交，此时再查询一次订单状态然后返回下单结果
                        order_info = self.get_order_info(order_id=result['order_id'])  # 下单后查询一次订单状态
                        if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
                            return order_info
        if config.automatic_cancellation:
            # 如果订单未完全成交，且未设置价格撤单和时间撤单，且设置了自动撤单，就自动撤单并返回下单结果与撤单结果
            try:
                self.revoke_order(order_id=result['order_id'])
                state = self.get_order_info(order_id=result['order_id'])
                return state
            except:  # 如撤单失败，则说明已经完全成交，此时再查询一次订单状态然后返回下单结果
                order_info = self.get_order_info(order_id=result['order_id'])  # 下单后查询一次订单状态
                if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
                    return order_info
        else:  # 未启用交易助手时，下单并查询订单状态后直接返回下单结果
            return order_info

    def sell(self, price=None, quantity=None, order_type=None, **kwargs):
        order_type = "LIMIT" or order_type
        type = order_type.lower()
        try:
            if order_type == "LIMIT":
                result = self.__okex_spot.take_order(instrument_id=self.__instrument_id,
                                                     side="sell",
                                                     type=type,
                                                     price=price,
                                                     size=quantity)
            else:
                result = self.__okex_spot.take_order(instrument_id=self.__instrument_id,
                                                     side="sell",
                                                     type=type,
                                                     size=quantity,
                                                     notional=kwargs.get('notional'))
        except Exception as e:
            raise SendOrderError(e)
        try:
            order_info = self.get_order_info(order_id=result['order_id'])  # 下单后查询一次订单状态
        except:
            raise SendOrderError(result['error_message'])
        if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
            return order_info
        # 如果订单状态不是"完全成交"或者"失败"
        if config.price_cancellation:  # 选择了价格撤单时，如果最新价超过委托价一定幅度，撤单重发，返回下单结果
            if order_info["订单状态"] == "等待成交":
                if float(self.get_ticker()['last']) <= price * (1 - config.price_cancellation_amplitude):
                    try:
                        self.revoke_order(order_id=result['order_id'])
                        state = self.get_order_info(order_id=result['order_id'])
                        if state['订单状态'] == "撤单成功":
                            return self.sell(float(self.get_ticker()['last']) * (1 - config.reissue_order), quantity - state["已成交数量"])
                    except: # 如撤单失败，则说明已经完全成交，此时再查询一次订单状态然后返回下单结果
                        order_info = self.get_order_info(order_id=result['order_id'])  # 下单后查询一次订单状态
                        if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
                            return order_info
            if order_info["订单状态"] == "部分成交":    # 部分成交时撤单然后重发委托，下单数量为原下单数量减去已成交数量
                if float(self.get_ticker()['last']) <= price * (1 - config.price_cancellation_amplitude):
                    try:
                        self.revoke_order(order_id=result['order_id'])
                        state = self.get_order_info(order_id=result['order_id'])
                        if state['订单状态'] == "撤单成功":
                            return self.sell(float(self.get_ticker()['last']) * (1 - config.reissue_order), quantity - state["已成交数量"])
                    except: # 如撤单失败，则说明已经完全成交，此时再查询一次订单状态然后返回下单结果
                        order_info = self.get_order_info(order_id=result['order_id'])  # 下单后查询一次订单状态
                        if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
                            return order_info
        if config.time_cancellation:  # 选择了时间撤单时，如果委托单发出多少秒后不成交，撤单重发，直至完全成交，返回成交结果
            time.sleep(config.time_cancellation_seconds)
            order_info = self.get_order_info(order_id=result['order_id'])
            if order_info["订单状态"] == "等待成交":
                try:
                    self.revoke_order(order_id=result['order_id'])
                    state = self.get_order_info(order_id=result['order_id'])
                    if state['订单状态'] == "撤单成功":
                        return self.sell(float(self.get_ticker()['last']) * (1 - config.reissue_order), quantity - state["已成交数量"])
                except:  # 如撤单失败，则说明已经完全成交，此时再查询一次订单状态然后返回下单结果
                    order_info = self.get_order_info(order_id=result['order_id'])  # 下单后查询一次订单状态
                    if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
                        return order_info
            if order_info["订单状态"] == "部分成交":    # 部分成交时撤单然后重发委托，下单数量为原下单数量减去已成交数量
                if float(self.get_ticker()['last']) <= price * (1 - config.price_cancellation_amplitude):
                    try:
                        self.revoke_order(order_id=result['order_id'])
                        state = self.get_order_info(order_id=result['order_id'])
                        if state['订单状态'] == "撤单成功":
                            return self.sell(float(self.get_ticker()['last']) * (1 - config.reissue_order), quantity - state["已成交数量"])
                    except: # 如撤单失败，则说明已经完全成交，此时再查询一次订单状态然后返回下单结果
                        order_info = self.get_order_info(order_id=result['order_id'])  # 下单后查询一次订单状态
                        if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
                            return order_info
        if config.automatic_cancellation:
            # 如果订单未完全成交，且未设置价格撤单和时间撤单，且设置了自动撤单，就自动撤单并返回下单结果与撤单结果
            try:
                self.revoke_order(order_id=result['order_id'])
                state = self.get_order_info(order_id=result['order_id'])
                return state
            except:  # 如撤单失败，则说明已经完全成交，此时再查询一次订单状态然后返回下单结果
                order_info = self.get_order_info(order_id=result['order_id'])  # 下单后查询一次订单状态
                if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
                    return order_info
        else:  # 未启用交易助手时，下单并查询订单状态后直接返回下单结果
            return order_info

    def get_order_list(self, state, limit):
        receipt = self.__okex_spot.get_orders_list(self.__instrument_id, state=state, limit=limit)
        return receipt

    def revoke_order(self, order_id):
        receipt = self.__okex_spot.revoke_order(self.__instrument_id, order_id)
        try:
            if receipt['error_code'] == "0":
                return True
        except Exception as e:
            return "撤单失败：{}".format(e)

    def get_order_info(self, order_id):
        result = self.__okex_spot.get_order_info(self.__instrument_id, order_id)
        instrument_id = result['instrument_id']
        action = None
        if result['side'] == 'buy':
            action = "买入开多"
        if result['side'] == 'sell':
            action = "卖出平多"
        if int(result['state']) == 2:
            dict = {"交易所": "Okex现货", "合约ID": instrument_id, "方向": action, "订单状态": "完全成交", "成交均价": float(result['price_avg']),
                    "已成交数量": float(result['filled_size']), "成交金额": float(result['filled_notional']), "order_id": order_id}
            return dict
        elif int(result['state']) == -2:
            dict = {"交易所": "Okex现货", "合约ID": instrument_id, "方向": action, "订单状态": "失败", "order_id": order_id}
            return dict
        elif int(result['state']) == -1:
            dict = {"交易所": "Okex现货", "合约ID": instrument_id, "方向": action, "订单状态": "撤单成功", "成交均价": float(result['price_avg']),
                    "已成交数量": float(result['filled_size']), "成交金额": float(result['filled_notional']), "order_id": order_id}
            return dict
        elif int(result['state']) == 0:
            dict = {"交易所": "Okex现货", "合约ID": instrument_id, "方向": action, "订单状态": "等待成交", "order_id": order_id}
            return dict
        elif int(result['state']) == 1:
            dict = {"交易所": "Okex现货", "合约ID": instrument_id, "方向": action, "订单状态": "部分成交", "成交均价": float(result['price_avg']),
                    "已成交数量": float(result['filled_size']), "成交金额": float(result['filled_notional']), "order_id": order_id}
            return dict
        elif int(result['state']) == 3:
            dict = {"交易所": "Okex现货", "合约ID": instrument_id, "方向": action, "订单状态": "下单中", "order_id": order_id}
            return dict
        elif int(result['state']) == 4:
            dict = {"交易所": "Okex现货", "合约ID": instrument_id, "方向": action, "订单状态": "撤单中", "order_id": order_id}
            return dict

    def get_kline(self, time_frame):
        if time_frame == "1m" or time_frame == "1M":
            granularity = '60'
        elif time_frame == '3m' or time_frame == "3M":
            granularity = '180'
        elif time_frame == '5m' or time_frame == "5M":
            granularity = '300'
        elif time_frame == '15m' or time_frame == "15M":
            granularity = '900'
        elif time_frame == '30m' or time_frame == "30M":
            granularity = '1800'
        elif time_frame == '1h' or time_frame == "1H":
            granularity = '3600'
        elif time_frame == '2h' or time_frame == "2H":
            granularity = '7200'
        elif time_frame == '4h' or time_frame == "4H":
            granularity = '14400'
        elif time_frame == '6h' or time_frame == "6H":
            granularity = '21600'
        elif time_frame == '12h' or time_frame == "12H":
            granularity = '43200'
        elif time_frame == '1d' or time_frame == "1D":
            granularity = '86400'
        else:
            raise KlineError
        receipt = self.__okex_spot.get_kline(self.__instrument_id, granularity=granularity)
        receipt.reverse()
        for i in receipt:
            i[0] = utctime_str_to_mts(i[0])
        return receipt

    def get_position(self):
        """OKEX现货，如交易对为'ETC-USDT', 则获取的是ETC的可用余额"""
        currency = self.__instrument_id.split('-')[0]
        receipt = self.__okex_spot.get_coin_account_info(currency=currency)
        direction = 'long'
        amount = float(receipt['balance'])
        price = None
        result = {'direction': direction, 'amount': amount, 'price': price}
        return result

    def get_ticker(self):
        receipt = self.__okex_spot.get_specific_ticker(instrument_id=self.__instrument_id)
        return receipt

    def get_depth(self, type=None, size=None):
        """
        OKEX现货获取深度数据
        :param type: 如不传参，返回asks和bids；只获取asks传入type="asks"；只获取"bids"传入type="bids"
        :param size: 返回深度档位数量，最多返回200，默认10档
        :return:
        """
        size = size or 10
        response = self.__okex_spot.get_depth(self.__instrument_id, size=size)
        asks_list = response['asks']
        bids_list = response['bids']
        bids = []
        asks = []
        for i in asks_list:
            asks.append(float(i[0]))
        for j in bids_list:
            bids.append(float(j[0]))
        if type == "asks":
            return asks
        elif type == "bids":
            return bids
        else:
            return response

    def get_single_equity(self, currency):
        """
        获取币币账户单个币种的余额、冻结和可用等信息。
        :param currency: 例如"btc"
        :return:返回浮点数
        """
        data = self.__okex_spot.get_coin_account_info(currency=currency)
        result =float(data["balance"])
        return result

    """获取交易所的一些原始信息"""

    def orders(self, order_id):
        result = self.__okex_spot.get_order_info(self.__instrument_id, order_id)
        return result

    def positions(self):
        receipt = self.__okex_spot.get_account_info()
        return receipt

    def tickers(self):
        receipt = self.__okex_spot.get_specific_ticker(instrument_id=self.__instrument_id)
        return receipt

    def orderbooks(self):
        response = self.__okex_spot.get_depth(self.__instrument_id, size=10)
        return response

    def info(self):
        result = requests.get("https://www.okex.com/api/spot/v3/instruments").json()
        return result