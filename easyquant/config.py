# -*- coding:utf-8 -*-

"""
服务配置

Author: Gary-Hertel
Date:   2020/07/09
email: easyquant@foxmail.com
"""

import json


class __Config:
    """服务配置"""

    def loads(self, config_file=None):
        """
        加载配置。
        :param config_file:json配置文件
        :return:
        """
        with open(config_file) as json_file:
            configures = json.load(json_file)
        # push
        self.ding_talk_api = configures['DINGTALK']['ding_talk_api']
        self.accountSID = configures['TWILIO']['accountSID']
        self.authToken = configures['TWILIO']['authToken']
        self.myNumber = configures['TWILIO']['myNumber']
        self.twilio_Number = configures['TWILIO']['twilio_Number']
        self.from_addr = configures['SENDMAIL']['from_addr']
        self.password = configures['SENDMAIL']['password']
        self.to_addr = configures['SENDMAIL']['to_addr']
        self.smtp_server = configures['SENDMAIL']['smtp_server']
        self.mail_port = configures['SENDMAIL']['port']
        self.sendmail = configures['PUSH']['sendmail']
        self.dingtalk = configures['PUSH']['dingtalk']
        self.twilio = configures['PUSH']['twilio']
        # logger
        self.level = configures['LOG']['level']
        self.handler = configures['LOG']['handler']
        self.backup_count = configures['LOG']['backup_count']
        # first_run
        self.first_run = configures["STATUS"]["first_run"]
        # ASSISTANT
        price_cancellation_amplitude_str = configures["ASSISTANT"]["amplitude"]
        self.price_cancellation_amplitude = float((price_cancellation_amplitude_str.split("%"))[0]) / 100
        self.time_cancellation = configures["ASSISTANT"]["time_cancellation"]
        self.time_cancellation_seconds = configures["ASSISTANT"]["seconds"]
        self.price_cancellation = configures["ASSISTANT"]["price_cancellation"]
        reissue_order_overprice_range_str = configures["ASSISTANT"]["reissue_order"]
        self.reissue_order = float((reissue_order_overprice_range_str.split("%"))[0]) / 100
        self.automatic_cancellation = configures["ASSISTANT"]["automatic_cancellation"]
        # MONGODB AUTHORIZATION
        self.mongodb_authorization = configures["MONGODB"]["authorization"]
        self.mongodb_user_name = configures["MONGODB"]["user_name"]
        self.mongodb_password = configures["MONGODB"]["password"]
        # MYSQL AUTHORIZATION
        self.mysql_authorization = configures["MYSQL"]["authorization"]
        self.mysql_user_name = configures["MYSQL"]["user_name"]
        self.mysql_password = configures["MYSQL"]["password"]
        # PROXY
        try:
            self.proxy_host = configures["PROXY"].split(":")[0]
            self.proxy_port = configures["PROXY"].split(":")[1]
            self.proxy = True
        except:
            self.proxy = False
        # exchange
        try:
            self.okex_access_key = configures['EXCHANGE']['okex']['access_key']
            self.okex_secret_key = configures['EXCHANGE']['okex']['secret_key']
            self.okex_passphrase = configures['EXCHANGE']['okex']['passphrase']
        except:
            pass
        try:
            self.huobi_access_key = configures['EXCHANGE']['huobi']['access_key']
            self.huobi_secret_key = configures['EXCHANGE']['huobi']['secret_key']
        except:
            pass
        try:
            self.binance_access_key = configures['EXCHANGE']['binance']['access_key']
            self.binance_secret_key = configures['EXCHANGE']['binance']['secret_key']
        except:
            pass
        try:
            self.bitmex_access_key = configures['EXCHANGE']['bitmex']['access_key']
            self.bitmex_secret_key = configures['EXCHANGE']['bitmex']['secret_key']
        except:
            pass
        try:
            self.bitcoke_access_key = configures['EXCHANGE']['bitcoke']['access_key']
            self.bitcoke_secret_key = configures['EXCHANGE']['bitcoke']['secret_key']
        except:
            pass
        try:
            self.bybit_access_key = configures['EXCHANGE']['bybit']['access_key']
            self.bybit_secret_key = configures['EXCHANGE']['bybit']['secret_key']
        except:
            pass
        try:
            self.mxc_access_key = configures['EXCHANGE']['mxc']['access_key']
            self.mxc_secret_key = configures['EXCHANGE']['mxc']['secret_key']
        except:
            pass

    def update_config(self, config_file, config_content):
        """
        更新配置文件
        :param config_file: 配置文件路径及名称，如"config.json"
        :param config_content: 配置文件中的具体字典内容，将以当前content内容替换掉原配置文件中的内容
        :return: 打印"配置文件已更新！"
        """
        with open(config_file, 'w') as json_file:
            json.dump(config_content, json_file, indent=4)
        print("配置文件已更新！")


config = __Config()