import shioaji as sj  #引入shioaji套件，命名為sj
import datetime as dt
import pandas as pd
import numpy as np
import time
from datetime import datetime

maxprofit = 0

for i in range(0,120):

    api = sj.Shioaji()  #建立shioaji api物件，simulation=True代表使用模擬環境
    accounts = api.login("personalid", "passport")

    api.activate_ca(
        ca_path="c:\ekey\\551\身分證\S\Sinopac.pfx",
        ca_passwd="personalid",
        person_id="personalid",
    )

    buy_order = api.Order(
        action=sj.constant.Action.Buy,
        price=0, #價格(點) # MKT, MKP will not use price parameter 此時price = 0
        quantity=1, #口數
        price_type = 'MKP', #不知道為何官網是用STOCKPRICETYPE
        order_type= 'IOC',
        octype=sj.constant.FuturesOCType.Auto, #倉別，使用自動
        account=api.futopt_account #下單帳戶指定期貨帳戶
    )

    sell_order = api.Order(
        action=sj.constant.Action.Sell,
        price=0, #價格(點) # MKT, MKP will not use price parameter 此時price = 0
        quantity=1, #口數
        price_type = 'MKP', # change to MKT or MKP #不知道為何官網是用STOCKPRICETYPE
        order_type= 'IOC', # MKT, MKP only accecpt IOC order
        octype=sj.constant.FuturesOCType.Auto, #倉別，使用自動
        account=api.futopt_account #下單帳戶指定期貨帳戶
    )

    

    for i in range(0,900):

        contract_for_261k = api.Contracts.Futures.MXF['MXFR1']#用來抓歷史資料的contract
        contract = api.Contracts.Futures.MXF['MXF202206']#用來交易的contract

        while True: #應該是永豐自己套件設計的問題，常常半夜城市跑到一半停掉，只好用例外處理重新連線
            try:
                kbars = api.kbars(
                    contract_for_261k,
                    start = '2023-01-01',
                    end = '2023-12-31'
                )
                break
            
            except:
                api = sj.Shioaji()  #建立shioaji api物件，simulation=True代表使用模擬環境
                accounts = api.login("personalid", "passport")
                api.activate_ca(
                    ca_path="c:\ekey\\551\身分證\S\Sinopac.pfx",
                    ca_passwd="personalid",
                    person_id="personalid",
                )
                time.sleep(5)
                continue
        
        

        df = pd.DataFrame({**kbars})
        df.ts = pd.to_datetime(df.ts)

        df.index = df.ts #將ts資料，設定為DataFrame的index
        kbars_15min_high = df.High.resample('15min',closed = 'right').max().dropna(axis=0,how='any') #最高。以15分鐘重新取樣一次後，取最大值 #dropna(axis=0,how='any') 把任何一列出現空白Nan刪掉
        kbars_15min_low = df.Low.resample('15min',closed = 'right').min().dropna(axis=0,how='any') #最低。以15分鐘重新取樣一次後，取最小值 #dropna(axis=0,how='any') 把任何一列出現空白Nan刪掉
        kbars_15min_close = df.Close.resample('15min',closed = 'right').last().dropna(axis=0,how='any') #收盤。以15分鐘重新取樣一次後，取最後一筆 #dropna(axis=0,how='any') 把任何一列出現空白Nan刪掉
        kbars_15min_open = df.Open.resample('15min',closed = 'right').first().dropna(axis=0,how='any') #開盤。以15分鐘重新取樣一次後，取第一筆 #dropna(axis=0,how='any') 把任何一列出現空白Nan刪掉
        kbars_15min_volume = df.Volume.resample('15min',closed = 'right').first().dropna(axis=0,how='any') #成交量。以15分鐘重新取樣一次後，取第一筆 #dropna(axis=0,how='any') 把任何一列出現空白Nan刪掉
        kbars_15min_close261MA = df.Close.resample('15min',closed = 'right').last().dropna(axis=0,how='any').rolling(window=261).mean().round(2)

        #df_5min_kbars = pd.concat([kbars_5min_open, kbars_5min_high, kbars_5min_low, kbars_5min_close, kbars_5min_volume,], axis=1)
        df_15min_kbars_261version = pd.concat([kbars_15min_open, kbars_15min_high, kbars_15min_low, kbars_15min_close, kbars_15min_volume, kbars_15min_close261MA], axis=1)

        #
        last1_261k = df_15min_kbars_261version.iat[-2,5]
        last2_261k = df_15min_kbars_261version.iat[-3,5]

        #
        last1_close = df_15min_kbars_261version.iat[-2,3]
        last2_close = df_15min_kbars_261version.iat[-3,3]
        
        #
        last1_high = df_15min_kbars_261version.iat[-2,1]
        last2_high = df_15min_kbars_261version.iat[-3,1]
        #
        last1_low = df_15min_kbars_261version.iat[-2,2]
        last2_low = df_15min_kbars_261version.iat[-3,2]
        #
        last1_open = df_15min_kbars_261version.iat[-2,0]
        last2_open = df_15min_kbars_261version.iat[-3,0]

        #買賣策略開始

        while True:  #應該是永豐自己套件設計的問題，常常半夜城市跑到一半停掉，只好用例外處理重新連線
            try:
                positions = api.get_account_openposition(query_type='1', account=api.futopt_account)
                break
            except:
                continue
        
        df_positions = pd.DataFrame(positions.data())
        contractlist = [api.Contracts.Futures.MXF['MXFR1']]
        snapshots = api.snapshots(contractlist)

        
        if (last2_open < last2_261k) and (last2_close > last2_261k) and (last1_close > last1_261k) and df_positions.empty == True: #穿越做多
            now = datetime.now()
            current_time = now.strftime("%H:%M:%S")
            current_min = float(now.strftime("%M"))
            current_sec = float(now.strftime("%S"))
            if (current_min % 15 == 0 and current_sec < 15):
                buy_trade = api.place_order(contract, buy_order)
                time.sleep(4)

        elif (last2_open > last2_261k) and (last2_low < last2_261k) and (last2_close > last2_261k) and (last1_close > last1_261k) and df_positions.empty == True: #拉回站穩做多
            now = datetime.now()
            current_time = now.strftime("%H:%M:%S")
            current_min = float(now.strftime("%M"))
            current_sec = float(now.strftime("%S"))
            if (current_min % 15 == 0 and current_sec < 15):
                buy_trade = api.place_order(contract, buy_order)
                time.sleep(4)

        elif (last2_open > last2_261k) and (last2_close < last2_261k) and (last1_close < last1_261k) and df_positions.empty == True: #穿越做空
            now = datetime.now()
            current_time = now.strftime("%H:%M:%S")
            current_min = float(now.strftime("%M"))
            current_sec = float(now.strftime("%S"))
            if (current_min % 15 == 0 and current_sec < 15):
                sell_trade = api.place_order(contract, sell_order)
                time.sleep(4)

        elif (last2_open < last2_261k) and (last2_high > last2_261k) and (last2_close < last2_261k) and (last1_close < last1_261k) and df_positions.empty == True: #拉回站穩做空
            now = datetime.now()
            current_time = now.strftime("%H:%M:%S")
            current_min = float(now.strftime("%M"))
            current_sec = float(now.strftime("%S"))
            if (current_min % 15 == 0 and current_sec < 15):
                sell_trade = api.place_order(contract, sell_order)
                time.sleep(4)
        
        
        elif df_positions.empty != True:

            df_OrderType = df_positions.iat[0,5] #buy or sell
            df_ContractAverPrice = df_positions.iat[0,10]
    
            #未實現損益改成這樣寫，不然沒有開盤的時間它的價格會亂跳，導致未實現損益錯誤而亂下單
            if df_OrderType == "B":
                df_FlowProfitLoss = (float(snapshots[0].close)-float(df_ContractAverPrice))*50
                
            elif df_OrderType == "S":
                df_FlowProfitLoss = (float(df_ContractAverPrice)-float(snapshots[0].close))*50

            maxprofit = max(maxprofit, df_FlowProfitLoss)
            profit_percentage = (df_FlowProfitLoss-70)/(float(df_ContractAverPrice)*50)
            
            print("倉位：", df_OrderType, ", 持倉均價：", df_ContractAverPrice, ", 未實現損益：", df_FlowProfitLoss, " 損益%：", profit_percentage,)

            
            if (profit_percentage <= -0.0035) and df_OrderType == 'B': #多單跌破261停損
                sell_trade = api.place_order(contract, sell_order)
                maxprofit = 0
                time.sleep(4)
            
            elif (last1_close < last1_261k) and df_OrderType == 'B' : 
                now = datetime.now()
                current_time = now.strftime("%H:%M:%S")
                current_min = float(now.strftime("%M"))
                current_sec = float(now.strftime("%S"))
                if (current_min % 15 == 0 and current_sec <= 15):
                    sell_trade = api.place_order(contract, sell_order)
                    maxprofit = 0
                    time.sleep(4)

            elif (profit_percentage >= 0.018) and df_OrderType == 'B': #多單%停利 
                sell_trade = api.place_order(contract, sell_order)
                maxprofit = 0
                time.sleep(4)
                    
            elif (maxprofit > 1450) and (df_FlowProfitLoss <= 500) and  df_OrderType == 'B':
                now = datetime.now()
                current_time = now.strftime("%H:%M:%S")
                current_min = float(now.strftime("%M"))
                current_sec = float(now.strftime("%S"))
                if (current_min % 15 == 0 and current_sec <= 15):
                    sell_trade = api.place_order(contract, sell_order)
                    maxprofit = 0
                    time.sleep(4)


            elif (profit_percentage <= -0.0035) and df_OrderType == 'S': #空單%停損
                buy_trade = api.place_order(contract, buy_order)
                maxprofit = 0
                time.sleep(4)

            elif (last1_close > last1_261k) and df_OrderType == 'S': #空單漲破停損   
                now = datetime.now()
                current_time = now.strftime("%H:%M:%S")
                current_min = float(now.strftime("%M"))
                current_sec = float(now.strftime("%S"))
                if (current_min % 15 == 0 and current_sec <= 15):
                    buy_trade = api.place_order(contract, buy_order)
                    maxprofit = 0
                    time.sleep(4)

            elif (profit_percentage >= 0.018) and df_OrderType == 'S': #空單%停利
                buy_trade = api.place_order(contract, buy_order)
                maxprofit = 0
                time.sleep(4)

            elif (maxprofit > 1450) and (df_FlowProfitLoss <= 500) and  df_OrderType == 'S':
                now = datetime.now()
                current_time = now.strftime("%H:%M:%S")
                current_min = float(now.strftime("%M"))
                current_sec = float(now.strftime("%S"))
                if (current_min % 15 == 0 and current_sec <= 15):
                    buy_trade = api.place_order(contract, sell_order)
                    maxprofit = 0
                    time.sleep(4)

        time.sleep(4)