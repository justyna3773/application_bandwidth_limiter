import socket
import json
import subprocess
import sys
import os
import logging

from config_parser import load_config, app_dict_ip

HOST = '127.0.0.1'  # Nazwa lub adres IP serwera
PORT = 7150        # Port dla netifyd




def set_rule(options, src_ip):  # przyjmuje liste ustawionych opcji odpowiadajaca aplikacji w slowniku oraz adres IP wykryty przez netifyd

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
    print(command)  # TODO: REMOVE
    proc = subprocess.run(command, stdout=subprocess.PIPE,
                          stderr=sys.stderr, universal_newlines=True, shell=True)# wywolanie stworzonej komendy dla wrappera tcconfig


def remove_application_rule(interface, ip_addr):
    for addr in ip_addr:
        proc = subprocess.run(f'tcdel {interface} --src-network {addr}', stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, universal_newlines=True, shell=True)




def setup(name, intercepted):#funkcja setup przyjmuje nazwe pliku konfiguracyjnego i pliku z przechwyconymi adresami
    interfaces = ['eth0', 'br-lan']
    config_parser_dict = load_config(name) #ladowanie konfiguracji z pliku
    addr_dict = app_dict_ip(config_parser_dict)# stworzenie slownika na zaktualizowane (wszystkie) adresy IP
    inter_dict = {}  # slownik na adresy IP przechwycone do ip_intercepted
    for i in interfaces:
        proc = subprocess.run(f'tcdel {i} --all ', stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              universal_newlines=True, shell=True)
    # usuniecie wszystkich poprzednich zasad dla interfejsow
    if os.path.isfile(intercepted) and os.access(intercepted, os.R_OK):#jesli plik intercepted istnieje
        with open(intercepted, 'r') as jsonfile:#otwarcie pliku
            inter_dict = json.load(jsonfile)#zaladowanie poprzednich adresow do slownika
            inter_dict = {app: set(inter_dict[app]) for app in inter_dict}
            if inter_dict:  # jesli cos jest w tym slowniku to ustawiam te zasady ponownie
                for app, ips in inter_dict.items():  # teraz dla kazdej aplikacji musze uwzglednic config obecny
                    # teraz uwzgleniam pojedyncze ip'
                    for i in ips:
                        set_rule(config_parser_dict[app], i)#wywoluje komende tcconfig dla kazdego adresu ip z intercepted dla aplikacji
                for app in inter_dict:
                    if app in addr_dict:
                        inter_dict = {
                            app: list(inter_dict[app]) for app in inter_dict}
                        # wstawiam poprzednie adresy do obecnego slownika na adresy
                        addr_dict[app] = inter_dict[app]

    return config_parser_dict, addr_dict, inter_dict


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:#otwarcie gniazda UDP

        s.connect((HOST, PORT))
        config_parser_dict, addr_dict, inter_dict = setup(
            'config.ini', 'ip_intercepted.json') #wywolanie funkcji setup
        try:
            while True:

                lines = s.recv(1024000) #odebranie na gniezdzie duzej ilosci danych z netifyd

                for line in lines.decode().split('\n'):
                    if line != '':
                        data = json.loads(line)
                        if 'flow' in data:
                            print("interface:\n", data['interface'])
                            print("name:\n", data['flow']
                                  ['detected_application_name'])

                            addr = data['flow']['other_ip'] 
                #operacje majace na celu wyodrebnienie aplikacji i adresu ip
                            for application in config_parser_dict: #dla kazdej aplikacji w slowniku konfiguracji
                                if application in data['flow']['detected_application_name']:# jesli obecnie netifyd zidentyfikowalo aplikacje ze slownika
                                    if addr not in addr_dict[application]:#jesli obecnie przechwycony adres nie pojawil sie dotad dla tej aplikacji
                                        addr_dict[application].append(addr)#dolacz adres do slownika adresow pod kluczem odpowiedniej aplikacji
                                        set_rule(
                                            config_parser_dict[application], addr)#ustaw zasade zgodnie z parametrami ze slownika konfiguracji

                                        print(json.dumps(data, indent=2))

                            print("ip:\n", data['flow']['other_ip'])
        except KeyboardInterrupt:
            print("Intercepted addresses saved to file ip_intercepted.json")
        finally:

            with open('ip_intercepted.json', 'w') as jsonfile:

                addr_dict = {app: list(addr_dict[app]) for app in addr_dict}
                json.dump(addr_dict, jsonfile)
        #przechwycone adresy zostaja zapisane w pliku ip_intercepted.json niezaleznie od sposobu w jaki sposob zamknie sie skrypt

if __name__ == '__main__':
    main()
