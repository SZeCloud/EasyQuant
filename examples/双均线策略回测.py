from easyquant.base import *


class Strategy:

    def __init__(self):
        self.b = BackTest('config.json', "OKEXFUTURES", "BTC-USDT-210625", "1d")
        self.asset = 1000
        self.fast_length = 20
        self.slow_length = 30
        self.long_stop = 0.95  # 多单止损幅度
        self.short_stop = 1.05  # 空单止损幅度
        self.contract_value = self.b.contract_value

    def begin(self):
        if self.b.bar_count < self.slow_length:   # 如果k线数据不够长就返回
            return
        # 计算策略信号
        ma = self.b.ma(self.fast_length, self.slow_length)
        fast_ma = ma[0]
        slow_ma = ma[1]
        cross_over = fast_ma[-2] >= slow_ma[-2] and fast_ma[-3] < slow_ma[-3]  # 不用当根k线上的ma来计算信号，防止信号闪烁
        cross_below = slow_ma[-2] >= fast_ma[-2] and slow_ma[-3] < fast_ma[-3]
        if cross_over:  # 金叉时
            if self.b.current_contracts == 0:    # 若当前无持仓，则买入开多记录下单结果
                backtest_save(self.b.timestamp, "买入开多", self.b.open, round(self.asset / self.b.open / self.contract_value), "long", self.b.open, round(self.asset / self.b.open / self.contract_value), 0, round(self.asset))
            if self.b.current_direction == 'short':  # 若当前持空头，先平空再开多
                profit = (self.b.current_price - self.b.open) * self.b.current_contracts * self.contract_value
                self.asset += profit
                backtest_save(self.b.timestamp, "买入平空", self.b.open, self.b.current_contracts, "none", 0, 0, round(profit), round(self.asset))
                backtest_save(self.b.timestamp, "买入开多", self.b.open, round(self.asset / self.b.open / self.contract_value), "long", self.b.open, round(self.asset / self.b.open / self.contract_value), 0, round(self.asset))
        if cross_below:
            if self.b.current_contracts == 0:    # 若当前无持仓，则卖出开空
                backtest_save(self.b.timestamp, "卖出开空", self.b.open, round(self.asset / self.b.open / self.contract_value), "short", self.b.open, round(self.asset / self.b.open / self.contract_value), 0, round(self.asset))
            if self.b.current_direction == 'long':  # 若当前持多头，先平多再开空
                # 平多
                profit = (self.b.open - self.b.current_price) * self.b.current_contracts * self.contract_value
                self.asset += profit
                backtest_save(self.b.timestamp, "卖出平多", self.b.open, self.b.current_contracts, "none", 0, 0, round(profit), round(self.asset))
                # 开空
                backtest_save(self.b.timestamp, "卖出开空", self.b.open, round(self.asset / self.b.open / self.contract_value), "short", self.b.open, round(self.asset / self.b.open / self.contract_value), 0, round(self.asset))
        # 止损
        if self.b.current_contracts > 0:
            if self.b.current_direction == 'long' and self.b.low <= self.b.current_price * self.long_stop:  # 多单止损
                profit = (self.b.current_price * self.long_stop - self.b.current_price) * self.b.current_contracts * self.contract_value
                self.asset += profit
                backtest_save(self.b.timestamp, "卖出平多", self.b.open, self.b.current_contracts, "none", 0, 0, round(profit), round(self.asset))

            if self.b.current_direction == 'short' and self.b.high >= self.b.current_price * self.short_stop:  # 空单止损
                profit = (self.b.current_price - self.b.current_price * self.long_stop) * self.b.current_contracts * self.contract_value
                self.asset += profit
                backtest_save(self.b.timestamp, "买入平空", self.b.open, self.b.current_contracts, "none", 0, 0, round(profit), round(self.asset))


if __name__ == '__main__':

    strategy = Strategy()
    records = []
    kline = read_server_data("binance", 2018, "btc", "1d")
    for k in kline:
        records.append(k)
        strategy.b.initialize(records, kline)
        strategy.begin()
    plot_asset()