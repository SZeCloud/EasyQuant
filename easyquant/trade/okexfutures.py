"""
okex交割合约
https://www.okex.com/docs/zh/#futures-README
Author: Gary-Hertel
Date:   2020/10/27
email: easyquant@foxmail.com
"""

import time
from easyquant.exchange.okex import futures_api as okexfutures
from easyquant.config import config
from easyquant.exceptions import *
from easyquant.logger import logger
from easyquant.time import utctime_str_to_mts
from easyquant.exchange.util import requests


class OKEXFUTURES:

    def __init__(self, access_key, secret_key, passphrase, instrument_id, margin_mode=None, leverage=None):
        """
        okex交割合约，初始化时会自动设置成全仓模式，可以传入参数设定开仓杠杆倍数。
        设置合约币种账户模式时，注意：当前有仓位或者有挂单时禁止切换账户模式。
        :param access_key:
        :param secret_key:
        :param passphrase:
        :param instrument_id: 例如："BTC-USD-201225", "BTC-USDT-201225"
        :param leverage:杠杆倍数，如不填则默认设置为20倍杠杆
        """
        self.__access_key = access_key
        self.__secret_key = secret_key
        self.__passphrase = passphrase
        self.__instrument_id = instrument_id
        self.__okex_futures = okexfutures.FutureAPI(self.__access_key, self.__secret_key, self.__passphrase)
        self.__leverage = leverage or 20
        if margin_mode == "fixed":
            try:
                self.__okex_futures.set_margin_mode(underlying=self.__instrument_id.split("-")[0] + "-" + self.__instrument_id.split("-")[1],
                                                    margin_mode="fixed")    # 设置账户模式为逐仓模式
                self.__okex_futures.set_leverage(leverage=self.__leverage,
                                                 underlying=self.__instrument_id.split("-")[0] + "-" +
                                                            self.__instrument_id.split("-")[1],
                                                 instrument_id=self.__instrument_id,
                                                 direction="long")  # 设置做多方向杠杆倍数
                self.__okex_futures.set_leverage(leverage=self.__leverage,
                                                 underlying=self.__instrument_id.split("-")[0] + "-" +
                                                            self.__instrument_id.split("-")[1],
                                                 instrument_id=self.__instrument_id,
                                                 direction="short")  # 设置做空方向杠杆倍数
            except Exception as e:
                logger.error("OKEX交割合约设置逐仓模式失败！错误：{}".format(str(e)))
        else:
            try:
                self.__okex_futures.set_margin_mode(underlying=self.__instrument_id.split("-")[0] + "-" + self.__instrument_id.split("-")[1],
                                                    margin_mode="crossed")
                self.__okex_futures.set_leverage(leverage=self.__leverage,
                                                 underlying=self.__instrument_id.split("-")[0] + "-" +
                                                            self.__instrument_id.split("-")[1])  # 设置账户模式为全仓模式后再设置杠杆倍数
            except Exception as e:
                logger.error("OKEX交割合约设置全仓模式失败！错误：{}".format(str(e)))


    def get_single_equity(self, currency):
        """
        获取单个合约账户的权益
        :param currency: 例如"usdt"
        :return:返回浮点数
        """
        currency = self.__instrument_id.split("-")[0] + "-" + self.__instrument_id.split("-")[1]
        data = self.__okex_futures.get_coin_account(underlying=currency)
        result =float(data["equity"])
        return result

    def buy(self, price=None, quantity=None, order_type=None):
        order_type = 0 if order_type is None else 4
        try:
            if order_type == 0:
                result = self.__okex_futures.take_order(instrument_id=self.__instrument_id,
                                                        type=1,
                                                        order_type=order_type,
                                                        price=price,
                                                        size=quantity)
            else:
                result = self.__okex_futures.take_order(instrument_id=self.__instrument_id,
                                                        type=1,
                                                        order_type=order_type,
                                                        price=None,
                                                        size=quantity)
        except Exception as e:
            raise SendOrderError(e)
        order_info = self.get_order_info(order_id=result['order_id'])   # 下单后查询一次订单状态
        if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ": # 如果订单状态为"完全成交"或者"失败"，返回结果
            return order_info
        # 如果订单状态不是"完全成交"或者"失败"
        if config.price_cancellation: # 选择了价格撤单时，如果最新价超过委托价一定幅度，撤单重发，返回下单结果
            if order_info["订单状态"] == "等待成交":
                if float(self.get_ticker()['last']) >= price * (1 + config.price_cancellation_amplitude):
                    try:    # 如果撤单失败，则订单可能在此期间已完全成交或部分成交
                        self.revoke_order(order_id=result['order_id'])
                        state = self.get_order_info(order_id=result['order_id'])
                        if state['订单状态'] == "撤单成功": # 已完全成交时，以原下单数量重发；部分成交时，重发委托数量为原下单数量减去已成交数量
                            return self.buy(float(self.get_ticker()['last']) * (1 + config.reissue_order), quantity - state["已成交数量"])
                    except:     # 撤单失败时，说明订单已完全成交
                        order_info = self.get_order_info(order_id=result['order_id'])   # 再查询一次订单状态
                        if order_info["订单状态"] == "完全成交":
                            return order_info
            if order_info["订单状态"] == "部分成交":
                if float(self.get_ticker()['last']) >= price * (1 + config.price_cancellation_amplitude):
                    try:
                        self.revoke_order(order_id=result['order_id'])
                        state = self.get_order_info(order_id=result['order_id'])
                        if state['订单状态'] == "撤单成功":
                            return self.buy(float(self.get_ticker()['last']) * (1 + config.reissue_order), quantity - state["已成交数量"])
                    except:     # 撤单失败时，说明订单已完全成交，再查询一次订单状态，如果已完全成交，返回下单结果
                        order_info = self.get_order_info(order_id=result['order_id'])  # 再查询一次订单状态
                        if order_info["订单状态"] == "完全成交":
                            return order_info
        if config.time_cancellation: # 选择了时间撤单时，如果委托单发出多少秒后不成交，撤单重发，直至完全成交，返回成交结果
            time.sleep(config.time_cancellation_seconds)
            order_info = self.get_order_info(order_id=result['order_id'])
            if order_info["订单状态"] == "等待成交":
                try:
                    self.revoke_order(order_id=result['order_id'])
                    state = self.get_order_info(order_id=result['order_id'])
                    if state['订单状态'] == "撤单成功":
                        return self.buy(float(self.get_ticker()['last']) * (1 + config.reissue_order), quantity - state["已成交数量"])
                except:
                    order_info = self.get_order_info(order_id=result['order_id'])  # 再查询一次订单状态
                    if order_info["订单状态"] == "完全成交":
                        return order_info
            if order_info["订单状态"] == "部分成交":
                try:
                    self.revoke_order(order_id=result['order_id'])
                    state = self.get_order_info(order_id=result['order_id'])
                    if state['订单状态'] == "撤单成功":
                        return self.buy(float(self.get_ticker()['last']) * (1 + config.reissue_order), quantity - state["已成交数量"])
                except:
                    order_info = self.get_order_info(order_id=result['order_id'])  # 再查询一次订单状态
                    if order_info["订单状态"] == "完全成交":
                        return order_info
        if config.automatic_cancellation:
            # 如果订单未完全成交，且未设置价格撤单和时间撤单，且设置了自动撤单，就自动撤单并返回下单结果与撤单结果
            try:
                self.revoke_order(order_id=result['order_id'])
                state = self.get_order_info(order_id=result['order_id'])
                return state
            except:
                order_info = self.get_order_info(order_id=result['order_id'])  # 再查询一次订单状态
                if order_info["订单状态"] == "完全成交":
                    return order_info
        else:   # 未启用交易助手时，下单并查询订单状态后直接返回下单结果
            return order_info

    def sell(self, price=None, quantity=None, order_type=None):
        order_type = 0 if order_type is None else 4
        try:
            if order_type == 0:
                result = self.__okex_futures.take_order(instrument_id=self.__instrument_id,
                                                        type=3,
                                                        order_type=order_type,
                                                        price=price,
                                                        size=quantity)
            else:
                result = self.__okex_futures.take_order(instrument_id=self.__instrument_id,
                                                        type=3,
                                                        order_type=order_type,
                                                        price=None,
                                                        size=quantity)
        except Exception as e:
            raise SendOrderError(e)
        order_info = self.get_order_info(order_id=result['order_id'])  # 下单后查询一次订单状态
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
                    except:
                        order_info = self.get_order_info(order_id=result['order_id'])  # 再查询一次订单状态
                        if order_info["订单状态"] == "完全成交":
                            return order_info
            if order_info["订单状态"] == "部分成交":
                if float(self.get_ticker()['last']) <= price * (1 - config.price_cancellation_amplitude):
                    try:
                        self.revoke_order(order_id=result['order_id'])
                        state = self.get_order_info(order_id=result['order_id'])
                        if state['订单状态'] == "撤单成功":
                            return self.sell(float(self.get_ticker()['last']) * (1 - config.reissue_order), quantity - state["已成交数量"])
                    except:
                        order_info = self.get_order_info(order_id=result['order_id'])  # 再查询一次订单状态
                        if order_info["订单状态"] == "完全成交":
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
                except:
                    order_info = self.get_order_info(order_id=result['order_id'])  # 再查询一次订单状态
                    if order_info["订单状态"] == "完全成交":
                        return order_info
            if order_info["订单状态"] == "部分成交":
                try:
                    self.revoke_order(order_id=result['order_id'])
                    state = self.get_order_info(order_id=result['order_id'])
                    if state['订单状态'] == "撤单成功":
                        return self.sell(float(self.get_ticker()['last']) * (1 - config.reissue_order), quantity - state["已成交数量"])
                except:
                    order_info = self.get_order_info(order_id=result['order_id'])  # 再查询一次订单状态
                    if order_info["订单状态"] == "完全成交":
                        return order_info
        if config.automatic_cancellation:
            # 如果订单未完全成交，且未设置价格撤单和时间撤单，且设置了自动撤单，就自动撤单并返回下单结果与撤单结果
            try:
                self.revoke_order(order_id=result['order_id'])
                state = self.get_order_info(order_id=result['order_id'])
                return state
            except:
                order_info = self.get_order_info(order_id=result['order_id'])  # 再查询一次订单状态
                if order_info["订单状态"] == "完全成交":
                    return order_info
        else:  # 未启用交易助手时，下单并查询订单状态后直接返回下单结果
            return order_info

    def sellshort(self, price=None, quantity=None, order_type=None):
        order_type = 0 if order_type is None else 4
        try:
            if order_type == 0:
                result = self.__okex_futures.take_order(instrument_id=self.__instrument_id,
                                                        type=2,
                                                        order_type=order_type,
                                                        price=price,
                                                        size=quantity)
            else:
                result = self.__okex_futures.take_order(instrument_id=self.__instrument_id,
                                                        type=2,
                                                        order_type=order_type,
                                                        price=None,
                                                        size=quantity)
        except Exception as e:
            raise SendOrderError(e)
        order_info = self.get_order_info(order_id=result['order_id'])  # 下单后查询一次订单状态
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
                            return self.sellshort(float(self.get_ticker()['last']) * (1 - config.reissue_order), quantity - state["已成交数量"])
                    except:
                        order_info = self.get_order_info(order_id=result['order_id'])  # 再查询一次订单状态
                        if order_info["订单状态"] == "完全成交":
                            return order_info
            if order_info["订单状态"] == "部分成交":
                if float(self.get_ticker()['last']) <= price * (1 - config.price_cancellation_amplitude):
                    try:
                        self.revoke_order(order_id=result['order_id'])
                        state = self.get_order_info(order_id=result['order_id'])
                        if state['订单状态'] == "撤单成功":
                            return self.sellshort(float(self.get_ticker()['last']) * (1 - config.reissue_order), quantity - state["已成交数量"])
                    except:
                        order_info = self.get_order_info(order_id=result['order_id'])  # 再查询一次订单状态
                        if order_info["订单状态"] == "完全成交":
                            return order_info
        if config.time_cancellation:  # 选择了时间撤单时，如果委托单发出多少秒后不成交，撤单重发，直至完全成交，返回成交结果
            time.sleep(config.time_cancellation_seconds)
            order_info = self.get_order_info(order_id=result['order_id'])
            if order_info["订单状态"] == "等待成交":
                try:
                    self.revoke_order(order_id=result['order_id'])
                    state = self.get_order_info(order_id=result['order_id'])
                    if state['订单状态'] == "撤单成功":
                        return self.sellshort(float(self.get_ticker()['last']) * (1 - config.reissue_order), quantity - state["已成交数量"])
                except:
                    order_info = self.get_order_info(order_id=result['order_id'])  # 再查询一次订单状态
                    if order_info["订单状态"] == "完全成交":
                        return order_info
            if order_info["订单状态"] == "部分成交":
                try:
                    self.revoke_order(order_id=result['order_id'])
                    state = self.get_order_info(order_id=result['order_id'])
                    if state['订单状态'] == "撤单成功":
                        return self.sellshort(float(self.get_ticker()['last']) * (1 - config.reissue_order), quantity - state["已成交数量"])
                except:
                    order_info = self.get_order_info(order_id=result['order_id'])  # 再查询一次订单状态
                    if order_info["订单状态"] == "完全成交":
                        return order_info
        if config.automatic_cancellation:
            # 如果订单未完全成交，且未设置价格撤单和时间撤单，且设置了自动撤单，就自动撤单并返回下单结果与撤单结果
            try:
                self.revoke_order(order_id=result['order_id'])
                state = self.get_order_info(order_id=result['order_id'])
                return state
            except:
                order_info = self.get_order_info(order_id=result['order_id'])  # 再查询一次订单状态
                if order_info["订单状态"] == "完全成交":
                    return order_info
        else:  # 未启用交易助手时，下单并查询订单状态后直接返回下单结果
            return order_info

    def buytocover(self, price=None, quantity=None, order_type=None):
        order_type = 0 if order_type is None else 4
        try:
            if order_type == 0:
                result = self.__okex_futures.take_order(instrument_id=self.__instrument_id,
                                                        type=4,
                                                        order_type=order_type,
                                                        price=price,
                                                        size=quantity)
            else:
                result = self.__okex_futures.take_order(instrument_id=self.__instrument_id,
                                                        type=4,
                                                        order_type=order_type,
                                                        price=None,
                                                        size=quantity)
        except Exception as e:
            raise SendOrderError(e)
        order_info = self.get_order_info(order_id=result['order_id'])  # 下单后查询一次订单状态
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
                            return self.buytocover(float(self.get_ticker()['last']) * (1 + config.reissue_order), quantity - state["已成交数量"])
                    except:
                        order_info = self.get_order_info(order_id=result['order_id'])  # 再查询一次订单状态
                        if order_info["订单状态"] == "完全成交":
                            return order_info
            if order_info["订单状态"] == "部分成交":
                if float(self.get_ticker()['last']) >= price * (1 + config.price_cancellation_amplitude):
                    try:
                        self.revoke_order(order_id=result['order_id'])
                        state = self.get_order_info(order_id=result['order_id'])
                        if state['订单状态'] == "撤单成功":
                            return self.buytocover(float(self.get_ticker()['last']) * (1 + config.reissue_order), quantity - state["已成交数量"])
                    except:
                        order_info = self.get_order_info(order_id=result['order_id'])  # 再查询一次订单状态
                        if order_info["订单状态"] == "完全成交":
                            return order_info
        if config.time_cancellation:  # 选择了时间撤单时，如果委托单发出多少秒后不成交，撤单重发，直至完全成交，返回成交结果
            time.sleep(config.time_cancellation_seconds)
            order_info = self.get_order_info(order_id=result['order_id'])
            if order_info["订单状态"] == "等待成交":
                try:
                    self.revoke_order(order_id=result['order_id'])
                    state = self.get_order_info(order_id=result['order_id'])
                    if state['订单状态'] == "撤单成功":
                        return self.buytocover(float(self.get_ticker()['last']) * (1 + config.reissue_order), quantity - state["已成交数量"])
                except:
                    order_info = self.get_order_info(order_id=result['order_id'])  # 再查询一次订单状态
                    if order_info["订单状态"] == "完全成交":
                        return order_info
            if order_info["订单状态"] == "部分成交":
                try:
                    self.revoke_order(order_id=result['order_id'])
                    state = self.get_order_info(order_id=result['order_id'])
                    if state['订单状态'] == "撤单成功":
                        return self.buytocover(float(self.get_ticker()['last']) * (1 + config.reissue_order), quantity - state["已成交数量"])
                except:
                    order_info = self.get_order_info(order_id=result['order_id'])  # 再查询一次订单状态
                    if order_info["订单状态"] == "完全成交":
                        return order_info
        if config.automatic_cancellation:
            # 如果订单未完全成交，且未设置价格撤单和时间撤单，且设置了自动撤单，就自动撤单并返回下单结果与撤单结果
            try:
                self.revoke_order(order_id=result['order_id'])
                state = self.get_order_info(order_id=result['order_id'])
                return state
            except:
                order_info = self.get_order_info(order_id=result['order_id'])  # 再查询一次订单状态
                if order_info["订单状态"] == "完全成交":
                    return order_info
        else:  # 未启用交易助手时，下单并查询订单状态后直接返回下单结果
            return order_info

    def get_order_list(self, state, limit):
        receipt = self.__okex_futures.get_order_list(self.__instrument_id, state=state, limit=limit)
        return receipt

    def revoke_order(self, order_id):
        receipt = self.__okex_futures.revoke_order(self.__instrument_id, order_id)
        try:
            if receipt['error_code'] == "0":
                return True
        except Exception as e:
            return "撤单失败：{}".format(e)

    def get_order_info(self, order_id):
        result = self.__okex_futures.get_order_info(self.__instrument_id, order_id)
        instrument_id = result['instrument_id']
        action = None
        if result['type'] == '1':
            action = "买入开多"
        elif result['type'] == '2':
            action = "卖出开空"
        if result['type'] == '3':
            action = "卖出平多"
        if result['type'] == '4':
            action = "买入平空"
        # 根据返回的数据中的合约id来判断是u本位合约还是币本位合约，计算成交金额两种方式有区别
        price = float(result['price_avg'])   # 成交均价
        amount = int(result['filled_qty'])   # 已成交数量
        if instrument_id.split("-")[1] == "usd" or instrument_id.split("-")[1] == "USD":
            turnover = float(result['contract_val']) * int(result['filled_qty'])
        elif instrument_id.split("-")[1] == "usdt" or instrument_id.split("-")[1] == "USDT":
            turnover = round(float(result['contract_val']) * int(result['filled_qty']) * float(result['price_avg']), 2)
        else:
            turnover = None

        if int(result['state']) == 2:
            dict = {"交易所": "Okex交割合约", "合约ID": instrument_id, "方向": action, "订单状态": "完全成交", "成交均价": price,
                    "已成交数量": amount, "成交金额": turnover, "order_id": order_id}
            return dict
        elif int(result['state']) == -2:
            dict = {"交易所": "Okex交割合约", "合约ID": instrument_id, "方向": action, "订单状态": "失败", "order_id": order_id}
            return dict
        elif int(result['state']) == -1:
            dict = {"交易所": "Okex交割合约", "合约ID": instrument_id, "方向": action, "订单状态": "撤单成功", "成交均价": price,
                    "已成交数量": amount, "成交金额": turnover, "order_id": order_id}
            return dict
        elif int(result['state']) == 0:
            dict = {"交易所": "Okex交割合约", "合约ID": instrument_id, "方向": action, "订单状态": "等待成交", "order_id": order_id}
            return dict
        elif int(result['state']) == 1:
            dict = {"交易所": "Okex交割合约", "合约ID": instrument_id, "方向": action, "订单状态": "部分成交", "成交均价": price,
                    "已成交数量": amount, "成交金额": turnover, "order_id": order_id}
            return dict
        elif int(result['state']) == 3:
            dict = {"交易所": "Okex交割合约", "合约ID": instrument_id, "方向": action, "订单状态": "下单中", "order_id": order_id}
            return dict
        elif int(result['state']) == 4:
            dict = {"交易所": "Okex交割合约", "合约ID": instrument_id, "方向": action, "订单状态": "撤单中", "order_id": order_id}
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
        receipt = self.__okex_futures.get_kline(self.__instrument_id, granularity=granularity)
        receipt.reverse()
        for i in receipt:
            i[0] = utctime_str_to_mts(i[0])
        return receipt

    def get_position(self, mode=None):
        result = self.__okex_futures.get_specific_position(instrument_id=self.__instrument_id)
        if mode == "both":     # 若传入参数为"both"则查询双向持仓模式的持仓信息
            dict = {"long":
                {
                'amount': int(result['holding'][0]['long_qty']),
                'price': float(result['holding'][0]['long_avg_cost'])
            },
            "short":
                {
                'amount': int(result['holding'][0]['short_qty']),
                'price': float(result['holding'][0]['short_avg_cost'])
            }
            }
            return dict
        else:   # 未传入参数则默认为查询单向持仓模式的持仓信息
            if int(result['holding'][0]['long_qty']) > 0:
                dict = {'direction': 'long', 'amount': int(result['holding'][0]['long_qty']),
                        'price': float(result['holding'][0]['long_avg_cost'])}
                return dict
            elif int(result['holding'][0]['short_qty']) > 0:
                dict = {'direction': 'short', 'amount': int(result['holding'][0]['short_qty']),
                        'price': float(result['holding'][0]['short_avg_cost'])}
                return dict
            else:
                dict = {'direction': 'none', 'amount': 0, 'price': 0.0}
                return dict

    def get_ticker(self):
        receipt = self.__okex_futures.get_specific_ticker(instrument_id=self.__instrument_id)
        return receipt

    def get_contract_value(self):
        receipt = self.__okex_futures.get_products()
        result = {}
        for item in receipt:
            result[item['instrument_id']] = item['contract_val']
        contract_value = float(result[self.__instrument_id])
        return contract_value

    def get_depth(self, type=None, size=None):
        """
        OKEX交割合约获取深度数据
        :param type: 如不传参，返回asks和bids；只获取asks传入type="asks"；只获取"bids"传入type="bids"
        :param size: 返回深度档位数量，最多返回200，默认10档
        :return:
        """
        size = size or 10
        response = self.__okex_futures.get_depth(self.__instrument_id, size=size)
        asks_list = response["asks"]
        bids_list = response["bids"]
        asks= []
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
        result = self.__okex_futures.get_order_info(self.__instrument_id, order_id)
        return result

    def positions(self):
        result = self.__okex_futures.get_position()
        return result

    def tickers(self):
        receipt = self.__okex_futures.get_specific_ticker(instrument_id=self.__instrument_id)
        return receipt

    def orderbooks(self):
        response = self.__okex_futures.get_depth(self.__instrument_id, size=10)
        return response

    def info(self):
        result = requests.get("https://www.okex.com/api/futures/v3/instruments").json()
        return result