import socket
import json
import subprocess
import sys
import os
import logging

from config_parser import load_config, app_dict_ip

HOST = '127.0.0.1'  # The server's hostname or IP address
PORT = 7150        # The port used by the server



def set_rule(options, src_ip):#przyjmuje liste ustawionych opcji odpowiadajaca aplikacji w slowniku
    
    command = 'set_download '
    command += f'-d {options["dest_network"]} ' if 'dest_network' in options else ''
    command += f'-s {src_ip}/32 ' if src_ip else ''
    command += f'-r {options["max_bandwidth"]} ' if 'max_bandwidth' in options else ''
    command += f'-l {options["delay"]} ' if 'delay' in options else ''
    command += f'-m {options["loss"]} ' if 'loss' in options else ''
    command += f'-p {options["port"]} ' if 'port' in options else ''   
    print(command) 
    proc = subprocess.Popen(['bash','-c', 'source ./htb_script.sh;' + command],stdout=subprocess.PIPE, stderr=subprocess.PIPE)



def remove_application_rule(interface, ip_addr, rate):
    for addr in ip_addr:
        proc = subprocess.Popen(f'tcdel {interface} --src-network {addr}',stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, shell=True)
        


def modify_rule(interface, addr, rate):
    get_current_rules = subprocess.run(f'tcshow {interface}', stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, shell=True)

    current_rules_addresses = []
    rules_dict = json.loads(get_current_rules.stdout)
    if interface in rules_dict:
        for key in rules_dict["br-lan"]["outgoing"]:
            address = key[key.find('=')+1:key.find('/')]
            current_rules_addresses.append(address)
            if addr in current_rules_addresses:
                modified_rule = subprocess.run(f'tcset {interface} --rate {rate}Kbps --src-network {address} --overwrite',stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, shell=True)
            else:
                new_rule = subprocess.run(f'tcset {interface} --rate {rate}Kbps --src-network {addr} --add',stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, shell=True)


def setup(name, intercepted):
    #interfaces = ['eth0', 'br-lan']
    config_parser_dict = load_config(name)
    addr_dict = app_dict_ip(config_parser_dict)
    inter_dict = {}#miejsce na nowe adresy wg aktualnego pliku config
    
    subprocess.Popen(['bash', '-c', 'source ./htb_script.sh; remove_download; htb_init'])
    
    # usunieto poprzednie tc configi
    if os.path.isfile(intercepted) and os.access(intercepted, os.R_OK):
        with open(intercepted,'r') as jsonfile:
            inter_dict = json.load(jsonfile)
            inter_dict = {app: set(inter_dict[app]) for app in inter_dict}
            if inter_dict:   #jesli cos jest w tym slowniku to ustawiam te zasady ponownie     
                for app,ips in inter_dict.items():#teraz dla kazdej aplikacji musze uwzglednic config obecny
                    #teraz uwzgleniam pojedyncze ip'
                    for i in ips:
                        set_rule(config_parser_dict[app], i)
                for app in inter_dict:
                    if app in addr_dict:
                        inter_dict = {app: list(inter_dict[app]) for app in inter_dict}
                        addr_dict[app] = inter_dict[app]    #wstawiam poprzednie adresy do obecnego slownika na adresy
            
    return config_parser_dict, addr_dict, inter_dict       

         
    
    
        

    


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        
        s.connect((HOST, PORT))
        config_parser_dict, addr_dict, inter_dict = setup('config.ini','ip_intercepted.json')
        try:
            while True: 
                
                
                lines = s.recv(1024000)
                
                
                
                for line in lines.decode().split('\n'):
                    if line != '':
                        data = json.loads(line)#TWORZY SLOWNIK Z DANYCH W JSONIE
                        if 'flow' in data:
                            print("interface:\n", data['interface'])
                            print("name:\n", data['flow']['detected_application_name'])
                            
                                
                            addr = data['flow']['other_ip']
                                #ip_ver = data['flow']['ip_version']
                            for application in config_parser_dict:
                                if application in data['flow']['detected_application_name']:
                                    if addr not in addr_dict[application]:
                                        addr_dict[application].append(addr)
                                        set_rule(config_parser_dict[application],addr)
                                        #print (addr_list)
                                        print(json.dumps(data, indent=2))
                                        #f.write(addr + '\n')
                                        

                                            
                        
                            print("ip:\n", data['flow']['other_ip'])
        except KeyboardInterrupt:
            print("Intercepted addresses saved to file ip_intercepted.json")
        finally:

            with open('ip_intercepted.json','w') as jsonfile:

                addr_dict = {app: list(addr_dict[app]) for app in addr_dict}
                json.dump(addr_dict, jsonfile)

            
           
                        
if __name__ == '__main__':
    main()
