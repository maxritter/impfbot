import platform
import telegram
import sys
import logging
from logging import Formatter
from logging.handlers import SysLogHandler
from src import helios, doctolib

# Global variables
api_timeout_seconds = 5
already_sent_ids = None
telegram_bot = None
logger = None
conf = {'muc1': {'token': '1851471777:AAHqNrWPAuvr7w5QRrjrnGvr0VJaWVC4BCo', 'chat_id': -1001464001536, 'lat': 48.13836, 'lng': 11.57939, 'address': '80333 Muenchen Altstadt-Lehel'},
        'muc2': {'token': '1851471777:AAHqNrWPAuvr7w5QRrjrnGvr0VJaWVC4BCo', 'chat_id': -1001464001536, 'lat': -1, 'lng': -1, 'address': ''},
        'muc3': {'token': '1851471777:AAHqNrWPAuvr7w5QRrjrnGvr0VJaWVC4BCo', 'chat_id': -1001464001536, 'lat': -1, 'lng': -1, 'address': ''},
        'nue': {'token': '1707020702:AAGxjS0uE02HZOyhR8mnvatInjF-Eybsl5w', 'chat_id': -1001159218767, 'lat': 49.4514, 'lng': 11.07471, 'address': '90402 Nuernberg Lorenz'},
        'str': {'token': '1873380443:AAF1PGcSX_Nm5X9_DeXoUvnuvGB53SJ8Kng', 'chat_id': -1001315735957, 'lat': 48.7767, 'lng': 9.18015, 'address': '70173 Stuttgart Mitte'},
        'agb': {'token': '1894787285:AAHxOYeit6cbW8qMamCkyVFdqHADSzXqTvA', 'chat_id': -1001432733051, 'lat': 48.36989, 'lng': 10.90017, 'address': '86150 Augsburg Innenstadt'},
        'cgn': {'token': '1785486821:AAEYmYGc4s8rBQI_Bp9Iunei7uhsyNXG5ak', 'chat_id': -1001439806320, 'lat': 50.93893, 'lng': 6.95752, 'address': '50667 Koeln Altstadt-Nord'},
        'dus': {'token': '1777569089:AAGDKiCGlaGw1pvolsWJQFUAO-Qyqb2Pk-M', 'chat_id': -1001441637885, 'lat': 51.22591, 'lng': 6.77356, 'address': '40213 Duesseldorf Altstadt'},
        'ber1': {'token': '1856093227:AAH57uMO_Fc3-ujR53PRsc0sGTfj_HcOp5E', 'chat_id': -1001311147212, 'lat': 52.52003, 'lng': 13.40489, 'address': '10178 Berlin Mitte'},
        'ber2': {'token': '1856093227:AAH57uMO_Fc3-ujR53PRsc0sGTfj_HcOp5E', 'chat_id': -1001311147212, 'lat': -1, 'lng': -1, 'address': ''},
        'ber3': {'token': '1856093227:AAH57uMO_Fc3-ujR53PRsc0sGTfj_HcOp5E', 'chat_id': -1001311147212, 'lat': -1, 'lng': -1, 'address': ''},
        'ffm': {'token': '1871460580:AAFBH3JpoI_yT26KIbXstgxIqgGAmI_5ykg', 'chat_id': -1001238323633, 'lat': 50.1126, 'lng': 8.68343, 'address': '60311 Frankfurt am Main Innenstadt'},
        'hh': {'token': '1825855360:AAGDroNCjzRmO_L_e9swc0Z6hCS3saHA7S8', 'chat_id': -1001237010945, 'lat': 53.55, 'lng': 10, 'address': '20457 Hamburg Hamburg-Altstadt'},
        'lej': {'token': '1612112501:AAHmdIhJG3CWz5nGdCu8jeBJpiP_y5MsgsI', 'chat_id': -1001487955448, 'lat': 51.33983, 'lng': 12.37541, 'address': '04109 Leipzig Zentrum'},
        'bre': {'token': '1837180023:AAFYz36fPgS272cRCLWym_32pA3BMmZClpo', 'chat_id': -1001224145181, 'lat': 53.0778, 'lng': 8.80385, 'address': '28195 Bremen Altstadt'},
        'h': {'token': '1860188851:AAGhHF8nl0XAwqAjOGmQQp-T4JWTnX8zDq0', 'chat_id': -1001486720744, 'lat': 52.37387, 'lng': 9.73779, 'address': '30161 Hannover Mitte'},
        'drs': {'token': '1817383072:AAHUNQaWQcmqPXyFIJyx-SkWIJB6iWetWT0', 'chat_id': -1001165597953, 'lat': 51.05174, 'lng': 13.73729, 'address': '01067 Dresden Innere Altstadt'},
        'fr': {'token': '', 'chat_id': -1001436511356, 'lat': 47.9953, 'lng': 7.85242, 'address': '79098 Freiburg im Breisgau Altstadt'},
        'erf': {'token': '', 'chat_id': -1001183027974, 'lat': 50.97961, 'lng': 11.02388, 'address': '99084 Erfurt Altstadt'},
        'wue': {'token': '', 'chat_id': -1, 'lat': 49.79471, 'lng': 9.93163, 'address': '97070 Wuerzburg Altstadt'},
        'md': {'token': '', 'chat_id': -1, 'lat': 52.1277, 'lng': 11.63815, 'address': '39104 Magdeburg Altstadt'},
        'dtm': {'token': '1819882627:AAFhuzPIz_GikhEwMO9jMuyF7tdKcyi6I_8', 'chat_id': -1001168900922, 'lat': 51.51422, 'lng': 7.46509, 'address': '44137 Dortmund Mitte'},
        'ess': {'token': '1754321830:AAHDjPXowmJdzmvYuwnqrltTXK2b0sR-z0E', 'chat_id': -1001398889913, 'lat': 51.4564, 'lng': 7.00999, 'address': '45127 Essen Innenstadt'},
        'bs': {'token': '', 'chat_id': -1, 'lat': 52.26382, 'lng': 10.52242, 'address': '38100 Braunschweig Innenstadt'}
        }


def is_local():
    if 'WSL2' in platform.platform():
        return True
    return False


def error_handler(type, value, tb):
    logger.exception('Uncaught exception: {0}'.format(str(value)))


def init_logger(city):
    global logger

    log_format = f'[%(levelname)s] [{city.upper()}] %(message)s'

    logger = logging.getLogger(city)
    logger.propagate = False
    logger.setLevel(logging.INFO)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(Formatter(log_format))
    logger.addHandler(console_handler)

    # For cluster monitoring, use papertrail.com that also alerts on errors
    if not is_local():
        papertrail_handler = SysLogHandler(
            address=("logs2.papertrailapp.com", 51309))
        papertrail_handler.setLevel(logging.INFO)
        papertrail_handler.setFormatter(Formatter(log_format))
        logger.addHandler(papertrail_handler)

    sys.excepthook = error_handler


def info_log(msg):
    logger.info(msg)


def warn_log(msg):
    logger.warning(msg)


def error_log(msg):
    logger.error(msg)


def is_telegram_enabled(city):
    return (conf[city]['token'] != '' and conf[city]['chat_id'] != -1 and not is_local())


def is_helios_enabled(city):
    return (conf[city]['lat'] != -1 and conf[city]['lng'] != -1 and conf[city]['address'] != '')


def send_telegram_msg(city, msg):
    global telegram_bot

    if is_telegram_enabled(city):
        telegram_bot.sendMessage(chat_id=conf[city]['chat_id'], text=msg)


def init(city):
    global telegram_bot, already_sent_ids, conf

    # General inits
    already_sent_ids = []
    init_logger(city)
    info_log('Init Impfbot..')
    if is_telegram_enabled(city):
        telegram_bot = telegram.Bot(token=conf[city]['token'])
    
    # Init Doctolib
    doctolib.doctolib_init(city)

    # Try to init Helios API
    if is_helios_enabled(city):
        helios.helios_init(city)
