import platform
import telegram
import sys
import os
import datetime
import logging
from logging import Formatter
from logging.handlers import SysLogHandler
from src import helios, doctolib

# Global variables
api_timeout_seconds = 10
already_sent_ids = None
telegram_bot = None
logger = None
conf = {'muc1': {'all_id': -1001464001536, 'mrna_id': -1001126966895, 'vec_id': -1001161931395, 'lat': 48.13836, 'lng': 11.57939, 'address': '80333 Muenchen Altstadt-Lehel'},
        'muc2': {'all_id': -1001464001536, 'mrna_id': -1001126966895, 'vec_id': -1001161931395, 'lat': -1, 'lng': -1, 'address': ''},
        'muc3': {'all_id': -1001464001536, 'mrna_id': -1001126966895, 'vec_id': -1001161931395, 'lat': -1, 'lng': -1, 'address': ''},
        'muc4': {'all_id': -1001464001536, 'mrna_id': -1001126966895, 'vec_id': -1001161931395, 'lat': -1, 'lng': -1, 'address': ''},
        'nue': {'all_id': -1001159218767, 'mrna_id': -1, 'vec_id': -1, 'lat': 49.4514, 'lng': 11.07471, 'address': '90402 Nuernberg Lorenz'},
        'str': {'all_id': -1001315735957, 'mrna_id': -1, 'vec_id': -1, 'lat': 48.7767, 'lng': 9.18015, 'address': '70173 Stuttgart Mitte'},
        'agb': {'all_id': -1001432733051, 'mrna_id': -1, 'vec_id': -1, 'lat': 48.36989, 'lng': 10.90017, 'address': '86150 Augsburg Innenstadt'},
        'cgn': {'all_id': -1001439806320, 'mrna_id': -403657350, 'vec_id': -475689537, 'lat': 50.93893, 'lng': 6.95752, 'address': '50667 Koeln Altstadt-Nord'},
        'dus': {'all_id': -1001441637885, 'mrna_id': -1, 'vec_id': -1, 'lat': 51.22591, 'lng': 6.77356, 'address': '40213 Duesseldorf Altstadt'},
        'ber1': {'all_id': -1001311147212, 'mrna_id': -543462022, 'vec_id': -439688085, 'lat': 52.52003, 'lng': 13.40489, 'address': '10178 Berlin Mitte'},
        'ber2': {'all_id': -1001311147212, 'mrna_id': -543462022, 'vec_id': -439688085, 'lat': -1, 'lng': -1, 'address': ''},
        'ber3': {'all_id': -1001311147212, 'mrna_id': -543462022, 'vec_id': -439688085, 'lat': -1, 'lng': -1, 'address': ''},
        'ffm': {'all_id': -1001238323633, 'mrna_id': -1, 'vec_id': -1, 'lat': 50.1126, 'lng': 8.68343, 'address': '60311 Frankfurt am Main Innenstadt'},
        'hh': {'all_id': -1001237010945, 'mrna_id': -502853530, 'vec_id': -512029942, 'lat': 53.55, 'lng': 10, 'address': '20457 Hamburg Hamburg-Altstadt'},
        'lej': {'all_id': -1001487955448, 'mrna_id': -1, 'vec_id': -1, 'lat': 51.33983, 'lng': 12.37541, 'address': '04109 Leipzig Zentrum'},
        'bre': {'all_id': -1001224145181, 'mrna_id': -1, 'vec_id': -1, 'lat': 53.0778, 'lng': 8.80385, 'address': '28195 Bremen Altstadt'},
        'h': {'all_id': -1001486720744, 'mrna_id': -1, 'vec_id': -1, 'lat': 52.37387, 'lng': 9.73779, 'address': '30161 Hannover Mitte'},
        'drs': {'all_id': -1001165597953, 'mrna_id': -1, 'vec_id': -1, 'lat': 51.05174, 'lng': 13.73729, 'address': '01067 Dresden Innere Altstadt'},
        'fr': {'all_id': -1001436511356, 'mrna_id': -1, 'vec_id': -1, 'lat': 47.9953, 'lng': 7.85242, 'address': '79098 Freiburg im Breisgau Altstadt'},
        'erf': {'all_id': -1001183027974, 'mrna_id': -1, 'vec_id': -1, 'lat': 50.97961, 'lng': 11.02388, 'address': '99084 Erfurt Altstadt'},
        'wue': {'all_id': -1001410779884, 'mrna_id': -1, 'vec_id': -1, 'lat': 49.79471, 'lng': 9.93163, 'address': '97070 Wuerzburg Altstadt'},
        'md': {'all_id': -1001183191239, 'mrna_id': -1, 'vec_id': -1, 'lat': 52.1277, 'lng': 11.63815, 'address': '39104 Magdeburg Altstadt'},
        'dtm': {'all_id': -1001168900922, 'mrna_id': -1, 'vec_id': -1, 'lat': 51.51422, 'lng': 7.46509, 'address': '44137 Dortmund Mitte'},
        'ess': {'all_id': -1001398889913, 'mrna_id': -1, 'vec_id': -1, 'lat': 51.4564, 'lng': 7.00999, 'address': '45127 Essen Innenstadt'},
        'bs': {'all_id': -1001333251690, 'mrna_id': -1, 'vec_id': -1, 'lat': 52.26382, 'lng': 10.52242, 'address': '38100 Braunschweig Innenstadt'}
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


def is_helios_enabled(city):
    return (conf[city]['lat'] != -1 and conf[city]['lng'] != -1 and conf[city]['address'] != '')


def send_telegram_msg(city, type, msg):
    global telegram_bot

    channel_id = conf[city][f'{type}_id']
    if not is_local() and channel_id is not None and channel_id != -1:
        telegram_bot.sendMessage(chat_id=channel_id, text=msg)


def init(city):
    global telegram_bot, already_sent_ids, conf

    # For local env, load secrets from file
    if is_local():
        from dotenv import load_dotenv
        load_dotenv(verbose=True)

    # General inits
    already_sent_ids = []
    init_logger(city)
    info_log('Init Impfbot..')
    telegram_bot = telegram.Bot(token=os.getenv('TELEGRAM_TOKEN'))

    # Init Doctolib
    doctolib.doctolib_init(city)

    # Try to init Helios API
    if is_helios_enabled(city):
        helios.helios_init(city)
