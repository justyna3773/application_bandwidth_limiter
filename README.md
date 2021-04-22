The scripts require python 3.8.0 and pip to work, also package Netifyd is required. Also, FriendlyWrt should be installed on your device.
Prerequisites for tc command to work are:
iproute2/iproute-tc
## Netifyd installation
Netifyd is crucial to detect applications such as YouTube.
To install package Netifyd with opkg run following commands:
```bash
opkg update
opkg install netifyd
opkg install jq
```
To start netifyd run:
```bash
service netifyd restart
```

## Tcconfig installation
Tcconfig is a command wrapper required to run applications_tcconfig.py, you can install it using commands:
```bash
sudo pip install tcconfig
```
## Usage
You can configure applications' parameters in the config.ini file. Then you can run applications_tcconfig.py to limit configured parameters for connection with chosen applications such as YouTube, Netflix etc. Tcconfig is more reliable, since it has a community of users and has been present for some time.
You can also run tcconfig on its own to cofigure parameters for an entire interface or a subnet for example. For tcconfig usage refer to: https://tcconfig.readthedocs.io/en/latest/pages/usage/index.html

You can also use file applications_htb_script.py which uses a simpler implementation of HTB and tc command in Bash to limit configured applications. 
You can use htb_script.sh functions from command line, but first you have to type:
```bash
source ./htb_script.sh
```
The script assumes your inner interface name is 'br-lan', but you can set it to the your interface's name by running command:
```bash
set_interface NAME
```
To remove qdiscs for download run: 
```bash 
remove_download
```
which removes all qdiscs attached to root. 
To remove qdiscs for upload run: 
```bash
remove_upload
```
To add a new rule for download/upload run:
```bash
set_download -d DEST_ADDRESS/MASK -s SOURCE_ADDRESS/MASK -p DEST_PORT -o SRC_PORT -l PACKET_LOSS[%] -m DELAY[ms] -r RATE[mbit or kbit]
set_upload -d DEST_ADDRESS/MASK -s SOURCE_ADDRESS/MASK -p DEST_PORT -o SRC_PORT -l PACKET_LOSS[%] -m DELAY[ms] -r RATE[mbit or kbit]
```
You can add multiple rules as long as they don't overlap with each other in terms of ports and addresses. If something goes wrong you can remove them.
