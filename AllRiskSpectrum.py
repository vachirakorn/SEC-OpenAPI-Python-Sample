import requests
import json
import pandas as pd
from pandas import ExcelWriter

headers = {
    # Request headers
    'Ocp-Apim-Subscription-Key': '1a64accca0e0405e98ae04763d5f4eda' # Don't forget to put your keys in xxxx
}

from ratelimit import *
import requests

command_code = 13

# 1 วิ เรียกได้ 5 ครั้ง
class RateLimiter:
    def __init__(self, headers):
        headers = headers
        return
    @rate_limited(1500, 300)
    def call_get_api(self, url):
        response = requests.get(url, headers=headers)

        if response.status_code == 204:
            return response
        if response.status_code != 200:
            print('Cannot call API: {}'.format(response.status_code))
        return response

limiter = RateLimiter(headers)

req = requests.get(f'https://api.sec.or.th/FundFactsheet/fund/amc', headers = headers)
amc = pd.read_json(req.content)

all_funds = pd.DataFrame(columns=['proj_id', 'proj_abbr_name','proj_name_en', 'proj_name_th','unique_id'])
for unique_id in amc.unique_id:
    req = requests.get(f'https://api.sec.or.th/FundFactsheet/fund/amc/{unique_id}', headers = headers)
    projects = pd.read_json(req.content)
    all_funds = all_funds.append(projects[['proj_id', 'proj_abbr_name','proj_name_en', 'proj_name_th','unique_id']])

print(f'There are in total {len(all_funds.index)} funds')
# Should be divided by 5 but allows for network inefficiencies
print(f'Estimate time to complete: {len(all_funds.index) / 4} seconds')

# Create a place to hold risk_spectrum
riskDF = pd.DataFrame(columns=['proj_id'])
# Just something to track the progress
count = 0
progressstep = 10
itr = 0

for proj_id in all_funds.proj_id:
    count += 1
    if(count > (itr*progressstep) * len(all_funds.index) / 100) :
        print(f'{itr*progressstep} % completed')
        print(f'Estimate time to complete: {len(all_funds.index - count) / 4} seconds')
        itr += 1

    if command_code == 12:
        res = limiter.call_get_api(url=f'https://api.sec.or.th/FundFactsheet/fund/{proj_id}/suitability')
        temp_data = json.loads(res.content)
        riskDF = riskDF.append([{'proj_id': proj_id, 'risk_spectrum': temp_data.get('risk_spectrum')}],
                               ignore_index=True)
    if command_code == 13:
        res = limiter.call_get_api(url=f'https://api.sec.or.th/FundFactsheet/fund/{proj_id}/risk')
        # read only not null
        if res.status_code == 200:
            items = json.loads(res.content)
            for item in items:
                riskDF = riskDF.append([{'proj_id': proj_id, 'group_code_desc': item.get('group_code_desc'), 'code_desc': item.get('code_desc'), 'last_upd_date': item.get('last_upd_date')}], ignore_index=True)
    if len(riskDF) > 100:
        break

all_funds = all_funds.merge(riskDF)
all_funds = all_funds.set_index('proj_id')
writer = ExcelWriter('AllRisk.xlsx')
all_funds.to_excel(writer,'FundFactsheet')
writer.save()