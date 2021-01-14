# -*- coding:utf-8 -*-

"""
数据存储与读取

Author: Gary-Hertel
Date:   2020/07/09
email: easyquant@foxmail.com
"""
import mysql.connector, pymongo
from easyquant.indicators import INDICATORS
import pandas as pd
from easyquant.config import config
from easyquant.time import *


class __Storage:
    """K线等各种数据的存储与读取"""

    def __init__(self):
        self.__old_kline = 0

    def __save_kline_func(self, database, data_sheet, timestamp, open, high, low, close, volume, currency_volume):
        """此函数专为存储7列k线数据的函数使用"""
        # 检查数据库是否存在，如不存在则创建
        user = config.mysql_user_name if config.mysql_authorization else 'root'
        password = config.mysql_password if config.mysql_authorization else 'root'
        conn1 = mysql.connector.connect(user=user, password=password)
        cursor1 = conn1.cursor()
        cursor1.execute("SHOW DATABASES")
        list1 = []
        for item in cursor1:
            for x in item:
                list1.append(x)
        if database in list1:
            pass
        else:
            cursor1.execute("CREATE DATABASE {}".format(database))
        conn1.commit()
        cursor1.close()
        conn1.close()
        # 检查数据表是否存在，如不存在则创建
        conn2 = mysql.connector.connect(user=user, password=password, database=database)
        cursor2 = conn2.cursor()
        cursor2.execute("SHOW TABLES")
        list2 = []
        for item in cursor2:
            for x in item:
                list2.append(x)
        if data_sheet in list2:
            pass
        else:
            cursor2.execute("CREATE TABLE {} (timestamp TEXT, open FLOAT, high FLOAT, low FLOAT, close FLOAT, volume FLOAT, currency_volume FLOAT)".format(data_sheet))
        # 插入数据
        cursor2.execute(
            'insert into {} (timestamp, open, high, low, close, volume, currency_volume) values (%s, %s, %s, %s, %s, %s, %s)'.format(
                data_sheet),
            [timestamp, open, high, low, close, volume, currency_volume])
        # 提交事务
        conn2.commit()
        # 关闭游标和连接
        cursor2.close()
        conn2.close()

    def __six_save_kline_func(self, database, data_sheet, timestamp, open, high, low, close, volume):
        """此函数专为存储6列k线数据的函数使用"""
        # 检查数据库是否存在，如不存在则创建
        user = config.mysql_user_name if config.mysql_authorization else 'root'
        password = config.mysql_password if config.mysql_authorization else 'root'
        conn1 = mysql.connector.connect(user=user, password=password)
        cursor1 = conn1.cursor()
        cursor1.execute("SHOW DATABASES")
        list1 = []
        for item in cursor1:
            for x in item:
                list1.append(x)
        if database in list1:
            pass
        else:
            cursor1.execute("CREATE DATABASE {}".format(database))
        conn1.commit()
        cursor1.close()
        conn1.close()
        # 检查数据表是否存在，如不存在则创建
        conn2 = mysql.connector.connect(user=user, password=password, database=database)
        cursor2 = conn2.cursor()
        cursor2.execute("SHOW TABLES")
        list2 = []
        for item in cursor2:
            for x in item:
                list2.append(x)
        if data_sheet in list2:
            pass
        else:
            cursor2.execute("CREATE TABLE {} (timestamp TEXT, open FLOAT, high FLOAT, low FLOAT, close FLOAT, volume FLOAT)".format(data_sheet))
        # 插入数据
        cursor2.execute(
            'insert into {} (timestamp, open, high, low, close, volume) values (%s, %s, %s, %s, %s, %s)'.format(
                data_sheet),
            [timestamp, open, high, low, close, volume])
        # 提交事务
        conn2.commit()
        # 关闭游标和连接
        cursor2.close()
        conn2.close()

    def kline_save(self, database, data_sheet, platform, instrument_id, time_frame):
        """
        从交易所获取k线数据，并将其存储至数据库中
        :param platform: 交易所
        :param database: 数据库名称
        :param data_sheet: 数据表名称
        :param instrument_id: 要获取k线数据的交易对名称或合约ID
        :param time_frame: k线周期，如'1m'为一分钟，'1d'为一天，字符串格式
        :return: "获取的历史数据已存储至mysql数据库！"
        """
        result = platform.get_kline(time_frame)
        result.reverse()
        try:
            for data in result:
                self.__save_kline_func(database, data_sheet, data[0], data[1], data[2], data[3], data[4], data[5], data[6])
        except:
            for data in result:
                self.__six_save_kline_func(database, data_sheet, data[0], data[1], data[2], data[3], data[4], data[5])
        print("获取的历史数据已存储至mysql数据库！")

    def kline_storage(self, database, data_sheet, platform, instrument_id, time_frame):
        """
        实时获取上一根k线存储至数据库中。
        :param database: 数据库名称
        :param data_sheet: 数据表名称
        :param instrument_id: 交易对或合约id
        :param time_frame: k线周期，如'1m', '1d'，字符串格式
        :return:
        """
        indicators = INDICATORS(platform, instrument_id, time_frame)
        if indicators.BarUpdate():
            last_kline = platform.get_kline(time_frame)[1]
            if last_kline != self.__old_kline:    # 若获取得k线不同于已保存的上一个k线
                timestamp = last_kline[0]
                open = last_kline[1]
                high = last_kline[2]
                low = last_kline[3]
                close = last_kline[4]
                volume = last_kline[5]
                self.__six_save_kline_func(database, data_sheet, timestamp, open, high, low, close, volume)
                print("时间：{} 实时k线数据已保存至MySQL数据库中！".format(get_localtime()))
                self.__old_kline = last_kline  # 将刚保存的k线设为旧k线
            else:
                return

    def read_mysql_datas(self, data, database, datasheet, field, operator):  # 获取数据库满足条件的数据
        """
        查询数据库中满足条件的数据
        :param data: 要查询的数据，数据类型由要查询的数据决定
        :param database: 数据库名称
        :param datasheet: 数据表名称
        :param field: 字段
        :return: 返回值查询到的数据，如未查询到则返回None
        """
        # 连接数据库
        user = config.mysql_user_name if config.mysql_authorization else 'root'
        password = config.mysql_password if config.mysql_authorization else 'root'
        conn = mysql.connector.connect(user=user, password=password, database=database, buffered=True)
        # 打开游标
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM {} WHERE {} {} '{}'".format(datasheet, field, operator, data))
        LogData = cursor.fetchall()  # 取出了数据库数据
        # 关闭游标和连接
        cursor.close()
        conn.close()
        return LogData

    def read_mysql_specific_data(self, data, database, datasheet, field):  # 获取数据库满足条件的数据
        """
        查询数据库中满足条件的数据
        :param data: 要查询的数据，数据类型由要查询的数据决定
        :param database: 数据库名称
        :param datasheet: 数据表名称
        :param field: 字段
        :return: 返回值查询到的数据，如未查询到则返回None
        """
        # 连接数据库
        user = config.mysql_user_name if config.mysql_authorization else 'root'
        password = config.mysql_password if config.mysql_authorization else 'root'
        conn = mysql.connector.connect(user=user, password=password, database=database, buffered=True)
        # 打开游标
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM {} WHERE {} = '{}'".format(datasheet, field, data))
        LogData = cursor.fetchone()  # 取出了数据库数据
        # 关闭游标和连接
        cursor.close()
        conn.close()
        return LogData

    def text_save(self, content, filename, mode='a'):
        """
        保存数据至txt文件。
        :param content: 要保存的内容,必须为string格式
        :param filename:文件路径及名称
        :param mode:
        :return:
        """
        with open(filename, mode=mode, encoding="utf-8") as file:
            file.write(content + '\n')

    def text_read(self, filename):
        """
        读取txt文件中的数据。
        :param filename: 文件路径、文件名称。
        :return:返回一个包含所有文件内容的列表，其中元素均为string格式
        """
        with open(filename, encoding="utf-8") as file:
            content = file.readlines()
        for i in range(len(content)):
            content[i] = content[i][:len(content[i]) - 1]
            file.close()
        return content

    def mongodb_save(self, database, collection, data):
        """保存数据至mongodb"""
        client = pymongo.MongoClient(host='localhost', port=27017)
        if config.mongodb_authorization:   # 如果启用了授权验证
            client.admin.authenticate(config.mongodb_user_name, config.mongodb_password, mechanism='SCRAM-SHA-1')
        db = client[database]
        col = db[collection]
        col.insert_one(data)

    def mongodb_read_data(self, database, collection):
        """读取mongodb数据库中某集合中的所有数据，并保存至一个列表中"""
        client = pymongo.MongoClient(host='localhost', port=27017)
        if config.mongodb_authorization:  # 如果启用了授权验证
            client.admin.authenticate(config.mongodb_user_name, config.mongodb_password, mechanism='SCRAM-SHA-1')
        db = client[database]
        col = db[collection]
        datalist = []
        for item in col.find():
            datalist.append([item])
        return datalist

    def export_mongodb_to_csv(self, database, collection, csv_file_path):
        """导出mongodb集合中的数据至csv文件"""
        client = pymongo.MongoClient(host='localhost', port=27017)
        if config.mongodb_authorization:  # 如果启用了授权验证
            client.admin.authenticate(config.mongodb_user_name, config.mongodb_password, mechanism='SCRAM-SHA-1')
        db = client[database]
        sheet_table = db[collection]
        df = pd.DataFrame(list(sheet_table.find()))
        df = df.drop('_id', axis=1, inplace=False)  # 删除列
        df.to_csv(csv_file_path, index=False)
        print("MongoDB【{}】数据库中【{}】集合的数据已导出至【{}】文件！".format(database, collection, csv_file_path))

    def delete_mysql_database(self, database):
        """删除mysql中的数据库"""
        # 连接数据库
        user = config.mysql_user_name if config.mysql_authorization else 'root'
        password = config.mysql_password if config.mysql_authorization else 'root'
        conn = mysql.connector.connect(user=user, password=password)
        cursor = conn.cursor()
        # 删除数据库
        sql = "DROP DATABASE IF EXISTS {}".format(database)
        cursor.execute(sql)
        # 保存更改并关闭连接
        conn.commit()
        cursor.close()
        conn.close()

    def delete_mongodb_database(self, database):
        """删除mongodb的数据库"""
        client = pymongo.MongoClient(host='localhost', port=27017)
        if config.mongodb_authorization:  # 如果启用了授权验证
            client.admin.authenticate(config.mongodb_user_name, config.mongodb_password, mechanism='SCRAM-SHA-1')
        db = client[database]
        db.command("dropDatabase")

    def mysql_save_strategy_run_info(self, database, data_sheet, timestamp, action, price, amount, turnover, hold_price, hold_direction, hold_amount, profit, total_profit, total_asset):
        """
        保存策略运行过程中的数据信息到mysql数据库中，可以是回测的信息或者是实盘运行过程中的信息
        :param database: 数据库名称
        :param data_sheet: 数据表名称
        :param timestamp: 时间戳
        :param action: 交易类型，如"买入开多"等等
        :param price: 下单价格
        :param amount: 下单数量
        :param turnover: 成交金额
        :param hold_price: 当前持仓价格
        :param hold_direction: 当前持仓方向
        :param hold_amount: 当前持仓数量
        :param profit: 此次交易盈亏
        :param total_profit: 策略运行总盈亏
        :param total_asset: 当前总资金
        :return:
        """
        # 检查数据库是否存在，如不存在则创建
        user = config.mysql_user_name if config.mysql_authorization else 'root'
        password = config.mysql_password if config.mysql_authorization else 'root'
        conn1 = mysql.connector.connect(user=user, password=password)
        cursor1 = conn1.cursor()
        cursor1.execute("SHOW DATABASES")
        list1 = []
        for item in cursor1:
            for x in item:
                list1.append(x)
        if database in list1:
            pass
        else:
            cursor1.execute("CREATE DATABASE {}".format(database))
        conn1.commit()
        cursor1.close()
        conn1.close()
        # 检查数据表是否存在，如不存在则创建
        conn2 = mysql.connector.connect(user=user, password=password, database=database)
        cursor2 = conn2.cursor()
        cursor2.execute("SHOW TABLES")
        list2 = []
        for item in cursor2:
            for x in item:
                list2.append(x)
        if data_sheet in list2:
            pass
        else:  # 如果数据表不存在就创建
            cursor2.execute(
                "CREATE TABLE {} (时间 TEXT, 类型 TEXT, 价格 FLOAT, 数量 FLOAT, 成交金额 FLOAT, 当前持仓价格 FLOAT, 当前持仓方向 TEXT, 当前持仓数量 FLOAT, 此次盈亏 FLOAT, 总盈亏 FLOAT, 总资金 FLOAT)".format(data_sheet))
        # 插入新数据
        cursor2.execute(
            'insert into {} (时间, 类型, 价格, 数量, 成交金额, 当前持仓价格, 当前持仓方向, 当前持仓数量, 此次盈亏, 总盈亏, 总资金) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'.format(data_sheet),
            [timestamp, action, price, amount, turnover, hold_price, hold_direction, hold_amount, profit, total_profit, total_asset])
        conn2.commit()
        cursor2.close()
        conn2.close()


storage = __Storage()


def combine_kline(csv_file_path, interval):
    """
    将自定义csv数据源的1分钟k线数据合成为任意周期的 k线数据，返回列表类型的k线数据，并自动保存新合成的k线数据至csv文件
    :param csv_file_path: 文件路径
    :param interval: 要合成的k线周期，例如3分钟就传入3，1小时就传入60，一天就传入1440
    :return: 返回列表类型的新合成的k线数据
    """
    df = pd.read_csv(csv_file_path)  # 读取传入的原1分钟k线数据
    df = df.set_index(pd.DatetimeIndex(pd.to_datetime(df['timestamp'], format='%Y-%m-%dT%H:%M:%S.000z', infer_datetime_format=True)))   # 设置索引
    open = df['open'].resample("%dmin"%interval, label="left", closed="left").first()    # 将open一列合成，取第一个价格
    high = df['high'].resample("%dmin"%interval, label="left", closed="left").max()  # 合并high一列，取最大值，即最高价
    low = df["low"].resample("%dmin"%interval, label="left", closed="left").min()    # 合并low一列，取最小值，即最低价
    close = df["close"].resample("%dmin"%interval, label="left", closed="left").last()   # 合并close一列，取最后一个价格
    volume = df["volume"].resample("%dmin"%interval, label="left", closed="left").sum()  # 合并volume一列，取和
    try:
        currency_volume = df["currency_volume"].resample("%dmin" % interval, label="left", closed="left").sum()  # 尝试合并currency_volume一列，如果失败则说明数据并不包含此列
        kline = pd.DataFrame(
            {"open": open, "high": high, "low": low, "close": close, "volume": volume, "currency_volume": currency_volume})
    except:
        kline = pd.DataFrame({"open": open, "high": high, "low": low, "close": close, "volume": volume})
    kline.to_csv("{}min_{}".format(interval, csv_file_path))    # 保存新数据至csv文件
    records = pd.read_csv("{}min_{}".format(interval, csv_file_path)) # 读取新文件，因为旧数据经处理后并不包含时间戳
    data = records.values.tolist()  # 将新读取的数据转换为列表数据类型
    return data

