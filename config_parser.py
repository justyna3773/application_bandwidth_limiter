import configparser
#should check integrity of config

def load_config(name):

    config = configparser.ConfigParser()
    config.read(name)
    config_parser_dict = {s:dict(config.items(s)) for s in config.sections()}
    return config_parser_dict


def app_dict_ip(config_parser_dict):
    apps = config_parser_dict.keys()
    app_dict = dict.fromkeys(apps)
    for app in app_dict:
        app_dict[app] = []
    return app_dict

config_parser_dict = load_config('config.ini')
apps = app_dict_ip(config_parser_dict)
print(apps)