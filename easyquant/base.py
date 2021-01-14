__all__ = [
    'sleep',
    'logger',
    'push',
    'Trade',
    'runforever',
    'utctime_str_to_ts',
    'txt_save',
    'txt_read',
    'combine_kline',
    'read_mysql_data',
    'read_mysql_specific_data',
    'read_mongodb_data',
    'save_to_mongodb',
    'export_mongodb_to_csv',
    'delete_mysql_database',
    'delete_mongodb_database',
    'ts_to_datetime_str',
    'BackTest',
    'backtest_save',
    'config',
    'current_date',
    'current_timestamp',
    'current_time',
    'read_server_data',
    'plot_asset',
    'current_ms_timestamp'
]


from easyquant.indicators import INDICATORS
from easyquant.trade.okexspot import OKEXSPOT
from easyquant.trade.okexfutures import OKEXFUTURES
from easyquant.trade.okexswap import OKEXSWAP
from easyquant.trade.huobispot import HUOBISPOT
from easyquant.trade.huobifutures import HUOBIFUTURES
from easyquant.trade.huobiswap import HUOBISWAP
from easyquant.trade.binancespot import BINANCESPOT
from easyquant.trade.binancefutures import BINANCEFUTURES
from easyquant.trade.binanceswap import BINANCESWAP
from easyquant.market import MARKET
from easyquant.position import POSITION
from easyquant.time import *
from easyquant.push import push
from easyquant.logger import logger
from easyquant.storage import storage
from easyquant.config import config
from easyquant.storage import combine_kline
import json
import mysql.connector
from matplotlib import pyplot as plt
import os
import pandas as pd
from easyquant import const


class Trade:

    def __init__(
            self,
            config_file,
            platform,
            symbol,
            time_frame=None,
            margin_mode=None,
            leverage=None,
            currency=None,
            position_side=None
    ):
        """
        初始化
        :param config_file: 配置文件路径
        :param platform: 交易所名称，如“OKEXSPOT”是okex现货
        :param symbol: 合约ID或者现货对名称
        :param time_frame: k线周期
        :param margin_mode: 持仓模式，默认设置全仓，如需逐仓传参“fixed”
        :param leverage: 杠杆倍数，默认20倍
        :param currency: 币种名称 ，用来查询账户指定币种权益
        :param position_side: 持仓模式，默认单向持仓，如需双向持仓传参“both”
        """
        config.loads(config_file)
        self.platform = platform
        self.symbol = symbol
        self.time_frame = time_frame
        margin_mode = margin_mode
        leverage = leverage
        self.currency = currency

        if self.platform == const.OKEXSPOT:
            self.platform = OKEXSPOT(config.okex_access_key, config.okex_secret_key, config.okex_passphrase, self.symbol)
        elif self.platform == const.OKEXFUTURES:
            self.platform = OKEXFUTURES(config.okex_access_key, config.okex_secret_key, config.okex_passphrase, self.symbol, margin_mode=margin_mode, leverage=leverage)
        elif self.platform == const.OKEXSWAP:
            self.platform = OKEXSWAP(config.okex_access_key, config.okex_secret_key, config.okex_passphrase, self.symbol, margin_mode=margin_mode, leverage=leverage)
        elif self.platform == const.HUOBISPOT:
            self.platform = HUOBISPOT(config.huobi_access_key, config.huobi_secret_key, self.symbol)
        elif self.platform == const.HUOBIFUTURES:
            self.platform = HUOBIFUTURES(config.huobi_access_key, config.huobi_secret_key, self.symbol, leverage=leverage)
        elif self.platform == const.HUOBISWAP:
            self.platform = HUOBISWAP(config.huobi_access_key, config.huobi_secret_key, self.symbol, leverage=leverage)
        elif self.platform == const.BINANCESPOT:
            self.platform = BINANCESPOT(config.binance_access_key, config.binance_secret_key, self.symbol)
        elif self.platform == const.BINANCEFUTURES:
            self.platform = BINANCEFUTURES(config.binance_access_key, config.binance_secret_key, self.symbol, margin_mode=margin_mode, leverage=leverage, position_side=position_side)
        elif self.platform == const.BINANCESWAP:
            self.platform = BINANCESWAP(config.binance_access_key, config.binance_secret_key, self.symbol, margin_mode=margin_mode, leverage=leverage, position_side=position_side)

        self.indicators = INDICATORS(self.platform, self.symbol, self.time_frame)
        self.market = MARKET(self.platform, self.symbol, self.time_frame)
        self.position = POSITION(self.platform, self.symbol, self.time_frame)

    """*******************************************************系统变量************************************************"""

    """获取交易所返回的原始数据的几个方法"""

    def orders(self, order_id):
        """获取指定order_id的订单的信息"""
        return self.platform.orders(order_id)

    def tickers(self):
        """获取指定币对的ticker信息"""
        return self.platform.tickers()

    def orderbooks(self):
        """获取指定币对的orderbook信息"""
        return self.platform.orderbooks()

    def positions(self):
        """获取全部币对的持仓信息"""
        return self.platform.positions()

    def info(self):
        """获取全部币对的价格精度等等信息"""
        return self.platform.info()

    """其他处理过的数据"""

    @property
    def funding_rate(self):
        """获取永续合约资金费率"""
        result = self.platform.get_funding_rate()
        return result
    
    @property
    def asks(self):
        """获取卖盘订单簿"""
        result = self.market.asks()
        return result

    @property
    def bids(self):
        """获取买盘订单簿"""
        result = self.market.bids()
        return result

    @property
    def bar_count(self):
        """K线总数"""
        result = self.indicators.CurrentBar()
        return result

    @property
    def contract_value(self):
        """获取合约面值"""
        result = float(self.market.contract_value())
        return result

    @property
    def close(self):
        """当根k线收盘价"""
        result = self.market.close(-1)
        return result

    @property
    def current_direction(self):
        """单向持仓模式下当前持仓方向"""
        result = self.position.direction()
        return result

    @property
    def current_contracts(self):
        """单向持仓模式下当前持仓数量"""
        result = self.position.amount()
        return result

    @property
    def current_price(self):
        """单向持仓模式下当前持仓均价"""
        result = self.position.price()
        return result

    @property
    def current_long_contracts(self):
        """双向持仓模式下当前多头持仓数量"""
        result = self.position.amount(mode="both", side="long")
        return result

    @property
    def current_short_contracts(self):
        """双向持仓模式下当前控头持仓数量"""
        result = self.position.amount(mode="both", side="short")
        return result

    @property
    def current_long_price(self):
        """双向持仓模式下当前多头持仓均价"""
        result = self.position.price(mode="both", side="long")
        return result

    @property
    def current_short_price(self):
        """双向持仓模式下当前空头持仓均价"""
        result = self.position.price(mode="both", side="short")
        return result

    @property
    def exchange_name(self):
        """交易所名称"""
        return self.platform

    @property
    def free_asset(self):
        """单个币种的可用权益"""
        result = self.platform.get_single_equity(currency=self.currency)
        return result

    @property
    def high(self):
        """当前k线最高价"""
        result = self.market.high(-1)
        return result

    @property
    def last(self):
        """当最新成交价"""
        result = self.market.last()
        return result

    @property
    def low(self):
        """当前k线最低价"""
        result = self.market.low(-1)
        return result

    @property
    def open(self):
        """当根k线开盘价"""
        result = self.market.open(-1)
        return result

    @property
    def symbol_name(self):
        """标的名称"""
        return self.symbol

    @property
    def volume(self):
        """当前k线成交量"""
        result = self.indicators.VOLUME()[-1]
        return result

    """*******************************************************系统函数************************************************"""

    def buy(self, price=None, quantity=None, order_type=None):
        """
        买入/买入开多
        限价单示例：buy(100, 20)  市价单：buy(100, 20, order_type="MARKET")
        :param price: 价格
        :param quantity: 数量
        :param order_type: 订单类型
        :return:
        """
        return self.platform.buy(price=price, quantity=quantity, order_type=order_type)

    def buytocover(self, price=None, quantity=None, order_type=None):
        """买入平空"""
        return self.platform.buytocover(price=price, quantity=quantity, order_type=order_type)

    def get_kline(self):
        """获取k线"""
        return self.platform.get_kline(self.time_frame)

    def sell(self, price=None, quantity=None, order_type=None):
        """卖出平多"""
        return self.platform.sell(price=price, quantity=quantity, order_type=order_type)

    def sellshort(self, price=None, quantity=None, order_type=None):
        """卖出开空"""
        return self.platform.sellshort(price=price, quantity=quantity, order_type=order_type)

    def cancel_order(self, order_id):
        """撤销指定的订单"""
        return self.platform.revoke_order(order_id)

    def get_order_info(self, order_id):
        """查询指定订单的信息"""
        return self.platform.get_order_info(order_id)

    def history_high(self, param, kline=None):
        """历史k线最高价"""
        result = self.market.high(param, kline=kline)
        return result

    def history_low(self, param, kline=None):
        """历史k线最低价"""
        result = self.market.low(param, kline=kline)
        return result

    def history_open(self, param, kline=None):
        """历史k线开盘价"""
        result = self.market.open(param, kline=kline)
        return result

    def history_close(self, param, kline=None):
        """历史k线收盘价"""
        result = self.market.close(param, kline=kline)
        return result

    def save_history_kline(self, database, data_sheet):
        """从交易所获取历史k线数据，并将其存储至MySQL数据库中"""
        storage.kline_save(database, data_sheet, self.platform, self.symbol, self.time_frame)

    def save_realtime_kline(self, database, data_sheet):
        """从交易所获取实时k线数据，并将其存储至MySQL数据库中"""
        storage.kline_storage(database, data_sheet, self.platform, self.symbol, self.time_frame)

    """*******************************************************技术指标************************************************"""

    def atr(self, length, kline=None):
        """真实波幅"""
        return self.indicators.ATR(length, kline=kline)

    def boll(self, length, kline=None):
        """布林"""
        return self.indicators.BOLL(length, kline=kline)

    def bar_update(self, kline=None):
        """判断k线是否更新"""
        return self.indicators.BarUpdate(kline=kline)

    def returnthisbar(self):
        """返回并结束这根k线上的代码运行，直到新的k线产生。"""
        while True:
            if self.indicators.BarUpdate():
                break
            else:
                sleep(3)

    def highest(self, length, kline=None):
        """周期最高价"""
        return self.indicators.HIGHEST(length, kline=kline)

    def ma(self, length, *args, kline=None):
        """移动平均线(简单移动平均)"""
        return self.indicators.MA(length, *args, kline=kline)

    def macd(self, fastperiod, slowperiod, signalperiod, kline=None):
        """MACD"""
        return self.indicators.MACD(fastperiod, slowperiod, signalperiod, kline=kline)

    def ema(self, length, *args, kline=None):
        """指数移动平均线"""
        return self.indicators.EMA(length, *args, kline=kline)

    def kama(self, length, *args, kline=None):
        """适应性移动平均线"""
        return self.indicators.KAMA(length, *args, kline=kline)

    def kdj(self, fastk_period, slowk_period, slowd_period, kline=None):
        """k值和d值"""
        return self.indicators.KDJ(fastk_period, slowk_period, slowd_period, kline=kline)

    def lowest(self, length, kline=None):
        """周期最低价"""
        return self.indicators.LOWEST(length, kline=kline)

    def obv(self, kline=None):
        """能量潮"""
        return self.indicators.OBV(kline=kline)

    def rsi(self, length, kline=None):
        """RSI"""
        return self.indicators.RSI(length, kline=kline)

    def roc(self, length, kline=None):
        """变动率指标"""
        return self.indicators.ROC(length, kline=kline)

    def stochrsi(self, timeperiod, fastk_period, fastd_period, kline=None):
        """STOCHRSI"""
        return self.indicators.STOCHRSI(timeperiod, fastk_period, fastd_period, kline=kline)

    def sar(self, kline=None):
        """抛物线指标"""
        return self.indicators.SAR(kline=kline)

    def stddev(self, length, nbdev=None, kline=None):
        """标准差"""
        return self.indicators.STDDEV(length, nbdev, kline=kline)

    def trix(self, length, kline=None):
        """三重指数平滑平均线"""
        return self.indicators.TRIX(length, kline=kline)


def runforever(func):
    """循环运行某个函数"""
    while True:
        func()


def txt_save(content, filename):
    """保存信息至txt文件"""
    storage.text_save(content, filename)


def txt_read(filename):
    """读取txt文件中信息"""
    return storage.text_read(filename)


def read_mysql_data(data, database, datasheet, field, operator):
    """查询数据库中满足条件的数据"""
    return storage.read_mysql_datas(data, database, datasheet, field, operator)


def read_mysql_specific_data(data, database, datasheet, field):
    """查询数据库中满足条件的数据"""
    return storage.read_mysql_specific_data(data, database, datasheet, field)


def save_to_mongodb(database, collection, data):
    """保存数据至mongodb"""
    storage.mongodb_save(database, collection, data)


def read_mongodb_data(database, collection):
    """读取mongodb数据库中某集合中的所有数据，并保存至一个列表中"""
    return storage.mongodb_read_data(database, collection)


def export_mongodb_to_csv(database, collection, csv_file_path):
    """导出mongodb集合中的数据至csv文件"""
    storage.export_mongodb_to_csv(database, collection, csv_file_path)


def delete_mysql_database(database):
    """删除mysql中的数据库"""
    storage.delete_mysql_database(database)


def delete_mongodb_database(database):
    """删除mongodb的数据库"""
    storage.delete_mongodb_database(database)


def current_timestamp():
    """当前秒时间戳"""
    return get_cur_timestamp()


def current_ms_timestamp():
    """当前毫秒时间戳"""
    return get_cur_timestamp_ms()


def current_date():
    """当前日期"""
    return get_date()


def current_time():
    """当前时间"""
    return get_localtime()


"""回测"""
class BackTest:
    def __init__(
            self,
            config_file,
            platform,
            symbol,
            time_frame=None,
            currency="USDT",
    ):
        config.loads(config_file)
        self.platform = platform
        self.symbol = symbol
        self.time_frame = time_frame
        self.currency = currency

        if self.platform == "OKEXSPOT":
            self.platform = OKEXSPOT(config.okex_access_key, config.okex_secret_key, config.okex_passphrase, self.symbol)
        elif self.platform == "OKEXFUTURES":
            self.platform = OKEXFUTURES(config.okex_access_key, config.okex_secret_key, config.okex_passphrase, self.symbol)
        elif self.platform == "OKEXSWAP":
            self.platform = OKEXSWAP(config.okex_access_key, config.okex_secret_key, config.okex_passphrase, self.symbol)
        elif self.platform == "HUOBISPOT":
            self.platform = HUOBISPOT(config.huobi_access_key, config.huobi_secret_key, self.symbol)
        elif self.platform == "HUOBIFUTURES":
            self.platform = HUOBIFUTURES(config.huobi_access_key, config.huobi_secret_key, self.symbol)
        elif self.platform == "HUOBISWAP":
            self.platform = HUOBISWAP(config.huobi_access_key, config.huobi_secret_key, self.symbol)
        elif self.platform == "BINANCESPOT":
            self.platform = BINANCESPOT(config.binance_access_key, config.binance_secret_key, self.symbol)
        elif self.platform == "BINANCEFUTURES":
            self.platform = BINANCEFUTURES(config.binance_access_key, config.binance_secret_key, self.symbol)
        elif self.platform == "BINANCESWAP":
            self.platform = BINANCESWAP(config.binance_access_key, config.binance_secret_key, self.symbol)

        self.indicators = INDICATORS(self.platform, self.symbol, self.time_frame)
        self.market = MARKET(self.platform, self.symbol, self.time_frame)
        self.position = POSITION(self.platform, self.symbol, self.time_frame)
        self.kline = None
        self.start_time = 0  # 回测开始时间
        backtest_save(get_localtime(), "none", 0, 0, "none", 0, 0, 0, 0)

    def initialize(self, kline, origin_data=None):
        """
        历史k线入口函数
        :param kline: 传入递增的k线
        :param origin_data: 传入原始k线数据计算回测进度
        :return:
        """
        length1 = len(kline)
        if length1 == 1:
            self.start_time = current_timestamp()
            print("{} 开始回测！".format(current_time()))
        if origin_data:
            length2 = len(origin_data)
            speed_of_progress = "{}%".format(round(length1 / length2 * 100, 2))
            print("{} 当前回测进度：{}".format(current_time(), speed_of_progress))
            if length1 == length2:
                cost = current_timestamp() - self.start_time
                print("回测完成，共计用时{}秒！".format(cost))
        self.kline = kline
        return self.kline

    @property
    def timestamp(self):
        """历史k线上的时间戳"""
        return self.kline[-1][0]

    @property
    def current_direction(self):
        """单向持仓模式下当前持仓方向"""
        result = read_backtest_info()["当前持仓方向"]
        return result

    @property
    def current_contracts(self):
        """单向持仓模式下当前持仓数量"""
        result = read_backtest_info()["当前持仓数量"]
        return float(result)

    @property
    def current_price(self):
        """单向持仓模式下当前持仓均价"""
        result = read_backtest_info()["当前持仓价格"]
        return float(result)

    @property
    def bar_count(self):
        """K线总数"""
        result = self.indicators.CurrentBar(kline=self.kline)
        return result

    @property
    def contract_value(self):
        """获取合约面值"""
        result = float(self.market.contract_value())
        return result

    @property
    def close(self):
        """当根k线收盘价"""
        result = self.market.close(-1, kline=self.kline)
        return result

    @property
    def high(self):
        """当前k线最高价"""
        result = self.market.high(-1, kline=self.kline)
        return result

    @property
    def low(self):
        """当前k线最低价"""
        result = self.market.low(-1, kline=self.kline)
        return result

    @property
    def open(self):
        """当根k线开盘价"""
        result = self.market.open(-1, kline=self.kline)
        return result

    @property
    def volume(self):
        """当前k线成交量"""
        result = self.indicators.VOLUME(kline=self.kline)[-1]
        return result

    def history_high(self, param):
        """历史k线最高价"""
        result = self.market.high(param, kline=self.kline)
        return result

    def history_low(self, param):
        """历史k线最低价"""
        result = self.market.low(param, kline=self.kline)
        return result

    def history_open(self, param):
        """历史k线开盘价"""
        result = self.market.open(param, kline=self.kline)
        return result

    def history_close(self, param):
        """历史k线收盘价"""
        result = self.market.close(param, kline=self.kline)
        return result

    def atr(self, length):
        """真实波幅"""
        return self.indicators.ATR(length, kline=self.kline)

    def boll(self, length):
        """布林"""
        return self.indicators.BOLL(length, kline=self.kline)

    def bar_update(self):
        """判断k线是否更新"""
        return self.indicators.BarUpdate(kline=self.kline)

    def highest(self, length):
        """周期最高价"""
        return self.indicators.HIGHEST(length, kline=self.kline)

    def ma(self, length, *args):
        """移动平均线(简单移动平均)"""
        return self.indicators.MA(length, *args, kline=self.kline)

    def macd(self, fastperiod, slowperiod, signalperiod):
        """MACD"""
        return self.indicators.MACD(fastperiod, slowperiod, signalperiod, kline=self.kline)

    def ema(self, length, *args):
        """指数移动平均线"""
        return self.indicators.EMA(length, *args, kline=self.kline)

    def kama(self, length, *args):
        """适应性移动平均线"""
        return self.indicators.KAMA(length, *args, kline=self.kline)

    def kdj(self, fastk_period, slowk_period, slowd_period):
        """k值和d值"""
        return self.indicators.KDJ(fastk_period, slowk_period, slowd_period, kline=self.kline)

    def lowest(self, length):
        """周期最低价"""
        return self.indicators.LOWEST(length, kline=self.kline)

    def obv(self):
        """能量潮"""
        return self.indicators.OBV(kline=self.kline)

    def rsi(self, length):
        """RSI"""
        return self.indicators.RSI(length, kline=self.kline)

    def roc(self, length):
        """变动率指标"""
        return self.indicators.ROC(length, kline=self.kline)

    def stochrsi(self, timeperiod, fastk_period, fastd_period):
        """STOCHRSI"""
        return self.indicators.STOCHRSI(timeperiod, fastk_period, fastd_period, kline=self.kline)

    def sar(self):
        """抛物线指标"""
        return self.indicators.SAR(kline=self.kline)

    def stddev(self, length, nbdev=None):
        """标准差"""
        return self.indicators.STDDEV(length, nbdev, kline=self.kline)

    def trix(self, length):
        """三重指数平滑平均线"""
        return self.indicators.TRIX(length, kline=self.kline)


def backtest_save(timestamp, action, price, amount, hold_direction, hold_price, hold_amount, profit, asset):
    """保存回测信息至txt文件"""
    dict = {
        "时间": timestamp,
        "操作": action,
        "价格": price,
        "数量": amount,
        "当前持仓方向": hold_direction,
        "当前持仓价格": hold_price,
        "当前持仓数量": hold_amount,
        "此次盈亏": profit,
        "当前总资金": asset
    }
    content = json.dumps(dict, ensure_ascii=False)
    txt_save(content, "回测.txt")


def read_backtest_info():
    """读取回测过程中保存至txt文件的持仓信息"""
    data = txt_read(".\回测.txt")[-1]
    data = json.loads(data)
    return data


def read_backtest_asset():
    """读取回测完成后的总资金数据"""
    data = txt_read(".\回测.txt")
    data.pop(0)
    time = []
    asset = []
    profit = []
    for i in data:
        result = json.loads(i)
        if result["当前总资金"] != 0:
            time.append(result["时间"])
            asset.append(result["当前总资金"])
            if result['此次盈亏'] > 0:
                profit.append(result['此次盈亏'])
    rate_of_win = "{}%".format(round(len(profit) / len(data) * 100, 2)*2)
    information = {"time": time, "asset": asset, "rate_of_win": rate_of_win}
    return information


def plot_asset():
    """回测完成后调用此函数绘制资金曲线图"""
    x = read_backtest_asset()["time"]
    y = read_backtest_asset()["asset"]
    profit = y[-1] - y[0]   # 累计收益
    yields = "{}%".format(round((profit / y[0]) * 100), 2)  # 收益率
    maximum_retreat = "{}%".format(round((min(y) - y[0]) / y[0] * 100, 2))  # 最大回撤
    rate = read_backtest_asset()["rate_of_win"]     # 胜率
    print("累计收益:", profit)
    print("总收益率:", yields)
    print("最大回撤:", maximum_retreat)
    print("系统胜率:", rate)
    plt.rcParams['axes.unicode_minus'] = False
    plt.figure(figsize=(15, 6))
    plt.subplot(facecolor="black")
    plt.plot(x, y, color="c", linestyle="-", linewidth=1.0)
    plt.xlabel("Date")
    plt.ylabel("Asset")
    plt.title("Backtest Result")
    # plt.xticks(rotation=15)
    plt.xticks(())  # 关闭x轴标签
    figManager = plt.get_current_fig_manager()
    figManager.window.showMaximized()
    os.rename(".\回测.txt", ".\回测 {}.txt".format(current_timestamp()))
    plt.show()


def read_server_data(platform, year, symbol, timeframe):
    """
    获取easyquant服务器上的历史k线数据
    :param platform: 交易所名称，如："BINANCE"
    :param year: 年份，如：2018
    :param symbol: 币种，如："BTC"
    :param timeframe: k线周期，如："1h"
    :return: 返回一个列表
    """
    platform = platform.lower()
    symbol = symbol.lower()
    timeframe = timeframe.lower()
    platform_list = ['binance']

    if platform not in platform_list:
        print("目前只支持的交易所：", [i for i in platform_list])
        exit()

    if platform == "binance":
        year_list = [2018, 2019]
        symbol_list = ["btc", "bch", "eos", "etc", "eth", "link", "ltc", "trx", "xrp"]
        timeframe_list = ["15m", "30m", "1h", "2h", "4h", "1d"]
        if year not in year_list:
            print("币安交易所只支持年份：", [i for i in year_list])
            exit()
        if symbol not in symbol_list:
            print("币安交易所只支持币种：", [i for i in symbol_list])
            exit()
        if timeframe not in timeframe_list:
            print("币安交易所只支持k线周期：", [i for i in timeframe_list])
            exit()

    datasheet = "{}_{}_{}_usdt_{}".format(platform, year, symbol, timeframe)
    try:
        conn = mysql.connector.connect(
            host="purequant.cloud",
            user="garyhertel",
            password="^C_U7TN.,+,KoV#W:Z_!",
            database="kline",
            buffered=True
        )
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM {} WHERE {} {} '{}'".format(datasheet, "open", ">", 0))
        data = cursor.fetchall()
        cursor.close()
        conn.close()
        print("{} 读取服务器数据成功！".format(current_time()))
        return data
    except Exception as e:
        if "Access denied" in str(e):
            info = str(e).split("' (using password: YES)")[0]
            ip = info.split("'@'")[1]
            print("你的IP地址是：{}，你目前没有权限访问数据库，只有作业合格的同学才有权限访问！".format(ip))
        else:
            print("ERROR: {}".format(e))