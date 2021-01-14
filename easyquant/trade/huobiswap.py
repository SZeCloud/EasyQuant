"""
火币永续合约
https://docs.huobigroup.com/docs/coin_margined_swap/v1/cn/#5ea2e0cde2
Author: Gary-Hertel
Date:   2020/10/27
email: easyquant@foxmail.com
"""

import time
from easyquant.exchange.huobi import huobi_swap as huobiusdswap
from easyquant.exchange.huobi import huobi_usdt_swap as huobiusdtswap
from easyquant.time import ts_to_utc_str
from easyquant.config import config
from easyquant.exceptions import *
from easyquant.exchange.util import requests
from easyquant.logger import logger


class HUOBISWAP:

    def __init__(self, access_key, secret_key, instrument_id, leverage=None):
        """
        :param access_key:
        :param secret_key:
        :param instrument_id: 'BTC-USD-SWAP'
        :param leverage:杠杆倍数，如不填则默认设置为20倍
        """
        self.__access_key = access_key
        self.__secret_key = secret_key
        self.__instrument_id = "{}-{}".format(instrument_id.split("-")[0], instrument_id.split("-")[1])
        if "USDT" in instrument_id or "usdt" in instrument_id:
            self.__huobi_swap = huobiusdtswap.HuobiUsdtSwap(self.__access_key, self.__secret_key)
        else:
            self.__huobi_swap = huobiusdswap.HuobiSwap(self.__access_key, self.__secret_key)
        self.__leverage = leverage or 20

    def get_single_equity(self, currency):
        """
        获取单个合约账户的权益
        :param currency: 例如 "BTC-USD"
        :return:返回浮点数
        """
        currency = self.__instrument_id
        data = self.__huobi_swap.get_contract_account_info(contract_code=currency)
        result =float(data["data"][0]["margin_balance"])
        return result

    def buy(self, price=None, quantity=None, order_type=None):
        order_type = "LIMIT" or order_type
        if order_type == 'LIMIT':
            order_price_type = 'limit'
        else:
            order_price_type = "opponent"
        result = self.__huobi_swap.send_contract_order(contract_code=self.__instrument_id,
                        client_order_id='', price=price, volume=quantity, direction='buy',
                        offset='open', lever_rate=self.__leverage, order_price_type=order_price_type)
        try:
            order_info = self.get_order_info(order_id=result['data']['order_id_str'])  # 下单后查询一次订单状态
        except:
            raise SendOrderError(result['err_msg'])
        if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
            return order_info
        # 如果订单状态不是"完全成交"或者"失败"
        if config.price_cancellation:  # 选择了价格撤单时，如果最新价超过委托价一定幅度，撤单重发，返回下单结果
            if order_info["订单状态"] == "准备提交" or order_info["订单状态"] == "已提交":
                try:    # 如果撤单成功，重发委托
                    if float(self.get_ticker()['last']) >= price * (1 + config.price_cancellation_amplitude):
                        self.revoke_order(order_id=result['data']['order_id_str'])
                        state = self.get_order_info(order_id=result['data']['order_id_str'])
                        if state['订单状态'] == "撤单成功" or state['订单状态'] == "部分成交撤销":
                            return self.buy(float(self.get_ticker()['last']) * (1 + config.reissue_order), quantity - state["已成交数量"])
                except: # 如果撤单失败，就再查询一次订单状态然后返回结果
                    order_info = self.get_order_info(order_id=result['data']['order_id_str'])  # 下单后查询一次订单状态
                    if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
                        return order_info
            if order_info["订单状态"] == "部分成交":
                if float(self.get_ticker()['last']) >= price * (1 + config.price_cancellation_amplitude):
                    try:
                        self.revoke_order(order_id=result['data']['order_id_str'])
                        state = self.get_order_info(order_id=result['data']['order_id_str'])
                        if state['订单状态'] == "部分成交撤销":
                            return self.buy(float(self.get_ticker()['last']) * (1 + config.reissue_order), quantity - state["已成交数量"])
                    except:  # 如果撤单失败，就再查询一次订单状态然后返回结果
                        order_info = self.get_order_info(order_id=result['data']['order_id_str'])  # 下单后查询一次订单状态
                        if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
                            return order_info
        if config.time_cancellation:  # 选择了时间撤单时，如果委托单发出多少秒后不成交，撤单重发，直至完全成交，返回成交结果
            time.sleep(config.time_cancellation_seconds)
            order_info = self.get_order_info(order_id=result['data']['order_id_str'])
            if order_info["订单状态"] == "准备提交" or order_info["订单状态"] == "已提交":
                try:
                    self.revoke_order(order_id=result['data']['order_id_str'])
                    state = self.get_order_info(order_id=result['data']['order_id_str'])
                    if state['订单状态'] == "撤单成功" or state['订单状态'] == "部分成交撤销":
                        return self.buy(float(self.get_ticker()['last']) * (1 + config.reissue_order), quantity - state["已成交数量"])
                except: # 如果撤单失败，就再查询一次订单状态然后返回结果
                    order_info = self.get_order_info(order_id=result['data']['order_id_str'])  # 下单后查询一次订单状态
                    if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
                        return order_info
            if order_info["订单状态"] == "部分成交":
                try:
                    self.revoke_order(order_id=result['data']['order_id_str'])
                    state = self.get_order_info(order_id=result['data']['order_id_str'])
                    if state['订单状态'] == "部分成交撤销":
                        return self.buy(float(self.get_ticker()['last']) * (1 + config.reissue_order), quantity - state["已成交数量"])
                except: # 如果撤单失败，就再查询一次订单状态然后返回结果
                    order_info = self.get_order_info(order_id=result['data']['order_id_str'])  # 下单后查询一次订单状态
                    if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
                        return order_info
        if config.automatic_cancellation:
            # 如果订单未完全成交，且未设置价格撤单和时间撤单，且设置了自动撤单，就自动撤单并返回下单结果与撤单结果
            try:
                self.revoke_order(order_id=result['data']['order_id_str'])
                state = self.get_order_info(order_id=result['data']['order_id_str'])
                return state
            except:  # 如果撤单失败，就再查询一次订单状态然后返回结果
                order_info = self.get_order_info(order_id=result['data']['order_id_str'])  # 下单后查询一次订单状态
                if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
                    return order_info
        else:  # 未启用交易助手时，下单并查询订单状态后直接返回下单结果
            return order_info

    def sell(self, price=None, quantity=None, order_type=None):
        order_type = "LIMIT" or order_type
        if order_type == 'LIMIT':
            order_price_type = 'limit'
        else:
            order_price_type = "opponent"
        result = self.__huobi_swap.send_contract_order(contract_code=self.__instrument_id,
                        client_order_id='', price=price, volume=quantity, direction='sell',
                        offset='close', lever_rate=self.__leverage, order_price_type=order_price_type)
        try:
            order_info = self.get_order_info(order_id=result['data']['order_id_str'])  # 下单后查询一次订单状态
        except:
            raise SendOrderError(result['err_msg'])
        if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
            return order_info
        # 如果订单状态不是"完全成交"或者"失败"
        if config.price_cancellation:  # 选择了价格撤单时，如果最新价超过委托价一定幅度，撤单重发，返回下单结果
            if order_info["订单状态"] == "准备提交" or order_info["订单状态"] == "已提交":
                if float(self.get_ticker()['last']) <= price * (1 - config.price_cancellation_amplitude):
                    try:
                        self.revoke_order(order_id=result['data']['order_id_str'])
                        state = self.get_order_info(order_id=result['data']['order_id_str'])
                        if state['订单状态'] == "撤单成功" or state["订单状态"] == "部分成交撤销":
                            return self.sell(float(self.get_ticker()['last']) * (1 - config.reissue_order), quantity - state["已成交数量"])
                    except:  # 如果撤单失败，就再查询一次订单状态然后返回结果
                        order_info = self.get_order_info(order_id=result['data']['order_id_str'])  # 下单后查询一次订单状态
                        if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
                            return order_info
            if order_info["订单状态"] == "部分成交":
                if float(self.get_ticker()['last']) <= price * (1 - config.price_cancellation_amplitude):
                    try:
                        self.revoke_order(order_id=result['data']['order_id_str'])
                        state = self.get_order_info(order_id=result['data']['order_id_str'])
                        if state['订单状态'] == "部分成交撤销":
                            return self.sell(float(self.get_ticker()['last']) * (1 - config.reissue_order), quantity - state["已成交数量"])
                    except:  # 如果撤单失败，就再查询一次订单状态然后返回结果
                        order_info = self.get_order_info(order_id=result['data']['order_id_str'])  # 下单后查询一次订单状态
                        if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
                            return order_info
        if config.time_cancellation:  # 选择了时间撤单时，如果委托单发出多少秒后不成交，撤单重发，直至完全成交，返回成交结果
            time.sleep(config.time_cancellation_seconds)
            order_info = self.get_order_info(order_id=result['data']['order_id_str'])
            if order_info["订单状态"] == "准备提交" or order_info["订单状态"] == "已提交":
                try:
                    self.revoke_order(order_id=result['data']['order_id_str'])
                    state = self.get_order_info(order_id=result['data']['order_id_str'])
                    if state['订单状态'] == "撤单成功" or state["订单状态"] == "部分成交撤销":
                        return self.sell(float(self.get_ticker()['last']) * (1 - config.reissue_order), quantity - state["已成交数量"])
                except:  # 如果撤单失败，就再查询一次订单状态然后返回结果
                    order_info = self.get_order_info(order_id=result['data']['order_id_str'])  # 下单后查询一次订单状态
                    if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
                        return order_info
            if order_info["订单状态"] == "部分成交":
                try:
                    self.revoke_order(order_id=result['data']['order_id_str'])
                    state = self.get_order_info(order_id=result['data']['order_id_str'])
                    if state['订单状态'] == "部分成交撤销":
                        return self.sell(float(self.get_ticker()['last']) * (1 - config.reissue_order), quantity - state["已成交数量"])
                except:  # 如果撤单失败，就再查询一次订单状态然后返回结果
                    order_info = self.get_order_info(order_id=result['data']['order_id_str'])  # 下单后查询一次订单状态
                    if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
                        return order_info
        if config.automatic_cancellation:
            # 如果订单未完全成交，且未设置价格撤单和时间撤单，且设置了自动撤单，就自动撤单并返回下单结果与撤单结果
            try:
                self.revoke_order(order_id=result['data']['order_id_str'])
                state = self.get_order_info(order_id=result['data']['order_id_str'])
                return state
            except:  # 如果撤单失败，就再查询一次订单状态然后返回结果
                order_info = self.get_order_info(order_id=result['data']['order_id_str'])  # 下单后查询一次订单状态
                if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
                    return order_info
        else:  # 未启用交易助手时，下单并查询订单状态后直接返回下单结果
            return order_info

    def buytocover(self, price=None, quantity=None, order_type=None):
        order_type = "LIMIT" or order_type
        if order_type == 'LIMIT':
            order_price_type = 'limit'
        else:
            order_price_type = "opponent"
        result = self.__huobi_swap.send_contract_order(contract_code=self.__instrument_id,
                        client_order_id='', price=price, volume=quantity, direction='buy',
                        offset='close', lever_rate=self.__leverage, order_price_type=order_price_type)
        try:
            order_info = self.get_order_info(order_id=result['data']['order_id_str'])  # 下单后查询一次订单状态
        except:
            raise SendOrderError(result['err_msg'])
        if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
            return order_info
        # 如果订单状态不是"完全成交"或者"失败"
        if config.price_cancellation:  # 选择了价格撤单时，如果最新价超过委托价一定幅度，撤单重发，返回下单结果
            if order_info["订单状态"] == "准备提交" or order_info["订单状态"] == "已提交":
                if float(self.get_ticker()['last']) >= price * (1 + config.price_cancellation_amplitude):
                    try:
                        self.revoke_order(order_id=result['data']['order_id_str'])
                        state = self.get_order_info(order_id=result['data']['order_id_str'])
                        if state['订单状态'] == "撤单成功" or state["订单状态"] == "部分成交撤销":
                            return self.buytocover(float(self.get_ticker()['last']) * (1 + config.reissue_order), quantity - state["已成交数量"])
                    except:  # 如果撤单失败，就再查询一次订单状态然后返回结果
                        order_info = self.get_order_info(order_id=result['data']['order_id_str'])  # 下单后查询一次订单状态
                        if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
                            return order_info
            if order_info["订单状态"] == "部分成交":
                if float(self.get_ticker()['last']) >= price * (1 + config.price_cancellation_amplitude):
                    try:
                        self.revoke_order(order_id=result['data']['order_id_str'])
                        state = self.get_order_info(order_id=result['data']['order_id_str'])
                        if state['订单状态'] == "部分成交撤销":
                            return self.buytocover(float(self.get_ticker()['last']) * (1 + config.reissue_order), quantity - state["已成交数量"])
                    except:  # 如果撤单失败，就再查询一次订单状态然后返回结果
                        order_info = self.get_order_info(order_id=result['data']['order_id_str'])  # 下单后查询一次订单状态
                        if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
                            return order_info
        if config.time_cancellation:  # 选择了时间撤单时，如果委托单发出多少秒后不成交，撤单重发，直至完全成交，返回成交结果
            time.sleep(config.time_cancellation_seconds)
            order_info = self.get_order_info(order_id=result['data']['order_id_str'])
            if order_info["订单状态"] == "准备提交" or order_info["订单状态"] == "已提交":
                try:
                    self.revoke_order(order_id=result['data']['order_id_str'])
                    state = self.get_order_info(order_id=result['data']['order_id_str'])
                    if state['订单状态'] == "撤单成功" or state["订单状态"] == "部分成交撤销":
                        return self.buytocover(float(self.get_ticker()['last']) * (1 + config.reissue_order), quantity - state["已成交数量"])
                except:  # 如果撤单失败，就再查询一次订单状态然后返回结果
                    order_info = self.get_order_info(order_id=result['data']['order_id_str'])  # 下单后查询一次订单状态
                    if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
                        return order_info
            if order_info["订单状态"] == "部分成交":
                try:
                    self.revoke_order(order_id=result['data']['order_id_str'])
                    state = self.get_order_info(order_id=result['data']['order_id_str'])
                    if state['订单状态'] == "部分成交撤销":
                        return self.buytocover(float(self.get_ticker()['last']) * (1 + config.reissue_order), quantity - state["已成交数量"])
                except:  # 如果撤单失败，就再查询一次订单状态然后返回结果
                    order_info = self.get_order_info(order_id=result['data']['order_id_str'])  # 下单后查询一次订单状态
                    if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
                        return order_info
        if config.automatic_cancellation:
            # 如果订单未完全成交，且未设置价格撤单和时间撤单，且设置了自动撤单，就自动撤单并返回下单结果与撤单结果
            try:
                self.revoke_order(order_id=result['data']['order_id_str'])
                state = self.get_order_info(order_id=result['data']['order_id_str'])
                return state
            except:  # 如果撤单失败，就再查询一次订单状态然后返回结果
                order_info = self.get_order_info(order_id=result['data']['order_id_str'])  # 下单后查询一次订单状态
                if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
                    return order_info
        else:  # 未启用交易助手时，下单并查询订单状态后直接返回下单结果
            return order_info

    def sellshort(self, price=None, quantity=None, order_type=None):
        order_type = "LIMIT" or order_type
        if order_type == 'LIMIT':
            order_price_type = 'limit'
        else:
            order_price_type = "opponent"
        result = self.__huobi_swap.send_contract_order(contract_code=self.__instrument_id,
                        client_order_id='', price=price, volume=quantity, direction='sell',
                        offset='open', lever_rate=self.__leverage, order_price_type=order_price_type)
        try:
            order_info = self.get_order_info(order_id=result['data']['order_id_str'])  # 下单后查询一次订单状态
        except:
            raise SendOrderError(result['err_msg'])
        if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
            return order_info
        # 如果订单状态不是"完全成交"或者"失败"
        if config.price_cancellation:  # 选择了价格撤单时，如果最新价超过委托价一定幅度，撤单重发，返回下单结果
            if order_info["订单状态"] == "准备提交" or order_info["订单状态"] == "已提交":
                if float(self.get_ticker()['last']) <= price * (1 - config.price_cancellation_amplitude):
                    try:
                        self.revoke_order(order_id=result['data']['order_id_str'])
                        state = self.get_order_info(order_id=result['data']['order_id_str'])
                        if state['订单状态'] == "撤单成功" or state["订单状态"] == "部分成交撤销":
                            return self.sellshort(float(self.get_ticker()['last']) * (1 - config.reissue_order), quantity - state["已成交数量"])
                    except:  # 如果撤单失败，就再查询一次订单状态然后返回结果
                        order_info = self.get_order_info(order_id=result['data']['order_id_str'])  # 下单后查询一次订单状态
                        if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
                            return order_info
            if order_info["订单状态"] == "部分成交":
                if float(self.get_ticker()['last']) <= price * (1 - config.price_cancellation_amplitude):
                    try:
                        self.revoke_order(order_id=result['data']['order_id_str'])
                        state = self.get_order_info(order_id=result['data']['order_id_str'])
                        if state['订单状态'] == "部分成交撤销":
                            return self.sellshort(float(self.get_ticker()['last']) * (1 - config.reissue_order), quantity - state["已成交数量"])
                    except:  # 如果撤单失败，就再查询一次订单状态然后返回结果
                        order_info = self.get_order_info(order_id=result['data']['order_id_str'])  # 下单后查询一次订单状态
                        if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
                            return order_info
        if config.time_cancellation:  # 选择了时间撤单时，如果委托单发出多少秒后不成交，撤单重发，直至完全成交，返回成交结果
            time.sleep(config.time_cancellation_seconds)
            order_info = self.get_order_info(order_id=result['data']['order_id_str'])
            if order_info["订单状态"] == "准备提交" or order_info["订单状态"] == "已提交":
                try:
                    self.revoke_order(order_id=result['data']['order_id_str'])
                    state = self.get_order_info(order_id=result['data']['order_id_str'])
                    if state['订单状态'] == "撤单成功" or state["订单状态"] == "部分成交撤销":
                        return self.sellshort(float(self.get_ticker()['last']) * (1 - config.reissue_order), quantity - state["已成交数量"])
                except:  # 如果撤单失败，就再查询一次订单状态然后返回结果
                    order_info = self.get_order_info(order_id=result['data']['order_id_str'])  # 下单后查询一次订单状态
                    if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
                        return order_info
            if order_info["订单状态"] == "部分成交":
                try:
                    self.revoke_order(order_id=result['data']['order_id_str'])
                    state = self.get_order_info(order_id=result['data']['order_id_str'])
                    if state['订单状态'] == "部分成交撤销":
                        return self.sellshort(float(self.get_ticker()['last']) * (1 - config.reissue_order), quantity - state["已成交数量"])
                except:  # 如果撤单失败，就再查询一次订单状态然后返回结果
                    order_info = self.get_order_info(order_id=result['data']['order_id_str'])  # 下单后查询一次订单状态
                    if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
                        return order_info
        if config.automatic_cancellation:
            # 如果订单未完全成交，且未设置价格撤单和时间撤单，且设置了自动撤单，就自动撤单并返回下单结果与撤单结果
            try:
                self.revoke_order(order_id=result['data']['order_id_str'])
                state = self.get_order_info(order_id=result['data']['order_id_str'])
                return state
            except:  # 如果撤单失败，就再查询一次订单状态然后返回结果
                order_info = self.get_order_info(order_id=result['data']['order_id_str'])  # 下单后查询一次订单状态
                if order_info["订单状态"] == "完全成交" or order_info["订单状态"] == "失败 ":  # 如果订单状态为"完全成交"或者"失败"，返回结果
                    return order_info
        else:  # 未启用交易助手时，下单并查询订单状态后直接返回下单结果
            return order_info

    def revoke_order(self, order_id):
        receipt = self.__huobi_swap.cancel_contract_order(self.__instrument_id, order_id)
        try:
            if receipt['status'] == "ok":
                return True
        except Exception as e:
            return "撤单失败：{}".format(e)

    def get_order_info(self, order_id):
        result = self.__huobi_swap.get_contract_order_info(self.__instrument_id, order_id)
        instrument_id = self.__instrument_id
        state = int(result['data'][0]['status'])
        avg_price = result['data'][0]['trade_avg_price']
        amount = result['data'][0]['trade_volume']
        turnover = result['data'][0]['trade_turnover']
        if result['data'][0]['direction'] == "buy" and result['data'][0]['offset'] == "open":
            action = "买入开多"
        elif result['data'][0]['direction'] == "buy" and result['data'][0]['offset'] == "close":
            action = "买入平空"
        elif result['data'][0]['direction'] == "sell" and result['data'][0]['offset'] == "open":
            action = "卖出开空"
        elif result['data'][0]['direction'] == "sell" and result['data'][0]['offset'] == "close":
            action = "卖出平多"
        else:
            action = "交易方向错误！"
        if state == 6:
            dict = {"交易所": "Huobi永续合约", "合约ID": instrument_id, "方向": action, "订单状态": "完全成交",
                    "成交均价": avg_price, "已成交数量": amount, "成交金额": turnover, "order_id": order_id}
            return dict
        elif state == 1:
            dict = {"交易所": "Huobi永续合约", "合约ID": instrument_id, "方向": action, "订单状态": "准备提交", "order_id": order_id}
            return dict
        elif state == 7:
            dict = {"交易所": "Huobi永续合约", "合约ID": instrument_id, "方向": action, "订单状态": "撤单成功",
                    "成交均价": avg_price, "已成交数量": amount, "成交金额": turnover, "order_id": order_id}
            return dict
        elif state == 2:
            dict = {"交易所": "Huobi永续合约", "合约ID": instrument_id, "方向": action, "订单状态": "准备提交", "order_id": order_id}
            return dict
        elif state == 4:
            dict = {"交易所": "Huobi永续合约", "合约ID": instrument_id, "方向": action, "订单状态": "部分成交",
                    "成交均价": avg_price, "已成交数量": amount, "成交金额": turnover, "order_id": order_id}
            return dict
        elif state == 3:
            dict = {"交易所": "Huobi永续合约", "合约ID": instrument_id, "方向": action, "订单状态": "已提交", "order_id": order_id}
            return dict
        elif state == 11:
            dict = {"交易所": "Huobi永续合约", "合约ID": instrument_id, "方向": action, "订单状态": "撤单中", "order_id": order_id}
            return dict
        elif state == 5:
            dict = {"交易所": "Huobi永续合约", "合约ID": instrument_id, "方向": action, "订单状态": "部分成交撤销",
                    "成交均价": avg_price, "已成交数量": amount, "成交金额": turnover, "order_id": order_id}
            return dict

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
        records = self.__huobi_swap.get_contract_kline(self.__instrument_id, period=period)['data']
        list = []
        for item in records:
            item = [1000 * int(item['id']), item['open'], item['high'], item['low'], item['close'], item['vol'], round(item['amount'], 2)]
            list.append(item)
        return list

    def get_position(self, mode=None):
        receipt = self.__huobi_swap.get_contract_position_info(self.__instrument_id)
        if mode == "both":
            if receipt['data'] == []:
                return {"long": {"price": 0, "amount": 0}, "short": {"price": 0, "amount": 0}}
            elif len(receipt['data']) == 1:
                if receipt['data'][0]['direction'] == "buy":
                    return {"long": {"price": receipt['data'][0]['cost_hold'], "amount": receipt['data'][0]['volume']}, "short": {"price": 0, "amount": 0}}
                elif receipt['data'][0]['direction'] == "sell":
                    return {"short": {"price": receipt['data'][0]['cost_hold'], "amount": receipt['data'][0]['volume']}, "long": {"price": 0, "amount": 0}}
            elif len(receipt['data']) == 2:
                return {
                    "long": {
                        "price": receipt['data'][0]['cost_hold'], "amount": receipt['data'][0]['volume']
                    },
                        "short": {
                            "price": receipt['data'][1]['cost_hold'], "amount": receipt['data'][1]['volume']
                        }
                }
        else:
            if receipt['data'] != []:
                direction = receipt['data'][0]['direction']
                amount = receipt['data'][0]['volume']
                price = receipt['data'][0]['cost_hold']
                if amount > 0 and direction == "buy":
                    dict = {'direction': 'long', 'amount': amount, 'price': price}
                    return dict
                elif amount > 0 and direction == "sell":
                    dict = {'direction': 'short', 'amount': amount, 'price': price}
                    return dict
            else:
                dict = {'direction': 'none', 'amount': 0, 'price': 0.0}
                return dict

    def get_ticker(self):
        receipt = self.__huobi_swap.get_contract_market_merged(self.__instrument_id)
        last = receipt['tick']['close']
        return {"last": last}

    def get_contract_value(self):
        receipt = self.__huobi_swap.get_contract_info()
        for item in receipt['data']:
            if item["contract_code"] == self.__instrument_id:
                contract_value = item["contract_size"]
                return contract_value

    def get_depth(self, type=None):
        """
        火币永续合约获取深度数据
        :param type: 如不传参，返回asks和bids；只获取asks传入type="asks"；只获取"bids"传入type="bids"
        :return:返回20档深度数据
        """
        response = self.__huobi_swap.get_contract_depth(contract_code=self.__instrument_id, type="step0")
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

    def get_funding_rate(self):
        """获取最新资金费率"""
        try:
            data = requests.get("https://api.hbdm.com/swap-api/v1/swap_funding_rate?contract_code=%s" % self.__instrument_id).json()
            instrument_id = data['data']['contract_code']
            funding_time = data['data']['funding_time']
            funding_rate = data['data']['funding_rate']
            result = {
                "instrument_id": instrument_id,
                "funding_time": funding_time,
                "funding_rate": funding_rate
            }
            return result
        except:
            data = requests.get(
                "https://api.hbdm.com/linear-swap-api/v1/swap_funding_rate?contract_code=%s" % self.__instrument_id).json()
            instrument_id = data['data']['contract_code']
            funding_time = data['data']['funding_time']
            funding_rate = data['data']['funding_rate']
            result = {
                "instrument_id": instrument_id,
                "funding_time": funding_time,
                "funding_rate": funding_rate
            }
            return result

    """获取交易所的一些原始信息"""

    def orders(self, order_id):
        result = self.__huobi_swap.get_contract_order_info(self.__instrument_id, order_id)
        return result

    def positions(self):
        receipt = self.__huobi_swap.get_contract_position_info()
        return receipt

    def tickers(self):
        receipt = self.__huobi_swap.get_contract_market_merged(self.__instrument_id)
        return receipt

    def orderbooks(self):
        response = self.__huobi_swap.get_contract_depth(contract_code=self.__instrument_id, type="step0")
        return response

    def info(self):
        if "USDT" in instrument_id or "usdt" in instrument_id:
            result = requests.get("https://api.hbdm.com/linear-swap-api/v1/swap_contract_info").json()
        else:
            result = requests.get("https://api.hbdm.com/swap-api/v1/swap_contract_info").json()
        return result