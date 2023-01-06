#原始版15/261

import csv
import pandas as pd
from datetime import datetime

year = input("請輸入想要回測的年份：")

df1 = pd.read_csv(year+'.csv')

df1.Date_Time = pd.to_datetime(df1.Date_Time)

df1.index = df1.Date_Time
kbars_15min_high = df1.High.resample('15min',closed = 'right').max().dropna(axis=0,how='any') #最高。以5分鐘重新取樣一次後，取最大值 #dropna(axis=0,how='any') 把任何一列出現空白Nan刪掉
kbars_15min_low = df1.Low.resample('15min',closed = 'right').min().dropna(axis=0,how='any') #最低。以5分鐘重新取樣一次後，取最小值 #dropna(axis=0,how='any') 把任何一列出現空白Nan刪掉
kbars_15min_close = df1.Close.resample('15min',closed = 'right').last().dropna(axis=0,how='any') #收盤。以5分鐘重新取樣一次後，取最後一筆 #dropna(axis=0,how='any') 把任何一列出現空白Nan刪掉
kbars_15min_open = df1.Open.resample('15min',closed = 'right').first().dropna(axis=0,how='any') #開盤。以5分鐘重新取樣一次後，取第一筆 #dropna(axis=0,how='any') 把任何一列出現空白Nan刪掉
kbars_15min_volume = df1.Volume.resample('15min',closed = 'right').first().dropna(axis=0,how='any') #成交量。以5分鐘重新取樣一次後，取第一筆 #dropna(axis=0,how='any') 把任何一列出現空白Nan刪掉
df1_15min_kbars = pd.concat([kbars_15min_open, kbars_15min_high, kbars_15min_low, kbars_15min_close, kbars_15min_volume], axis=1)


import numpy as np
from backtesting import Backtest, Strategy 
from backtesting.lib import crossover
from backtesting.test import SMA 
import talib #要用MA這個指標就醫定要載 #https://ithelp.ithome.com.tw/articles/10273907


profitovertp = 0

class OneMA(Strategy): 
    
    n1 = 261  #預設的均線參數
    fk = 30 #fk/1000 停利
    ffk = 25 #fkk/1000 停損
    n_sl = 22
    bigger = 30 #當獲利曾經超過30點用來設定保利
    news = 7

    def init(self): #初始化會用到的參數和指標，告知要如何計算
        self.sma1 = self.I(SMA, self.data.Close, self.n1) 

    def next(self): 
        price = self.data.Close[-1]
        global profitovertp
        
        #紀錄目前為止的最大獲利有多少
        if self.position.size != 0 :
            profitovertp = max(profitovertp, self.position.pl)   
        else:
            profitovertp = 0

        #連續兩根收盤價 >sma 做多；反之做空
        
        #第一根漲破sma1；第二根站穩sma1
        if (self.data.Close[-2] > self.sma1[-2]) and (self.data.Open[-2] < self.sma1[-2]) and (self.data.Close[-1] > self.sma1[-1]) and (self.position.size == 0) :
            self.buy(size=1, tp=price+price*self.fk/1000, sl=price-price*self.ffk/10000)
        
        #第一根盤中曾接跌破SMA1不過收下引線收盤仍在SMA1之上，第二根也站穩SMA1之上
        elif (self.data.Close[-2] > self.sma1[-2]) and (self.data.Open[-2] > self.sma1[-2]) and (self.data.Low[-2] < self.sma1[-2]) and (self.data.Close[-1] > self.sma1[-1]) and (self.position.size == 0) :
            self.buy(size=1, tp=price+price*self.fk/1000, sl=price-price*self.ffk/10000)

        elif (self.data.Close[-2] < self.sma1[-2]) and (self.data.Open[-2] > self.sma1[-2]) and (self.data.Close[-1] < self.sma1[-1]) and (self.position.size == 0) :
            self.sell(size=1, tp=price-price*self.fk/1000, sl=price+price*self.ffk/10000)

        elif (self.data.Close[-2] < self.sma1[-2]) and (self.data.Open[-2] < self.sma1[-2]) and (self.data.High[-2] > self.sma1[-2]) and (self.data.Close[-1] < self.sma1[-1]) and (self.position.size == 0) :
            self.sell(size=1, tp=price-price*self.fk/1000, sl=price+price*self.ffk/10000)

        #收盤價跌破sma1，若有作多部位出場
        elif (self.data.Close[-1] < self.sma1[-1]) and (self.position.is_long):
            self.position.close()

        elif (self.data.Close[-1] > self.sma1[-1]) and (self.position.is_short):
            self.position.close()

        for trade in self.trades:
            
            #若最大獲利曾經超過30點，開始設定停損7點(應付盤整盤)
            if profitovertp > self.bigger and (self.position.is_long): 
                trade.sl = trade.entry_price+self.news

            elif profitovertp> self.bigger and (self.position.is_short):
                trade.sl = trade.entry_price-self.news

            #若最大獲利報酬率>0.022%，當獲利剩下最大獲利的一半時(ex.28點->14點)出場
            if (profitovertp/trade.entry_price) > self.n_sl/1000 and (self.position.is_short):
                trade.sl = trade.entry_price-0.5*profitovertp

            elif (profitovertp/trade.entry_price) > self.n_sl/1000 and (self.position.is_long):
                trade.sl = trade.entry_price+0.5*profitovertp

        return profitovertp


bt = Backtest(df1_15min_kbars, OneMA, cash=10000000, commission=0.00008)

#將跑完回測得到的數據放到stats
stats = bt.run()
stats = bt.optimize(n1=range(2, 300, 1), maximize='Equity Final [$]',method ='skopt') #用來最佳會用的
#fk=range(2, 100, 1), ffk=range(2, 30, 1)
#輸出回測統計
tradingstats = stats.to_csv("tradingstats.csv", index=False)
#輸出交易明細
op = stats['_trades'].to_csv("op.csv", index=False)
print(stats)

final_gain = (stats['Equity Final [$]']-10000000)*50 #總獲利金額(台幣)
print(final_gain)

#bt.plot()
