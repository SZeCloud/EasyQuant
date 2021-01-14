"""
币安币本位合约
Author: Gary-Hertel
Date:   2020/10/27
email: easyquant@foxmail.com
"""

import time
from easyquant.exchange.binance import binance_futures
from easyquant.time import ts_to_utc_str
from easyquant.config import config
from easyquant.exceptions import *
from easyquant.logger import logger
from easyquant.exchange.util import requests


class BINANCEFUTURES:

    def __init__(self, access_key, secret_key, instrument_id, margin_mode=None, leverage=None, position_side=None):
        """
        初始化
        :param access_key: api_key
        :param secret_key: secret_key
        :param symbol: 合约ID，例如：交割合约："ADA-USD-200925"  永续合约："ADA-USD-SWAP"
        :param leverage:开仓杠杆倍数，如不填则默认设置为20倍
        :param position_side:持仓模式，如不填则默认为单向持仓，如需双向持仓请传入"both"
        """
        self.__access_key = access_key
        self.__secret_key = secret_key
        if "SWAP" in instrument_id:
            self.__instrument_id = "{}{}_{}".format(instrument_id.split("-")[0], instrument_id.split("-")[1], "PERP")
        else:
            self.__instrument_id = "{}{}_{}".format(instrument_id.split("-")[0], instrument_id.split("-")[1], instrument_id.split("-")[2])
        self.__binance_futures = binance_futures
        self.__binance_futures.set(self.__access_key, self.__secret_key)   # 设置api
        self.position_side = position_side  # 持仓模式
        self.__leverage = leverage or 20
        try:
            if self.position_side == "both":
                # 设置所有symbol合约上的持仓模式为双向持仓模式
                self.__binance_futures.set_side_mode(dualSidePosition="true")
            else:
                # 设置所有symbol合约上的持仓模式为单向持仓模式
                self.__binance_futures.set_side_mode(dualSidePosition="false")
            # 设置指定symbol合约上的保证金模式为全仓模式
            if margin_mode == "fixed":
                self.__binance_futures.set_margin_mode(symbol=self.__instrument_id, marginType="ISOLATED")
            else:
                self.__binance_futures.set_margin_mode(symbol=self.__instrument_id, marginType="CROSSED")
            self.__binance_futures.set_leverage(self.__instrument_id, self.__leverage)
        except Exception as e:
            logger.error("设置单双向持仓、全逐仓模式、杠杆倍数失败：{}".format(e))

    def get_single_equity(self, currency):
        """
        获取单个币种合约的权益
        :param currency: 例如 "ETC"
        :return:返回浮点数
        """
        currency = self.__instrument_id.split("USD")[0]
        data = self.__binance_futures.balance()
        for i in data:
            if i["asset"] == currency:
                balance = float(i["balance"])
                return balance

    def buy(self, price=None, quantity=None, order_type=None, **kwargs):
        positionSide = "LONG" if self.position_side == "both" else "BOTH"
        order_type = "LIMIT" if order_type is None else order_type  # 默认限价单
        if order_type == "LIMIT":
            result = self.__binance_futures.order(symbol=self.__instrument_id,
                                                  side="BUY",
                                                  quantity=quantity,
                                                  price=price,
                                                  positionSide=positionSide,
                                                  order_type=order_type,
                                                  timeInForce="GTC")
        elif order_type == "MARKET":
            result = self.__binance_futures.order(symbol=self.__instrument_id,
                                                  side="BUY",
                                                  positionSide=positionSide,
                                                  order_type=order_type,
                                                  quantity=quantity
                                                  )
        else:
            result = self.__binance_futures.order(symbol=self.__instrument_id,
                                                  side="BUY",
                                                  order_type=order_type,
                                                  **kwargs
                                                  )
        if "msg" in str(result):   # 如果下单失败就抛出异常，提示错误信息。
            raise SendOrderError(result["msg"])
        order_info = self.get_order_info(order_id=result['orderId'])  # 下单后查询一次订单状态
        if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
            return order_info
        # 如果订单状态不是"完全成交"或者"失败"
        if config.price_cancellation:  # 选择了价格撤单时，如果最新价超过委托价一定幅度，撤单重发，返回下单结果
            if order_info["订单状态"] == "等待成交":
                if float(self.get_ticker()['last']) >= price * (1 + config.price_cancellation_amplitude):
                    try:
                        self.revoke_order(order_id=result['orderId'])
                        state = self.get_order_info(order_id=result['orderId'])
                        if state['订单状态'] == "撤单成功":
                            return self.buy(float(self.get_ticker()['last']) * (1 + config.reissue_order), quantity - state["已成交数量"])
                    except:
                        order_info = self.get_order_info(order_id=result['orderId'])
                        if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":
                            return order_info
            if order_info["订单状态"] == "部分成交":
                if float(self.get_ticker()['last']) >= price * (1 + config.price_cancellation_amplitude):
                    try:
                        self.revoke_order(order_id=result['orderId'])
                        state = self.get_order_info(order_id=result['orderId'])
                        if state['订单状态'] == "撤单成功":
                            return self.buy(float(self.get_ticker()['last']) * (1 + config.reissue_order),
                                            quantity - state["已成交数量"])
                    except:
                        order_info = self.get_order_info(order_id=result['orderId'])
                        if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":
                            return order_info
        if config.time_cancellation:  # 选择了时间撤单时，如果委托单发出多少秒后不成交，撤单重发，直至完全成交，返回成交结果
            time.sleep(config.time_cancellation_seconds)
            order_info = self.get_order_info(order_id=result['orderId'])
            if order_info["订单状态"] == "等待成交":
                try:
                    self.revoke_order(order_id=result['orderId'])
                    state = self.get_order_info(order_id=result['orderId'])
                    if state['订单状态'] == "撤单成功":
                        return self.buy(float(self.get_ticker()['last']) * (1 + config.reissue_order), quantity - state["已成交数量"])
                except:
                    order_info = self.get_order_info(order_id=result['orderId'])
                    if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":
                        return order_info
            if order_info["订单状态"] == "部分成交":
                try:
                    self.revoke_order(order_id=result['orderId'])
                    state = self.get_order_info(order_id=result['orderId'])
                    if state['订单状态'] == "撤单成功":
                        return self.buy(float(self.get_ticker()['last']) * (1 + config.reissue_order),
                                        quantity - state["已成交数量"])
                except:
                    order_info = self.get_order_info(order_id=result['orderId'])
                    if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":
                        return order_info
        if config.automatic_cancellation:
            # 如果订单未完全成交，且未设置价格撤单和时间撤单，且设置了自动撤单，就自动撤单并返回下单结果与撤单结果
            try:
                self.revoke_order(order_id=result['orderId'])
                state = self.get_order_info(order_id=result['orderId'])
                return state
            except:
                order_info = self.get_order_info(order_id=result['orderId'])
                if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":
                    return order_info
        else:  # 未启用交易助手时，下单并查询订单状态后直接返回下单结果
            return order_info

    def sell(self, price=None, quantity=None, order_type=None, **kwargs):
        positionSide = "LONG" if self.position_side == "both" else "BOTH"
        order_type = "LIMIT" if order_type is None else order_type  # 默认限价单
        if order_type == "LIMIT":
            result = self.__binance_futures.order(symbol=self.__instrument_id,
                                                  side="SELL",
                                                  quantity=quantity,
                                                  price=price,
                                                  positionSide=positionSide,
                                                  order_type=order_type,
                                                  timeInForce="GTC")
        elif order_type == "MARKET":
            result = self.__binance_futures.order(symbol=self.__instrument_id,
                                                  side="SELL",
                                                  positionSide=positionSide,
                                                  order_type=order_type,
                                                  quantity=quantity
                                                  )
        else:
            result = self.__binance_futures.order(symbol=self.__instrument_id,
                                                  side="SELL",
                                                  order_type=order_type,
                                                  **kwargs
                                                  )
        if "msg" in str(result):   # 如果下单失败就抛出异常，提示错误信息。
            raise SendOrderError(result["msg"])
        order_info = self.get_order_info(order_id=result['orderId'])  # 下单后查询一次订单状态
        if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
            return order_info
        # 如果订单状态不是"完全成交"或者"失败"
        if config.price_cancellation:  # 选择了价格撤单时，如果最新价超过委托价一定幅度，撤单重发，返回下单结果
            if order_info["订单状态"] == "等待成交":
                if float(self.get_ticker()['last']) <= price * (1 - config.price_cancellation_amplitude):
                    try:
                        self.revoke_order(order_id=result['orderId'])
                        state = self.get_order_info(order_id=result['orderId'])
                        if state['订单状态'] == "撤单成功":
                            return self.sell(float(self.get_ticker()['last']) * (1 - config.reissue_order), quantity - state["已成交数量"])
                    except:
                        order_info = self.get_order_info(order_id=result['orderId'])
                        if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":
                            return order_info
            if order_info["订单状态"] == "部分成交":
                if float(self.get_ticker()['last']) <= price * (1 - config.price_cancellation_amplitude):
                    try:
                        self.revoke_order(order_id=result['orderId'])
                        state = self.get_order_info(order_id=result['orderId'])
                        if state['订单状态'] == "撤单成功":
                            return self.sell(float(self.get_ticker()['last']) * (1 - config.reissue_order),
                                            quantity - state["已成交数量"])
                    except:
                        order_info = self.get_order_info(order_id=result['orderId'])
                        if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":
                            return order_info
        if config.time_cancellation:  # 选择了时间撤单时，如果委托单发出多少秒后不成交，撤单重发，直至完全成交，返回成交结果
            time.sleep(config.time_cancellation_seconds)
            order_info = self.get_order_info(order_id=result['orderId'])
            if order_info["订单状态"] == "等待成交":
                try:
                    self.revoke_order(order_id=result['orderId'])
                    state = self.get_order_info(order_id=result['orderId'])
                    if state['订单状态'] == "撤单成功":
                        return self.sell(float(self.get_ticker()['last']) * (1 - config.reissue_order), quantity - state["已成交数量"])
                except:
                    order_info = self.get_order_info(order_id=result['orderId'])
                    if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":
                        return order_info
            if order_info["订单状态"] == "部分成交":
                try:
                    self.revoke_order(order_id=result['orderId'])
                    state = self.get_order_info(order_id=result['orderId'])
                    if state['订单状态'] == "撤单成功":
                        return self.sell(float(self.get_ticker()['last']) * (1 - config.reissue_order),
                                        quantity - state["已成交数量"])
                except:
                    order_info = self.get_order_info(order_id=result['orderId'])
                    if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":
                        return order_info
        if config.automatic_cancellation:
            # 如果订单未完全成交，且未设置价格撤单和时间撤单，且设置了自动撤单，就自动撤单并返回下单结果与撤单结果
            try:
                self.revoke_order(order_id=result['orderId'])
                state = self.get_order_info(order_id=result['orderId'])
                return state
            except:
                order_info = self.get_order_info(order_id=result['orderId'])
                if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":
                    return order_info
        else:  # 未启用交易助手时，下单并查询订单状态后直接返回下单结果
            return order_info

    def buytocover(self, price=None, quantity=None, order_type=None, **kwargs):
        positionSide = "SHORT" if self.position_side == "both" else "BOTH"
        order_type = "LIMIT" if order_type is None else order_type  # 默认限价单
        if order_type == "LIMIT":
            result = self.__binance_futures.order(symbol=self.__instrument_id,
                                                  side="BUY",
                                                  quantity=quantity,
                                                  price=price,
                                                  positionSide=positionSide,
                                                  order_type=order_type,
                                                  timeInForce="GTC")
        elif order_type == "MARKET":
            result = self.__binance_futures.order(symbol=self.__instrument_id,
                                                  side="BUY",
                                                  positionSide=positionSide,
                                                  order_type=order_type,
                                                  quantity=quantity
                                                  )
        else:
            result = self.__binance_futures.order(symbol=self.__instrument_id,
                                                  side="BUY",
                                                  order_type=order_type,
                                                  **kwargs
                                                  )
        if "msg" in str(result):   # 如果下单失败就抛出异常，提示错误信息。
            raise SendOrderError(result["msg"])
        order_info = self.get_order_info(order_id=result['orderId'])  # 下单后查询一次订单状态
        if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
            return order_info
        # 如果订单状态不是"完全成交"或者"失败"
        if config.price_cancellation:  # 选择了价格撤单时，如果最新价超过委托价一定幅度，撤单重发，返回下单结果
            if order_info["订单状态"] == "等待成交":
                if float(self.get_ticker()['last']) >= price * (1 + config.price_cancellation_amplitude):
                    try:
                        self.revoke_order(order_id=result['orderId'])
                        state = self.get_order_info(order_id=result['orderId'])
                        if state['订单状态'] == "撤单成功":
                            return self.buytocover(float(self.get_ticker()['last']) * (1 + config.reissue_order), quantity - state["已成交数量"])
                    except:
                        order_info = self.get_order_info(order_id=result['orderId'])
                        if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":
                            return order_info
            if order_info["订单状态"] == "部分成交":
                if float(self.get_ticker()['last']) >= price * (1 + config.price_cancellation_amplitude):
                    try:
                        self.revoke_order(order_id=result['orderId'])
                        state = self.get_order_info(order_id=result['orderId'])
                        if state['订单状态'] == "撤单成功":
                            return self.buytocover(float(self.get_ticker()['last']) * (1 + config.reissue_order),
                                            quantity - state["已成交数量"])
                    except:
                        order_info = self.get_order_info(order_id=result['orderId'])
                        if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":
                            return order_info
        if config.time_cancellation:  # 选择了时间撤单时，如果委托单发出多少秒后不成交，撤单重发，直至完全成交，返回成交结果
            time.sleep(config.time_cancellation_seconds)
            order_info = self.get_order_info(order_id=result['orderId'])
            if order_info["订单状态"] == "等待成交":
                try:
                    self.revoke_order(order_id=result['orderId'])
                    state = self.get_order_info(order_id=result['orderId'])
                    if state['订单状态'] == "撤单成功":
                        return self.buytocover(float(self.get_ticker()['last']) * (1 + config.reissue_order), quantity - state["已成交数量"])
                except:
                    order_info = self.get_order_info(order_id=result['orderId'])
                    if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":
                        return order_info
            if order_info["订单状态"] == "部分成交":
                try:
                    self.revoke_order(order_id=result['orderId'])
                    state = self.get_order_info(order_id=result['orderId'])
                    if state['订单状态'] == "撤单成功":
                        return self.buytocover(float(self.get_ticker()['last']) * (1 + config.reissue_order),
                                        quantity - state["已成交数量"])
                except:
                    order_info = self.get_order_info(order_id=result['orderId'])
                    if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":
                        return order_info
        if config.automatic_cancellation:
            # 如果订单未完全成交，且未设置价格撤单和时间撤单，且设置了自动撤单，就自动撤单并返回下单结果与撤单结果
            try:
                self.revoke_order(order_id=result['orderId'])
                state = self.get_order_info(order_id=result['orderId'])
                return state
            except:
                order_info = self.get_order_info(order_id=result['orderId'])
                if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":
                    return order_info
        else:  # 未启用交易助手时，下单并查询订单状态后直接返回下单结果
            return order_info

    def sellshort(self, price=None, quantity=None, order_type=None, **kwargs):
        positionSide = "SHORT" if self.position_side == "both" else "BOTH"
        order_type = "LIMIT" if order_type is None else order_type  # 默认限价单
        if order_type == "LIMIT":
            result = self.__binance_futures.order(symbol=self.__instrument_id,
                                                  side="SELL",
                                                  quantity=quantity,
                                                  price=price,
                                                  positionSide=positionSide,
                                                  order_type=order_type,
                                                  timeInForce="GTC")
        elif order_type == "MARKET":
            result = self.__binance_futures.order(symbol=self.__instrument_id,
                                                  side="SELL",
                                                  positionSide=positionSide,
                                                  order_type=order_type,
                                                  quantity=quantity
                                                  )
        else:
            result = self.__binance_futures.order(symbol=self.__instrument_id,
                                                  side="SELL",
                                                  order_type=order_type,
                                                  **kwargs
                                                  )
        if "msg" in str(result):   # 如果下单失败就抛出异常，提示错误信息。
            raise SendOrderError(result["msg"])
        order_info = self.get_order_info(order_id=result['orderId'])  # 下单后查询一次订单状态
        if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
            return order_info
        # 如果订单状态不是"完全成交"或者"失败"
        if config.price_cancellation:  # 选择了价格撤单时，如果最新价超过委托价一定幅度，撤单重发，返回下单结果
            if order_info["订单状态"] == "等待成交":
                if float(self.get_ticker()['last']) <= price * (1 - config.price_cancellation_amplitude):
                    try:
                        self.revoke_order(order_id=result['orderId'])
                        state = self.get_order_info(order_id=result['orderId'])
                        if state['订单状态'] == "撤单成功":
                            return self.sellshort(float(self.get_ticker()['last']) * (1 - config.reissue_order), quantity - state["已成交数量"])
                    except:
                        order_info = self.get_order_info(order_id=result['orderId'])
                        if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":
                            return order_info
            if order_info["订单状态"] == "部分成交":
                if float(self.get_ticker()['last']) <= price * (1 - config.price_cancellation_amplitude):
                    try:
                        self.revoke_order(order_id=result['orderId'])
                        state = self.get_order_info(order_id=result['orderId'])
                        if state['订单状态'] == "撤单成功":
                            return self.sellshort(float(self.get_ticker()['last']) * (1 - config.reissue_order),
                                            quantity - state["已成交数量"])
                    except:
                        order_info = self.get_order_info(order_id=result['orderId'])
                        if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":
                            return order_info
        if config.time_cancellation:  # 选择了时间撤单时，如果委托单发出多少秒后不成交，撤单重发，直至完全成交，返回成交结果
            time.sleep(config.time_cancellation_seconds)
            order_info = self.get_order_info(order_id=result['orderId'])
            if order_info["订单状态"] == "等待成交":
                try:
                    self.revoke_order(order_id=result['orderId'])
                    state = self.get_order_info(order_id=result['orderId'])
                    if state['订单状态'] == "撤单成功":
                        return self.sellshort(float(self.get_ticker()['last']) * (1 - config.reissue_order), quantity - state["已成交数量"])
                except:
                    order_info = self.get_order_info(order_id=result['orderId'])
                    if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":
                        return order_info
            if order_info["订单状态"] == "部分成交":
                try:
                    self.revoke_order(order_id=result['orderId'])
                    state = self.get_order_info(order_id=result['orderId'])
                    if state['订单状态'] == "撤单成功":
                        return self.sellshort(float(self.get_ticker()['last']) * (1 - config.reissue_order),
                                        quantity - state["已成交数量"])
                except:
                    order_info = self.get_order_info(order_id=result['orderId'])
                    if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":
                        return order_info
        if config.automatic_cancellation:
            # 如果订单未完全成交，且未设置价格撤单和时间撤单，且设置了自动撤单，就自动撤单并返回下单结果与撤单结果
            try:
                self.revoke_order(order_id=result['orderId'])
                state = self.get_order_info(order_id=result['orderId'])
                return state
            except:
                order_info = self.get_order_info(order_id=result['orderId'])
                if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":
                    return order_info
        else:  # 未启用交易助手时，下单并查询订单状态后直接返回下单结果
            return order_info

    def get_order_info(self, order_id):
        """币安币本位合约查询订单信息"""
        result = self.__binance_futures.orderStatus(symbol=self.__instrument_id, orderId=order_id)
        instrument_id = self.__instrument_id
        action = None
        if result['side'] == 'BUY' and result["positionSide"] == "BOTH":
            action = "买入"
        elif result['side'] == 'SELL' and result["positionSide"] == "BOTH":
            action = "卖出"
        elif result['side'] == 'BUY' and result["positionSide"] == "LONG":
            action = "买入开多"
        elif result['side'] == 'SELL' and result["positionSide"] == "SHORT":
            action = "卖出开空"
        elif result['side'] == 'BUY' and result["positionSide"] == "SHORT":
            action = "买入平空"
        elif result['side'] == 'SELL' and result["positionSide"] == "LONG":
            action = "卖出平多"

        if result['status'] == "FILLED":
            dict = {"交易所": "币安币本位合约", "币对": instrument_id, "方向": action, "订单状态": "完全成交",
                    "成交均价": float(result['avgPrice']),
                    "已成交数量": int(result['executedQty']),
                    "成交金额": float(result["cumBase"]),
                    "order_id": order_id
                    }
            return dict
        elif result['status'] == "REJECTED":
            dict = {"交易所": "币安币本位合约", "币对": instrument_id, "方向": action, "订单状态": "失败", "order_id": order_id}
            return dict
        elif result['status'] == "CANCELED":
            dict = {"交易所": "币安币本位合约", "币对": instrument_id, "方向": action, "订单状态": "撤单成功",
                    "成交均价": float(result['avgPrice']),
                    "已成交数量": int(result['executedQty']),
                    "成交金额": float(result["cumBase"]),
                    "order_id": order_id}
            return dict
        elif result['status'] == "NEW":
            dict = {"交易所": "币安币本位合约", "币对": instrument_id, "方向": action, "订单状态": "等待成交", "order_id": order_id}
            return dict
        elif result['status'] == "PARTIALLY_FILLED":
            dict = {"交易所": "币安币本位合约", "币对": instrument_id, "方向": action, "订单状态": "部分成交",
                    "成交均价": float(result['avgPrice']),
                    "已成交数量": int(result['executedQty']),
                    "成交金额": float(result["cumBase"]),
                    "order_id": order_id}
            return dict
        elif result['status'] == "EXPIRED":
            dict = {"交易所": "币安币本位合约", "币对": instrument_id, "方向": action, "订单状态": "订单被交易引擎取消",
                    "成交均价": float(result['avgPrice']),
                    "已成交数量": int(result['executedQty']),
                    "成交金额": float(result["cumBase"]),
                    "order_id": order_id}
            return dict
        elif result['status'] == "PENDING_CANCEL	":
            dict = {"交易所": "币安币本位合约", "币对": instrument_id, "方向": action, "订单状态": "撤单中", "order_id": order_id}
            return dict

    def revoke_order(self, order_id):
        """币安币本位合约撤销订单"""
        receipt = self.__binance_futures.cancel(self.__instrument_id, orderId=order_id)
        try:
            if receipt['status'] == "CANCELED":
                return True
        except Exception as e:
            return "撤单失败：{}".format(e)

    def get_ticker(self):
        """币安币本位合约查询最新价"""
        response = self.__binance_futures.get_ticker(self.__instrument_id)[0]
        receipt = {'symbol': response['symbol'], 'last': response['price']}
        return receipt

    def get_kline(self, time_frame):
        """
        币安币本位合约获取k线数据
        :param time_frame: k线周期。1m， 3m， 5m， 15m， 30m， 1h， 2h， 4h， 6h， 8h， 12h， 1d， 3d， 1w， 1M
        :return:返回一个列表，包含开盘时间戳、开盘价、最高价、最低价、收盘价、成交量。
        """
        receipt = self.__binance_futures.klines(self.__instrument_id, time_frame)  # 获取历史k线数据
        for item in receipt:
            item[0] = int(item[0])
            item.pop(6)
            item.pop(7)
            item.pop(8)
            item.pop(6)
            item.pop(7)
            item.pop(6)
        return receipt

    def get_position(self, mode=None):
        """
        币安币本位合约获取持仓信息
        :return: 返回一个字典，{'direction': direction, 'amount': amount, 'price': price}
        """
        if mode == "both":
            long_amount = 0
            long_price = 0
            short_amount = 0
            short_price = 0
            receipt = self.__binance_futures.position()
            for item in receipt:
                if item["symbol"] == self.__instrument_id:
                    if item["positionSide"] == "LONG":
                        long_amount = int(item["positionAmt"])
                        long_price = float(item["entryPrice"])
                    if item["positionSide"] == "SHORT":
                        short_amount = abs(int(item["positionAmt"]))
                        short_price = float(item["entryPrice"])
            return {
                "long": {
                    "price": long_price,
                    "amount": long_amount
                },
                "short":{
                    "price": short_price,
                    "amount": short_amount
                }
            }
        else:
            result = None
            receipt = self.__binance_futures.position()
            for item in receipt:
                if item["symbol"] == self.__instrument_id and item["positionSide"] == "BOTH":
                    if float(item["positionAmt"]) == 0:
                        direction = "none"
                    else:
                        direction = 'long' if "-" not in item["positionAmt"] else "short"
                    amount = abs(int(item['positionAmt']))
                    price = float(item["entryPrice"])
                    result = {'direction': direction, 'amount': amount, 'price': price}
            return result

    def get_contract_value(self):
        receipt = self.__binance_futures.get_contract_value(self.__instrument_id)
        return receipt

    def get_depth(self, type=None):
        """
        币安币本位合约获取深度数据
        :param type: 如不传参，返回asks和bids；只获取asks传入type="asks"；只获取"bids"传入type="bids"
        :return:返回10档深度数据
        """
        response = self.__binance_futures.depth(self.__instrument_id)
        asks_list = response["asks"]
        bids_list = response["bids"]
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

    def get_funding_rate(self):
        """获取最新资金费率"""
        data = requests.get("https://dapi.binance.com/dapi/v1/premiumIndex?symbol=%s" % self.__instrument_id).json()
        instrument_id = data['symbol']
        funding_time = data['time']
        funding_rate = data['lastFundingRate']
        result = {
            "instrument_id": instrument_id,
            "funding_time": funding_time,
            "funding_rate": funding_rate
        }
        return result

    """一些查询交易所原始信息的接口"""

    def orders(self, order_id):
        result = self.__binance_futures.orderStatus(symbol=self.__instrument_id, orderId=order_id)
        return result

    def tickers(self):
        response = self.__binance_futures.get_ticker(self.__instrument_id)
        return response

    def positions(self):
        receipt = self.__binance_futures.position()
        return receipt

    def orderbooks(self):
        response = self.__binance_futures.depth(self.__instrument_id)
        return response

    def info(self):
        result = requests.get("https://dapi.binance.com/dapi/v1/exchangeInfo").json()
        return result