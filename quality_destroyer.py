# function shou;d take the quality as the parameter 
import subprocess
import sys
import os
#def init_func():
    
def quality_degrade(quality):
    subprocess.Popen(['bash', '-c', 'source ./h.sh; remove_qdiscs; htb_init'])
    #init_func()
    qualities = {"240p FLV": 40960, "360p MP4": 94208, "720p MP4": 408576, "360p FLV": 118784, "480p FLV": 163840, "1080p MP4": 792576, "360p WebM": 118784, "480p WebM": 163840, "1080p WebM": "n/a" }
    bandwidth_required = qualities[quality]/100
    command = 'set_download -d 192.168.2.0/24 -r ' + str(bandwidth_required) + 'kbit'
    print (command)
    proc = subprocess.Popen(['bash','-c', 'source ./h.sh;' + command],stdout=subprocess.PIPE, stderr=subprocess.PIPE)


