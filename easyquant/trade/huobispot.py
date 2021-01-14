"""
火币现货
Author: Gary-Hertel
Date:   2020/10/27
email: easyquant@foxmail.com
"""

import time
from easyquant.time import ts_to_utc_str
from easyquant.exchange.huobi import huobi_spot as huobispot
from easyquant.config import config
from easyquant.exceptions import *
from easyquant.exchange.util import requests


class HUOBISPOT:

    def __init__(self, access_key, secret_key, instrument_id):
        """

        :param access_key:
        :param secret_key:
        :param instrument_id: e.g. 'ETC-USDT'
        """
        self.__access_key = access_key
        self.__secret_key = secret_key
        self.__instrument_id = (instrument_id.split('-')[0] + instrument_id.split('-')[1]).lower()
        self.__huobi_spot = huobispot.HuobiSVC(self.__access_key, self.__secret_key)
        self.__currency = (instrument_id.split('-')[0]).lower()
        self.__account_id = self.__huobi_spot.get_accounts()['data'][0]['id']

    def get_single_equity(self, currency):
        """
        获取单个币种的权益
        :param currency: 例如 "USDT"
        :return:返回浮点数
        """
        data = self.__huobi_spot.get_balance_currency(acct_id=self.__account_id, currency=currency)
        result = float(data[currency])
        return result

    def buy(self, price=None, quantity=None, order_type=None):
        order_type = "LIMIT" or order_type
        if order_type == "LIMIT":
            order_type = 'buy-limit'
        else:
            order_type = 'buy-market'
        result = self.__huobi_spot.send_order(self.__account_id, quantity, 'spot-api', self.__instrument_id, _type=order_type, price=price)
        if result["status"] == "error": # 如果下单失败就抛出异常
            raise SendOrderError(result["err-msg"])
        order_info = self.get_order_info(order_id=result['data'])  # 下单后查询一次订单状态
        if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
            return order_info
        # 如果订单状态不是"完全成交"或者"失败"
        if config.price_cancellation:  # 选择了价格撤单时，如果最新价超过委托价一定幅度，撤单重发，返回下单结果
            if order_info["订单状态"] == "准备提交" or order_info["订单状态"] == "已提交":
                if float(self.get_ticker()['last']) >= price * (1 + config.price_cancellation_amplitude):
                    try:
                        self.revoke_order(order_id=result['data'])
                        state = self.get_order_info(order_id=result['data'])
                        if state['订单状态'] == "撤单成功" or state['订单状态'] == "部分成交撤销":
                            return self.buy(float(self.get_ticker()['last']) * (1 + config.reissue_order), quantity - state["已成交数量"])
                    except:
                        order_info = self.get_order_info(order_id=result['data'])  # 下单后查询一次订单状态
                        if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
                            return order_info
            if order_info["订单状态"] == "部分成交":
                if float(self.get_ticker()['last']) >= price * (1 + config.price_cancellation_amplitude):
                    try:
                        self.revoke_order(order_id=result['data'])
                        state = self.get_order_info(order_id=result['data'])
                        if state['订单状态'] == "部分成交撤销":
                            return self.buy(float(self.get_ticker()['last']) * (1 + config.reissue_order), quantity - state["已成交数量"])
                    except:
                        order_info = self.get_order_info(order_id=result['data'])  # 下单后查询一次订单状态
                        if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
                            return order_info
        if config.time_cancellation:  # 选择了时间撤单时，如果委托单发出多少秒后不成交，撤单重发，直至完全成交，返回成交结果
            time.sleep(config.time_cancellation_seconds)
            order_info = self.get_order_info(order_id=result['data'])
            if order_info["订单状态"] == "准备提交" or order_info["订单状态"] == "已提交":
                try:
                    self.revoke_order(order_id=result['data'])
                    state = self.get_order_info(order_id=result['data'])
                    if state['订单状态'] == "撤单成功" or state['订单状态'] == "部分成交撤销":
                        return self.buy(float(self.get_ticker()['last']) * (1 + config.reissue_order), quantity - state["已成交数量"])
                except:
                    order_info = self.get_order_info(order_id=result['data'])  # 下单后查询一次订单状态
                    if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
                        return order_info
            if order_info["订单状态"] == "部分成交":
                try:
                    self.revoke_order(order_id=result['data'])
                    state = self.get_order_info(order_id=result['data'])
                    if state['订单状态'] == "部分成交撤销":
                        return self.buy(float(self.get_ticker()['last']) * (1 + config.reissue_order), quantity - state["已成交数量"])
                except:
                    order_info = self.get_order_info(order_id=result['data'])  # 下单后查询一次订单状态
                    if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
                        return order_info
        if config.automatic_cancellation:
            # 如果订单未完全成交，且未设置价格撤单和时间撤单，且设置了自动撤单，就自动撤单并返回下单结果与撤单结果
            try:
                self.revoke_order(order_id=result['data'])
                state = self.get_order_info(order_id=result['data'])
                return state
            except:
                order_info = self.get_order_info(order_id=result['data'])  # 下单后查询一次订单状态
                if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
                    return order_info
        else:  # 未启用交易助手时，下单并查询订单状态后直接返回下单结果
            return order_info

    def sell(self, price=None, quantity=None, order_type=None):
        order_type = "LIMIT" or order_type
        if order_type == "LIMIT":
            order_type = 'sell-limit'
        else:
            order_type = 'sell-market'
        result = self.__huobi_spot.send_order(self.__account_id, quantity, 'spot-api', self.__instrument_id,
                                              _type=order_type, price=price)
        if result["status"] == "error":  # 如果下单失败就抛出异常
            raise SendOrderError(result["err-msg"])
        order_info = self.get_order_info(order_id=result['data'])  # 下单后查询一次订单状态
        if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
            return order_info
        # 如果订单状态不是"完全成交"或者"失败"
        if config.price_cancellation:  # 选择了价格撤单时，如果最新价超过委托价一定幅度，撤单重发，返回下单结果
            if order_info["订单状态"] == "准备提交" or order_info["订单状态"] == "已提交":
                if float(self.get_ticker()['last']) <= price * (1 - config.price_cancellation_amplitude):
                    try:
                        self.revoke_order(order_id=result['data'])
                        state = self.get_order_info(order_id=result['data'])
                        if state['订单状态'] == "撤单成功" or state['订单状态'] == "部分成交撤销":
                            return self.sell(float(self.get_ticker()['last']) * (1 - config.reissue_order), quantity - state["已成交数量"])
                    except:
                        order_info = self.get_order_info(order_id=result['data'])  # 下单后查询一次订单状态
                        if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
                            return order_info
            if order_info["订单状态"] == "部分成交":
                if float(self.get_ticker()['last']) <= price * (1 - config.price_cancellation_amplitude):
                    try:
                        self.revoke_order(order_id=result['data'])
                        state = self.get_order_info(order_id=result['data'])
                        if state['订单状态'] == "部分成交撤销":
                            return self.sell(float(self.get_ticker()['last']) * (1 - config.reissue_order), quantity - state["已成交数量"])
                    except:
                        order_info = self.get_order_info(order_id=result['data'])  # 下单后查询一次订单状态
                        if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
                            return order_info
        if config.time_cancellation:  # 选择了时间撤单时，如果委托单发出多少秒后不成交，撤单重发，直至完全成交，返回成交结果
            time.sleep(config.time_cancellation_seconds)
            order_info = self.get_order_info(order_id=result['data'])
            if order_info["订单状态"] == "准备提交" or order_info["订单状态"] == "已提交":
                try:
                    self.revoke_order(order_id=result['data'])
                    state = self.get_order_info(order_id=result['data'])
                    if state['订单状态'] == "撤单成功" or state['订单状态'] == "部分成交撤销":
                        return self.sell(float(self.get_ticker()['last']) * (1 - config.reissue_order), quantity - state["已成交数量"])
                except:
                    order_info = self.get_order_info(order_id=result['data'])  # 下单后查询一次订单状态
                    if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
                        return order_info
            if order_info["订单状态"] == "部分成交":
                try:
                    self.revoke_order(order_id=result['data'])
                    state = self.get_order_info(order_id=result['data'])
                    if state['订单状态'] == "部分成交撤销":
                        return self.sell(float(self.get_ticker()['last']) * (1 - config.reissue_order), quantity - state["已成交数量"])
                except:
                    order_info = self.get_order_info(order_id=result['data'])  # 下单后查询一次订单状态
                    if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
                        return order_info
        if config.automatic_cancellation:
            # 如果订单未完全成交，且未设置价格撤单和时间撤单，且设置了自动撤单，就自动撤单并返回下单结果与撤单结果
            try:
                self.revoke_order(order_id=result['data'])
                state = self.get_order_info(order_id=result['data'])
                return state
            except:
                order_info = self.get_order_info(order_id=result['data'])  # 下单后查询一次订单状态
                if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
                    return order_info
        else:  # 未启用交易助手时，下单并查询订单状态后直接返回下单结果
            return order_info

    def get_order_info(self, order_id):
        result = self.__huobi_spot.order_info(order_id)
        instrument_id = self.__instrument_id
        action = None
        try:
            if "buy" in result['data']['type']:
                action = "买入开多"
            elif "sell" in result['data']['type']:
                action = "卖出平多"
        except Exception as e:
            raise GetOrderError(e)

        if result["data"]['state'] == 'filled':
            dict = {"交易所": "Huobi现货", "合约ID": instrument_id, "方向": action, "订单状态": "完全成交",
                    "成交均价": float(result['data']['price']),
                    "已成交数量": float(result["data"]["field-amount"]),
                    "成交金额": float(result['data']["field-cash-amount"]),
                    "order_id": order_id}
            return dict
        elif result["data"]['state'] == 'canceled':
            dict = {"交易所": "Huobi现货", "合约ID": instrument_id, "方向": action, "订单状态": "撤单成功",
                    "成交均价": float(result['data']['price']),
                    "已成交数量": float(result["data"]["field-amount"]),
                    "成交金额": float(result['data']["field-cash-amount"]),
                    "order_id": order_id}
            return dict
        elif result["data"]['state'] == 'partial-filled':
            dict = {"交易所": "Huobi现货", "合约ID": instrument_id, "方向": action, "订单状态": "部分成交",
                    "成交均价": float(result['data']['price']),
                    "已成交数量": float(result["data"]["field-amount"]),
                    "成交金额": float(result['data']["field-cash-amount"]),
                    "order_id": order_id}
            return dict
        elif result["data"]['state'] == 'partial-canceled':
            dict = {"交易所": "Huobi现货", "合约ID": instrument_id, "方向": action, "订单状态": "部分成交撤销",
                    "成交均价": float(result['data']['price']),
                    "已成交数量": float(result["data"]["field-amount"]),
                    "成交金额": float(result['data']["field-cash-amount"]),
                    "order_id": order_id}
            return dict
        elif result["data"]['state'] == 'submitted':
            dict = {"交易所": "Huobi现货", "合约ID": instrument_id, "方向": action, "订单状态": "已提交", "order_id": order_id}
            return dict

    def revoke_order(self, order_id):
        receipt = self.__huobi_spot.cancel_order(order_id)
        try:
            if receipt['status'] == "ok":
                return True
        except Exception as e:
            return "撤单失败：{}".format(e)

    def get_kline(self, time_frame):
        if time_frame == '1m' or time_frame == '1M':
            period = '1min'
        elif time_frame == '5m' or time_frame == '5M':
            period = '5min'
        elif time_frame == '15m' or time_frame == '15M':
            period = '15min'
        elif time_frame == '30m' or time_frame == '30M':
            period = '30min'
        elif time_frame == '1h' or time_frame == '1H':
            period = '60min'
        elif time_frame == '4h' or time_frame == '4H':
            period = '4hour'
        elif time_frame == '1d' or time_frame == '1D':
            period = '1day'
        else:
            raise KlineError("交易所: Huobi k线周期错误，k线周期只能是【1m, 5m, 15m, 30m, 1h, 4h, 1d】!")
        records = self.__huobi_spot.get_kline(self.__instrument_id, period=period)['data']
        list = []
        for item in records:
            item = [1000 * int(item['id']), item['open'], item['high'], item['low'], item['close'], item['vol'],
                    round(item['amount'], 2)]
            list.append(item)
        list.reverse()
        return list

    def get_position(self):
        """获取当前交易对的计价货币的可用余额，如当前交易对为etc-usdt, 则获取的是etc的可用余额"""
        receipt = self.__huobi_spot.get_balance_currency(self.__account_id, self.__currency)
        direction = 'long'
        amount = receipt[self.__currency]
        price = None
        result = {'direction': direction, 'amount': amount, 'price': price}
        return result

    def get_ticker(self):
        receipt = self.__huobi_spot.get_ticker(self.__instrument_id)
        last = receipt['tick']['close']
        return {"last": last}

    def get_depth(self, type=None, size=None):
        """
        火币现货获取深度数据
        :param type: 如不传参，返回asks和bids；只获取asks传入type="asks"；只获取"bids"传入type="bids"
        :param size: 返回深度档位数量，取值范围：5，10，20，默认10档
        :return:
        """
        size = size or 10
        response = self.__huobi_spot.get_depth(self.__instrument_id, depth=size, type="step0")
        asks_list = response["tick"]["asks"]
        bids_list = response["tick"]["bids"]
        asks = []
        bids = []
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

    """获取交易所的一些原始信息"""

    def orders(self, order_id):
        result = self.__huobi_spot.order_info(order_id)
        return result

    def positions(self):
        receipt = self.__huobi_spot.get_balance_currency(self.__account_id)
        return receipt

    def tickers(self):
        receipt = self.__huobi_spot.get_ticker(self.__instrument_id)
        return receipt

    def orderbooks(self):
        response = self.__huobi_spot.get_depth(self.__instrument_id, depth=10, type="step0")
        return response

    def info(self):
        result = requests.get("https://api.huobi.pro/v1/common/symbols").json()
        return result