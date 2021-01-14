# -*- coding:utf-8 -*-

"""
持仓信息模块

Author: Gary-Hertel
Date:   2020/07/09
email: easyquant@foxmail.com
"""
from easyquant.market import MARKET
from easyquant.storage import storage


class POSITION:

    def __init__(self, platform, instrument_id, time_frame):
        self.__platform = platform
        self.__instrument_id = instrument_id
        self.__time_frame = time_frame
        self.__market = MARKET(self.__platform, self.__instrument_id, self.__time_frame)

    def direction(self, backtest=False):
        """获取当前持仓方向"""
        if backtest is False:    # 实盘模式下实时获取账户实际持仓方向，仅支持单向持仓模式下的查询
            result = self.__platform.get_position()['direction']
            return result
        else:   # 回测模式下从数据库中读取持仓方向
            result = storage.read_mysql_datas(0, "回测", self.__instrument_id.split("-")[0].lower() + "_" + self.__time_frame, "总资金", ">")[-1][6]
            return result

    def amount(self, mode=None, side=None, backtest=False):
        """获取当前持仓数量"""
        if backtest is False:    # 实盘模式下实时获取账户实际持仓数量
            if mode == "both":  # 如果传入参数"both"，查询双向持仓模式的持仓数量
                result = self.__platform.get_position(mode=mode)
                if side == "long":
                    long_amount = result["long"]["amount"]
                    return long_amount
                elif side == "short":
                    short_amount = result["short"]["amount"]
                    return short_amount
            else:
                result = self.__platform.get_position()['amount']
                return result
        else:   # 回测模式下从数据库中读取持仓数量
            result = storage.read_mysql_datas(0, "回测", self.__instrument_id.split("-")[0].lower() + "_" + self.__time_frame, "总资金", ">")[-1][7]
            return result

    def price(self, mode=None, side=None, backtest=False):
        """获取当前的持仓价格"""
        if backtest is False:    # 实盘模式下实时获取账户实际持仓价格
            if mode == "both":  # 如果传入参数"both"，查询双向持仓模式的持仓价格
                result = self.__platform.get_position(mode=mode)
                if side == "long":
                    long_price = result["long"]["price"]
                    return long_price
                elif side == "short":
                    short_price = result["short"]["price"]
                    return short_price
            else:
                result = self.__platform.get_position()['price']
                return result
        else:   # 回测模式下从数据库中读取持仓价格
            result = storage.read_mysql_datas(0, "回测", self.__instrument_id.split("-")[0].lower() + "_" + self.__time_frame, "总资金", ">")[-1][5]
            return result