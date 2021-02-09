# -*- coding:utf-8 -*-

try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup


setup(
    name="easyquant",
    version="0.0.9",
    packages=[
        "easyquant",
        "easyquant/exchange",
        "easyquant/exchange/util",
        "easyquant/exchange/huobi",
        "easyquant/exchange/okex",
        "easyquant/exchange/binance",
        "easyquant/trade"
    ],
    platforms="any",
    description="Professional quant framework",
    url="https://github.com/Gary-Hertel/easyquant",
    author="Gary-Hertel",
    author_email="easyquant@foxmail.com",
    license="MIT",
    keywords=[
        "easyquant", "quant", "framework", "btc", "trade"
    ],
    install_requires=[
        "chardet>=3.0.4",
        "idna>=2.9",
        "mysql>=0.0.2",
        "mysqlclient>=2.0.1",
        "mysql-connector-python>=8.0.21",
        "numpy>=1.19.1",
        "pymongo>=3.10.1",
        "requests>=2.23.0",
        "six>=1.14.0",
        "twilio>=6.44.0",
        "urllib3>=1.25.8",
        "concurrent-log-handler>=0.9.17",
        "colorlog>=4.2.1",
        "pandas>=1.1.4",
        "matplotlib>=3.3.3"
    ]
)
