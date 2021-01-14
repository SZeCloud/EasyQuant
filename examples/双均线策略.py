from easyquant.base import *                                                # 导入模块


class Strategy:                                                             # 创建策略类

    def __init__(self, platform, instrument_id, timeframe, asset, fast_length, slow_length, long_stop, short_stop):
        self.t = Trade("config.json", platform, instrument_id, timeframe)   # 初始化RestApi
        self.asset = asset                                                  # 总资金
        self.fast_length = fast_length                                      # 短周期均线长度
        self.slow_length = slow_length                                      # 长周期均线长度
        self.long_stop = long_stop                                          # 多头止损幅度
        self.short_stop = short_stop                                        # 空头止损幅度
        self.contract_value = self.t.contract_value                         # 合约面值
        if config.first_run:                                                # 第一次运行策略就往txt文件中保存总资金数据
            txt_save(str(self.asset), "data.txt")
        self.asset = float(txt_read("data.txt")[-1])                        # 启动策略时从txt文件中读取保存的self.asset
        logger.info("{} 双均线多空策略已启动！".format(instrument_id))          # 程序启动时打印提示信息

    def begin(self):                                                        # 策略主体
        try:
            ma = self.t.ma(self.fast_length, self.slow_length)              # 计算指标
            fast_ma = ma[0]                                                 # 取出短周期均线
            slow_ma = ma[1]                                                 # 取出长周期均线
            if fast_ma[-2] > slow_ma[-2] and fast_ma[-3] <= slow_ma[-3]:    # 金叉时
                if self.t.current_contracts == 0:                           # 若无持仓，买入开多
                    result = self.t.buy(self.t.last, int(self.asset/self.t.last/self.contract_value))
                    push(result)                                            # 推送下单结果
                elif self.t.current_direction == "short":                   # 若当前持空，平空后再开多
                    cover_amount = self.t.current_contracts                 # 平仓数量
                    hold_price = self.t.current_price                       # 持仓价格
                    result1 = self.t.buytocover(self.t.last, int(self.t.current_contracts))   # 买入平空
                    push(result1)                                           # 推送下单结果
                    avg_price = result1['成交均价']                           # 取出成交均价
                    profit = (avg_price - hold_price) * cover_amount * self.contract_value  # 计算利润
                    self.asset += profit                                    # 总资金变化
                    txt_save(str(self.asset), "data.txt")                   # 保存总资金道txt文件
                    result2 = self.t.buy(self.t.last, int(self.asset/self.t.last/self.contract_value))   # 买入开多
                    push(result2)
            # 死叉时
            if fast_ma[-2] < slow_ma[-2] and fast_ma[-3] >= slow_ma[-3]:
                if self.t.current_contracts == 0:
                    result = self.t.sellshort(self.t.last, int(self.asset/self.t.last/self.contract_value))
                    push(result)
                elif self.t.current_direction == "long":
                    cover_amount = self.t.current_contracts
                    hold_price = self.t.current_price
                    result1 = self.t.sell(self.t.last, int(self.t.current_contracts))
                    push(result1)
                    avg_price = result1['成交均价']
                    profit = (hold_price - avg_price) * cover_amount * self.contract_value
                    self.asset += profit
                    txt_save(str(self.asset), "data.txt")
                    result2 = self.t.sellshort(self.t.last, int(self.asset/self.t.last/self.contract_value))
                    push(result2)
            # 止损
            if self.t.current_contracts > 0:     # 如果当前持仓数量大于0
                if self.t.current_direction == "long" and self.t.last <= self.t.current_price * self.long_stop:
                    cover_amount = self.t.current_contracts
                    hold_price = self.t.current_price
                    result = self.t.sell(self.t.last, int(self.t.current_contracts))
                    push(result)
                    avg_price = result['成交均价']
                    profit = (hold_price - avg_price) * cover_amount * self.contract_value
                    self.asset += profit
                    txt_save(str(self.asset), "data.txt")
                    self.t.returnthisbar()   # 此根k线不再运行此策略
                if self.t.current_direction == "short" and self.t.last >= self.t.current_price * self.short_stop:
                    cover_amount = self.t.current_contracts
                    hold_price = self.t.current_price
                    result = self.t.buytocover(self.t.last, int(self.t.current_contracts))  # 买入平空
                    push(result)
                    avg_price = result['成交均价']
                    profit = (avg_price - hold_price) * cover_amount * self.contract_value
                    self.asset += profit
                    txt_save(str(self.asset), "data.txt")
                    self.t.returnthisbar()  # 此根k线不再运行此策略
        except:
            logger.error()


if __name__ == '__main__':

    strategy = Strategy("OKEXFUTURES", "TRX-USDT-210326", "15m", 50, 20, 30, 0.95, 1.05)
    while True:
        strategy.begin()
        sleep(3)