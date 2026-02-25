import subprocess
import urllib.parse
import json
import time

import http_send

ip='127.0.0.1'
#ip='192.168.2.107'
agentdata_url='http://'+ip+':18087/AgentData'
patterndata_url='http://'+ip+':18087/RuntimeData'
doe_url='http://'+ip+':18087/ExperimentConfig'
doc_url='http://'+ip+':18087/DoctrinesConfig'
cmd_url='http://'+ip+':18087/PoiCmd'

formations_url='http://'+ip+':18087/FormationsData'

def exe_cmd_post(url, filepath):
    file_contents = http_send.loaddata_json(filepath)    
    #print(file_contents)
    return http_send.exe_request_post(url,file_contents)

#http_send.exe_request_get('http://127.0.0.1:18087/getRunningSpeed')
exe_cmd_post(agentdata_url,'./contents/agentdata_df.json')
exe_cmd_post(agentdata_url,'./contents/agentdata_sm3.json')
exe_cmd_post(agentdata_url,'./contents/agentdata_yjj.json')
exe_cmd_post(patterndata_url,'./contents/patterndata_df.json')
exe_cmd_post(patterndata_url,'./contents/patterndata_qzj.json')
exe_cmd_post(patterndata_url,'./contents/patterndata_yjj.json')
exe_cmd_post(doc_url,'./contents/doc.json')
exe_cmd_post(doe_url,'./contents/ExperimentConfig.json')

# print("暂停5秒后继续执行...")

# time.sleep(5)  # 暂停5秒


