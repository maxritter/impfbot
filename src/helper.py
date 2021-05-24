import platform
import telegram
from src import helios, doctolib

# Global variables
already_sent_ids = None
telegram_bot = None
conf = {'muc1': {'token': '1851471777:AAHqNrWPAuvr7w5QRrjrnGvr0VJaWVC4BCo', 'chat_id': -1001464001536, 'lat': 48.13836, 'lon': 11.57939, 'address': '80333 Muenchen Altstadt-Lehel'},
        'muc2': {'token': '1851471777:AAHqNrWPAuvr7w5QRrjrnGvr0VJaWVC4BCo', 'chat_id': -1001464001536},
        'muc3': {'token': '1851471777:AAHqNrWPAuvr7w5QRrjrnGvr0VJaWVC4BCo', 'chat_id': -1001464001536},
        'nue': {'token': '1707020702:AAGxjS0uE02HZOyhR8mnvatInjF-Eybsl5w', 'chat_id': -1001159218767, 'lat': 49.4514, 'lon': 11.07471, 'address': '90402 Nuernberg Lorenz'},
        'str': {'token': '1873380443:AAF1PGcSX_Nm5X9_DeXoUvnuvGB53SJ8Kng', 'chat_id': -1001315735957, 'lat': 48.7767, 'lon': 9.18015, 'address': '70173 Stuttgart Mitte'},
        'agb': {'token': '1894787285:AAHxOYeit6cbW8qMamCkyVFdqHADSzXqTvA', 'chat_id': -1001432733051, 'lat': 48.36989, 'lon': 10.90017, 'address': '86150 Augsburg Innenstadt'},
        'cgn': {'token': '1785486821:AAEYmYGc4s8rBQI_Bp9Iunei7uhsyNXG5ak', 'chat_id': -1001439806320, 'lat': 50.93893, 'lon': 6.95752, 'address': '50667 Koeln Altstadt-Nord'},
        'dus': {'token': '1777569089:AAGDKiCGlaGw1pvolsWJQFUAO-Qyqb2Pk-M', 'chat_id': -1001441637885, 'lat': 51.22591, 'lon': 6.77356, 'address': '40213 Duesseldorf Altstadt'},
        'ber1': {'token': '1856093227:AAH57uMO_Fc3-ujR53PRsc0sGTfj_HcOp5E', 'chat_id': -1001311147212, 'lat': 52.52003, 'lon': 13.40489, 'address': '10178 Berlin Mitte'},
        'ber2': {'token': '1856093227:AAH57uMO_Fc3-ujR53PRsc0sGTfj_HcOp5E', 'chat_id': -1001311147212},
        'ber3': {'token': '1856093227:AAH57uMO_Fc3-ujR53PRsc0sGTfj_HcOp5E', 'chat_id': -1001311147212},
        'ffm': {'token': '1871460580:AAFBH3JpoI_yT26KIbXstgxIqgGAmI_5ykg', 'chat_id': -1001238323633, 'lat': 50.1126, 'lon': 8.68343, 'address': '60311 Frankfurt am Main Innenstadt'},
        'hh': {'token': '1825855360:AAGDroNCjzRmO_L_e9swc0Z6hCS3saHA7S8', 'chat_id': -1001237010945, 'lat': 53.55, 'lon': 10, 'address': '20457 Hamburg Hamburg-Altstadt'},
        'lej': {'token': '', 'chat_id': -1, 'lat': 51.33983, 'lon': 12.37541, 'address': '04109 Leipzig Zentrum'},
        'bre': {'token': '', 'chat_id': -1, 'lat': 53.0778, 'lon': 8.80385, 'address': '28195 Bremen Altstadt'},
        'h': {'token': '', 'chat_id': -1, 'lat': 52.37387, 'lon': 9.73779, 'address': '30161 Hannover Mitte'},
        'h': {'token': '', 'chat_id': -1, 'lat': 51.05174, 'lon': 13.73729, 'address': '01067 Dresden Innere Altstadt'},
        'fr': {'token': '', 'chat_id': -1, 'lat': 47.9953, 'lon': 7.85242, 'address': '79098 Freiburg im Breisgau Altstadt'},
        'erf': {'token': '', 'chat_id': -1, 'lat': 50.97961, 'lon': 11.02388, 'address': '99084 Erfurt Altstadt'},
        'wue': {'token': '', 'chat_id': -1, 'lat': 49.79471, 'lon': 9.93163, 'address': '97070 Würzburg Altstadt'},
        'wue': {'token': '', 'chat_id': -1, 'lat': 49.79471, 'lon': 9.93163, 'address': '97070 Würzburg Altstadt'},
        'md': {'token': '', 'chat_id': -1, 'lat': 52.1277, 'lon': 11.63815, 'address': '39104 Magdeburg Altstadt'}
        }


def is_local():
    if 'WSL2' in platform.platform():
        return True
    return False


def is_telegram_enabled(city):
    return (conf[city]['token'] != '' and conf[city]['chat_id'] != -1 and not is_local())


def is_helios_enabled(city):
    return (conf[city]['lat'] and conf[city]['lon'] and conf[city]['address'])


def send_telegram_msg(city, msg):
    global telegram_bot

    if is_telegram_enabled(city):
        telegram_bot.sendMessage(chat_id=conf[city]['chat_id'], text=msg)


def init(city):
    global telegram_bot, already_sent_ids, conf

    if is_telegram_enabled(city):
        telegram_bot = telegram.Bot(token=conf[city]['token'])
    already_sent_ids = []

    doctolib.doctolib_init(city)

    if is_helios_enabled(city):
        helios.helios_init()
        while True:
            if helios.helios_gather_locations(city, conf[city]['lat'], conf[city]['lon'], conf[city]['address']):
                break
            print(f'{city}: ERROR - Unable to gather Helios location, try again..')
