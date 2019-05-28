import logging
import urllib.request
from bs4 import BeautifulSoup

# リアルタイム運行状況のURL(石神井公園駅北口　→　成増駅南口）
BUS_SCHEDULE_URL_KOKUSAI = 'http://www.kokusaibus.com/blsys/loca?VID=ldt&EID=nt&DSMK=1207&DK=15n_af_hs6ih7-15n_af_hs6ih4-15n_af_hs6ih5-15n_af_ll'
BUS_SCHEDULE_URL_SEIBU = 'https://transfer.navitime.biz/seibubus-dia/pc/location/BusLocationResult?startId=00110202&goalId=00110102'


#運行状況を取得（西武バス）
def get_bus_schedule_seibu(url):
    logging.info("Retrieving URL: {}".format(url))
    content = urllib.request.urlopen(url).read()  #.decode('shift_jisx0213')するとエラーになる
    soup = BeautifulSoup(content, "html.parser")

    # 該当ページから時刻を取得できなかった時の処理
    errors = soup.select('.errorTxt')
    if len(list(errors)) > 0:
        message = errors[0].contents[0]
        logging.warn("Error: ".format(message))
        raise Exception(message)


    result = []
    for bus_info in soup.select('.orvPane')[:2]:
        res = list(map(lambda col: col.string, bus_info.find_all('div')))


        info = {
            'scheduled_arrival': res[2].replace('\t','').replace('\n','').replace('計画時刻:','時刻表によると'),  # 時刻表上の到着時刻(ex 10:00)
            'real_arrival': res[1].replace('\t','').replace('\n','').replace('到着予定:',''), #到着予定時刻
            'bus_stop': 'None',  # 乗り場 (ない時はNone)
            'destination': '（西武バス）。成増駅南口',  # 系統及び行き先
            'type': 'None',  # 車両 (ex ノンステップ)
            'status':''
        }
        if len(res) < 4:
            info.update({'status':'運行状況は不明です。'})
        else:
            info.update({'status': res[3].replace('\t','').replace('\n','').replace(':',"") + 'です。'})  # 運行状況 (ex 約5分遅れです, まもなく到着します)
        if info['real_arrival'] == '--:--':
            info.update({'real_arrival':info['scheduled_arrival']}) # 置き換え
        result += [info]
    return result


#運行状況を取得する（国際）
def get_bus_schedule_kokusai(url):
    logging.info("Retrieving URL: {}".format(url))
    content = urllib.request.urlopen(url).read().decode('shift_jisx0213')
    soup = BeautifulSoup(content, "html.parser")

    # 該当ページから時刻を取得できなかった時の処理
    errors = soup.select('.errorTxt')
    if len(list(errors)) > 0:
        message = errors[0].contents[0]
        logging.warn("Error: ".format(message))
        raise Exception(message)

    result = []
    for bus_info in soup.select('.R_Table tr')[1:]: # 最初の<tr>はタイトルなので除外する。
        res = list(map(lambda col: col.string, bus_info.find_all('td')))

        info = {
            'scheduled_arrival': res[0],  # 時刻表上の到着時刻(ex 10:00)
            'real_arrival': res[1], #到着予定時刻
            'bus_stop': res[2],  # 乗り場
            'destination': res[3].replace('【石02】','').replace('【石03】',''),  # 系統及び行き先
            'type': res[4],  # 車両 (ex ノンステップ)
            'status': res[5]  # 運行状況 (ex 約5分遅れです, まもなく到着します)
        }

        result += [info]

    return result


def bus(event, context):
    logging.info(event)


    # スケジュールを取得してメッセージを組み立てる
    try:
        #西武・国際の各運行状況を取得
        schedules_kokusai = get_bus_schedule_kokusai(BUS_SCHEDULE_URL_KOKUSAI)
        schedules_seibu   = get_bus_schedule_seibu(BUS_SCHEDULE_URL_SEIBU)


        #テスト用
        #print(schedules_kokusai[0]['real_arrival'])
        #print(schedules_kokusai[1]['real_arrival'])
        #if(len(schedules_seibu)>0):
            #print(schedules_seibu[0]['real_arrival'])
            #if(len(schedules_seibu)>1):
                #print(schedules_seibu[1]['real_arrival'])


        #時間の早い順にソートして集約
        schedules=[]
        schedules_fixed={}
        schedules.append(list(schedules_kokusai[0].items()))
        schedules.append(list(schedules_kokusai[1].items()))
        #西武バスは本数が少ないため，取得できていない可能性も考慮する
        if(len(schedules_seibu)>0):
            schedules.append(list(schedules_seibu[0].items()))
            if(len(schedules_seibu)>1):
                schedules.append(list(schedules_seibu[1].items()))

        #print(len(schedules))

        #到着時刻の早い順にソート
        schedules = sorted(schedules, key=lambda x: x[1])
        for i in range(len(schedules)):
                schedules_fixed[i] = dict(schedules[i])

        message = '{}行きのバスは{}到着予定。{}'.format(schedules_fixed[0]['destination'],schedules_fixed[0]['real_arrival'], schedules_fixed[0]['status'])
        if len(schedules_fixed) > 1:
            message += 'その次は{}行きのバスが{}到着予定。{}'.format(schedules_fixed[1]['destination'],schedules_fixed[1]['real_arrival'], schedules_fixed[1]['status'])



    except Exception as e:
        message = '運行情報を取得できません'

    logging.info(message)

    response = {
        'version': '1.0',
        'response': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': message,
            }
        }
    }

    return response



# cmdでの検証用
if __name__ == '__main__':
    print(bus(None, None))