import socket
import json
import subprocess
import sys
import os
import logging

from config_parser import load_config, app_dict_ip

HOST = '127.0.0.1'   # Nazwa lub adres IP serwera
PORT = 7150         # Port dla netifyd



def set_rule(options, src_ip):#przyjmuje liste ustawionych opcji odpowiadajaca aplikacji w slowniku oraz adres IP wykryty przez netifyd
    
    command = 'set_download '
    command += f'-d {options["dest_network"]} ' if 'dest_network' in options else ''
    command += f'-s {src_ip}/32 ' if src_ip else ''
    command += f'-r {options["max_bandwidth"]} ' if 'max_bandwidth' in options else ''
    command += f'-l {options["delay"]} ' if 'delay' in options else ''
    command += f'-m {options["loss"]} ' if 'loss' in options else ''
    command += f'-p {options["port"]} ' if 'port' in options else ''   
    print(command) 
    proc = subprocess.Popen(['bash','-c', 'source ./htb_script.sh;' + command],stdout=subprocess.PIPE, stderr=subprocess.PIPE)# wywolanie stworzonej komendy dla skryptu htb_script.sh



def remove_application_rule(interface, ip_addr, rate):
    for addr in ip_addr:
        proc = subprocess.Popen(f'tcdel {interface} --src-network {addr}',stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, shell=True)
        



def setup(name, intercepted):#funkcja setup przyjmuje nazwe pliku konfiguracyjnego i pliku z przechwyconymi adresami
    config_parser_dict = load_config(name)
    addr_dict = app_dict_ip(config_parser_dict)# stworzenie slownika na zaktualizowane (wszystkie) adresy IP
    inter_dict = {}# slownik na adresy IP przechwycone do ip_intercepted
    
    subprocess.Popen(['bash', '-c', 'source ./htb_script.sh; remove_download; htb_init'])
    # usuniecie wszystkich poprzednich zasad dla interfejsu
    if os.path.isfile(intercepted) and os.access(intercepted, os.R_OK):#jesli plik intercepted istnieje
        with open(intercepted,'r') as jsonfile:#otwarcie pliku
            inter_dict = json.load(jsonfile)#zaladowanie poprzednich adresow do slownika
            inter_dict = {app: set(inter_dict[app]) for app in inter_dict}
            if inter_dict:   #jesli cos jest w tym slowniku to ustawiam te zasady ponownie     
                for app,ips in inter_dict.items():#teraz dla kazdej aplikacji musze uwzglednic config obecny
                    #teraz uwzgleniam pojedyncze ip dla aplikacji
                    for i in ips:
                        set_rule(config_parser_dict[app], i)#wywoluje funkcje skryptu htb_script dla kazdego adresu ip dla aplikacji
                for app in inter_dict:
                    if app in addr_dict:
                        inter_dict = {app: list(inter_dict[app]) for app in inter_dict}
                        addr_dict[app] = inter_dict[app]    #wstawiam poprzednie adresy do obecnego slownika na adresy
            
    return config_parser_dict, addr_dict, inter_dict       

         
    
    
        

    


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:#otwarcie gniazda UDP
        
        s.connect((HOST, PORT))
        config_parser_dict, addr_dict, inter_dict = setup('config.ini','ip_intercepted.json')#wywolanie funkcji setup
        try:
            while True: 
                
                
                lines = s.recv(1024000) #odebranie na gniezdzie duzej ilosci danych z netifyd

                
                
                
                for line in lines.decode().split('\n'):
                    if line != '':
                        data = json.loads(line)#tworzenie slownika z danych w jsonie
                        if 'flow' in data:
                            print("interface:\n", data['interface'])
                            print("name:\n", data['flow']['detected_application_name'])
                            
                                
                            addr = data['flow']['other_ip']
                #operacje majace na celu wyodrebnienie aplikacji i adresu ip
                            for application in config_parser_dict:#dla kazdej aplikacji w slowniku konfiguracji
                                if application in data['flow']['detected_application_name']:# jesli obecnie netifyd zidentyfikowalo aplikacje ze slownika
                                    if addr not in addr_dict[application]:#jesli obecnie przechwycony adres nie pojawil sie dotad dla tej aplikacji
                                        addr_dict[application].append(addr)#dolacz adres do slownika adresow pod kluczem odpowiedniej aplikacji
                                        set_rule(config_parser_dict[application],addr)#ustaw zasade zgodnie z parametrami ze slownika konfiguracji
                                        print(json.dumps(data, indent=2))

                                        

                                            
                        
                            print("ip:\n", data['flow']['other_ip'])
        except KeyboardInterrupt:
            print("Intercepted addresses saved to file ip_intercepted.json")
        finally:

            with open('ip_intercepted.json','w') as jsonfile:

                addr_dict = {app: list(addr_dict[app]) for app in addr_dict}
                json.dump(addr_dict, jsonfile)
 #przechwycone adresy zostaja zapisane w pliku ip_intercepted.json niezaleznie od sposobu w jaki sposob zamknie sie skrypt
            
           
                        
if __name__ == '__main__':
    main()
