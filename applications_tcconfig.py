import socket
import json
import subprocess
import sys
import csv
import os
import logging

from config_parser import load_config, app_dict_ip

HOST = '127.0.0.1'  # The server's hostname or IP address
PORT = 7150        # The port used by the server

#config_parser_dict = load_config('ex_config.ini')

def set_rule(options, src_ip):#przyjmuje liste ustawionych opcji odpowiadajaca aplikacji w slowniku
    
    command = 'tcset '
    command += f'{options["interface"]} '
    command += f'--rate {options["max_bandwidth"]} ' if 'max_bandwidth' in options else ''
    command += f'--direction {options["direction"]} ' if 'direction' in options else ''
    command += f'--src-network {src_ip} ' if src_ip else ''
    command += f'--dst-network {options["dest_network"]} ' if 'dest_network' in options else ''
    command += f'--delay {options["delay"]} ' if 'delay' in options else ''
    command += f'--loss {options["loss"]} ' if 'loss' in options else ''
    command += f'--port {options["port"]} ' if 'port' in options else ''
    command += f'--add'    
    print(command) # TODO: REMOVE
    proc = subprocess.run(command,stdout=subprocess.PIPE, stderr=sys.stderr, universal_newlines=True, shell=True)


def remove_application_rule(interface, ip_addr, rate):
    for addr in ip_addr:
        proc = subprocess.run(f'tcdel {interface} --src-network {addr}',stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, shell=True)
        


def modify_rule(interface, addr, rate):
    get_current_rules = subprocess.run(f'tcshow {interface}', stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, shell=True)
    #print(get_current_rules.stdout)
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

#addr_dict = {'youtube':[], 'netflix':[]}

#application_rate = list_of_dict[0][1] #dictionary with rates for an application

#application_dict ={'youtube': 100, 'netflix': 100} #list with applications to limit, but it should be a dictionary 
#create files to hold identified addresses
#application_dict = sys.argv[1]
# def address_file_application(name):
#     with open('.'.join(name, 'txt'),"a") as f:
#         return 0
def setup(name, intercepted):
    interfaces = ['eth0', 'br-lan']#nazwa pliku config i pliku z przechwyconymi ip
    config_parser_dict = load_config(name)
    addr_dict = app_dict_ip(config_parser_dict)
    inter_dict = {}#miejsce na nowe adresy wg aktualnego pliku config
    # inter_before = {}
    for i in interfaces:   
        proc = subprocess.run(f'tcdel {i} --all ',stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True, shell=True)
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
        config_parser_dict, addr_dict, inter_dict = setup('ex_config.ini','ip_intercepted.json')
        try:
            while True: 
                
                
                lines = s.recv(1024000)
                
                
                #with open('.'.join((application, 'txt')), "a") as f:
                #otwieranie pliku przechowujacego wszystkie znane adresy dla danej aplikacji
                for line in lines.decode().split('\n'):
                    if line != '':
                        data = json.loads(line)#TWORZY SLOWNIK PYTH Z DANYCH W JSONIE
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
            print("why'd you interrupt me")
        finally:

            with open('ip_intercepted.json','w') as jsonfile:

                addr_dict = {app: list(addr_dict[app]) for app in addr_dict}
                json.dump(addr_dict, jsonfile)

            
            # with open('ip_intercepted.csv', newline = '') as csvfile:
            #     ipreader = csv.reader(csvfile, delimiter = ' ', quotechar='|')
            #     for row in ipreader:
            #         existing_ip_addresses[row[0]] = row[1:]
            
            # with open ('ip_intercepted.csv', 'a', newline = '') as csvfile:
            #     ipwriter = csv.writer(csvfile, delimiter=' ',
            #                     quotechar='|', quoting=csv.QUOTE_MINIMAL)
            #     for application,address in addr_dict.items():
        
            #             if addr not in existing_ip_addresses[application]:
            #                 ipwriter.writerow([application, ','.join(address)])


            
            #zczytanie obecnych juz danych do tablicy
            # with open('.'.join((application,'txt')), 'r') as r:
            #     lines = r.readlines()
            #     for line in lines:
            #         existing_ip_addresses.append(line.rstrip('\n'))

            # for application in config_parser_dict:
            #     with open('.'.join((application, 'txt')), "a") as f:
                    
            #         for addr in addr_dict[application]:
            #                 if addr not in existing_ip_addresses:
            #                     f.write(addr + '\n')
                    
                        #sprawdzac czy taki adres juz istnieje 
                        
if __name__ == '__main__':
    main()
