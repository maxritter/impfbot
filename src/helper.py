import platform
from requests.sessions import Session
import telegram
import random
import time
import sys
import os
import csv
import urllib.request
from dotenv import load_dotenv
import datetime
import pytz
import logging
from logging import Formatter
from logging.handlers import SysLogHandler
from src import helios, doctolib, jameda

# Global variables
api_timeout_seconds = 10
local_timezone = pytz.timezone('Europe/Berlin')
already_sent_ids = None
telegram_bot = None
logger = None
conf = {
    'agb': {'all_id': -1001432733051, 'mrna_id': -1, 'vec_id': -1, 'lat': 48.36989, 'lng': 10.90017, 'address': '86150 Augsburg Innenstadt', 'city': 'Augsburg'},
    'ber': {'all_id': -1001311147212, 'mrna_id': -1001238768507, 'vec_id': -1001407959008, 'lat': 52.52003, 'lng': 13.40489, 'address': '10178 Berlin Mitte', 'city': 'Berlin'},
    'bfe': {'all_id': -1001326829050, 'mrna_id': -1, 'vec_id': -1, 'lat': 52.02465, 'lng': 8.54159, 'address': '33602 Bielefeld Innenstadt', 'city': 'Bielefeld'},
    'bn': {'all_id': -1001391425907, 'mrna_id': -1, 'vec_id': -1, 'lat': 50.72194, 'lng': 7.08833, 'address': '53115 Bonn Poppelsdorf', 'city': 'Bonn'},
    'bre': {'all_id': -1001224145181, 'mrna_id': -1, 'vec_id': -1, 'lat': 53.0778, 'lng': 8.80385, 'address': '28195 Bremen Altstadt', 'city': 'Bremen'},
    'cgn': {'all_id': -1001439806320, 'mrna_id': -1001346411243, 'vec_id': -1001440545907, 'lat': 50.93893, 'lng': 6.95752, 'address': '50667 Koeln Altstadt-Nord', 'city': 'Köln'},
    'co': {'all_id': -1001290443403, 'mrna_id': -1, 'vec_id': -1, 'lat': 50.25944, 'lng': 10.96027, 'address': '96450 Coburg Coburg', 'city': 'Coburg'},
    'drs': {'all_id': -1001165597953, 'mrna_id': -1, 'vec_id': -1, 'lat': 51.05174, 'lng': 13.73729, 'address': '01067 Dresden Innere Altstadt', 'city': 'Dresden'},
    'dtm': {'all_id': -1001168900922, 'mrna_id': -1001312226933, 'vec_id': -1001163809419, 'lat': 51.51422, 'lng': 7.46509, 'address': '44137 Dortmund Mitte', 'city': 'Dortmund'},
    'dus': {'all_id': -1001441637885, 'mrna_id': -1001170209652, 'vec_id': -1001371958170, 'lat': 51.22591, 'lng': 6.77356, 'address': '40213 Duesseldorf Altstadt', 'city': 'Düsseldorf'},
    'erf': {'all_id': -1001183027974, 'mrna_id': -1, 'vec_id': -1, 'lat': 50.97961, 'lng': 11.02388, 'address': '99084 Erfurt Altstadt', 'city': 'Erfurt'},
    'ess': {'all_id': -1001398889913, 'mrna_id': -1001230771678, 'vec_id': -1001435263461, 'lat': 51.4564, 'lng': 7.00999, 'address': '45127 Essen Innenstadt', 'city': 'Essen'},
    'ffm': {'all_id': -1001238323633, 'mrna_id': -1001314044312, 'vec_id': -1001150816653, 'lat': 50.1126, 'lng': 8.68343, 'address': '60311 Frankfurt am Main Innenstadt', 'city': 'Frankfurt'},
    'goe': {'all_id': -1001428055753, 'mrna_id': -1, 'vec_id': -1, 'lat': 51.53305, 'lng': 9.93527, 'address': '37073 Goettingen Goettingen', 'city': 'Göttingen'},
    'hh': {'all_id': -1001237010945, 'mrna_id': -1001251036735, 'vec_id': -1001235895701, 'lat': 53.55, 'lng': 10, 'address': '20457 Hamburg Hamburg-Altstadt', 'city': 'Hamburg'},
    'ka': {'all_id': -1001436511356, 'mrna_id': -1, 'vec_id': -1, 'lat': 49.00934, 'lng': 8.3962, 'address': '76137 Karlsruhe Innenstadt-West', 'city': 'Karlsruhe'},
    'ko': {'all_id': -1001473711809, 'mrna_id': -1, 'vec_id': -1, 'lat': 50.35225, 'lng': 7.59298, 'address': '56068 Koblenz Mitte', 'city': 'Koblenz'},
    'lej': {'all_id': -1001487955448, 'mrna_id': -1001460759342, 'vec_id': -1001451326581, 'lat': 51.33983, 'lng': 12.37541, 'address': '04109 Leipzig Zentrum', 'city': 'Leipzig'},
    'md': {'all_id': -1001183191239, 'mrna_id': -1, 'vec_id': -1, 'lat': 52.1277, 'lng': 11.63815, 'address': '39104 Magdeburg Altstadt', 'city': 'Magdeburg'},
    'ms': {'all_id': -1001427604433, 'mrna_id': -1, 'vec_id': -1, 'lat': 51.9622, 'lng': 7.62719, 'address': '48143 Muenster Centrum', 'city': 'Münster'},
    'muc': {'all_id': -1001464001536, 'mrna_id': -1001126966895, 'vec_id': -1001161931395, 'lat': 48.13836, 'lng': 11.57939, 'address': '80333 Muenchen Altstadt-Lehel', 'city': 'München'},
    'nue': {'all_id': -1001159218767, 'mrna_id': -1001446237946, 'vec_id': -1001181035310, 'lat': 49.4514, 'lng': 11.07471, 'address': '90402 Nuernberg Lorenz', 'city': 'Nürnberg'},
    'str': {'all_id': -1001315735957, 'mrna_id': -1001374316872, 'vec_id': -1001347549449, 'lat': 48.7767, 'lng': 9.18015, 'address': '70173 Stuttgart Mitte', 'city': 'Stuttgart'},
}


def is_local():
    if 'WSL2' in platform.platform() or 'manjaro' in platform.platform():
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


def is_jameda_enabled(city):
    return conf[city]['city'] != ''


def impfstatus_generate_progressbar(percentage):
    num_chars = 10
    num_filled = round(percentage*num_chars)
    num_empty = num_chars-num_filled
    display_percentage = str(round(percentage*100, 1)).replace('.', ',')
    msg = '{}{} {}%'.format('▓'*num_filled, '░'*num_empty, display_percentage)
    return msg


def impfstatus_get_current_data(url):
    tsvstream = urllib.request.urlopen(url)
    tsv_file_lines = tsvstream.read().decode('utf-8').splitlines()
    tsv_data_lines = csv.DictReader(tsv_file_lines, delimiter='\t')
    # skip to last line
    for line_dict in tsv_data_lines:
        pass
    return line_dict


def send_daily_stats(city):
    if is_local():
        return

    city_name = conf[city]['city']
    if city_name == '':
        return
    info_log(f"Sending out daily stats for city {city_name}..")

    msg = f"💉 TÄGLICHE STATISTIK {datetime.datetime.today().strftime('%d.%m.%Y')} FÜR 🇩🇪 💉\n\n"
    impfstatus_data = impfstatus_get_current_data(
        "https://impfdashboard.de/static/data/germany_vaccinations_timeseries_v2.tsv")
    bar_erst = impfstatus_generate_progressbar(
        float(impfstatus_data.get('impf_quote_erst')))
    bar_voll = impfstatus_generate_progressbar(
        float(impfstatus_data.get('impf_quote_voll')))
    msg = msg + f"{bar_erst} haben mindestens eine Impfdosis\n"
    msg = msg + f"{bar_voll} sind bereits vollständig geimpft\n\n"

    msg = msg + "Ich arbeite an diesem Projekt in meiner freien Zeit, "
    msg = msg + "über eine kleine Spende würde ich mich sehr freuen ❤️\n"
    msg = msg + "Das Projekt unterstützen: https://ko-fi.com/maxritter. Vielen Dank 🙏"

    # Send to Telegram channels
    channel_ids = [conf[city]['all_id'], conf[city]
                   ['mrna_id'], conf[city]['vec_id']]
    for channel_id in channel_ids:
        if channel_id is not None and channel_id != -1:
            try:
                telegram_bot.sendMessage(chat_id=channel_id, text=msg)
            except Exception as e:
                error_log(f'[Telegram] Error during message send [{str(e)}]')


def send_channel_msg(city, type, msg):
    global telegram_bot

    # Send to Telegram
    channel_id = conf[city][f'{type}_id']
    if not is_local() and channel_id is not None and channel_id != -1:
        try:
            telegram_bot.sendMessage(chat_id=channel_id, text=msg)
        except Exception as e:
            error_log(f'[Telegram] Error during message send [{str(e)}]')


def init(city):
    global telegram_bot, already_sent_ids, conf

    # Load secrets from file
    load_dotenv(verbose=True)

    # General inits
    already_sent_ids = []
    init_logger(city)
    info_log('Init Impfbot..')

    # Init Telegram Bot
    if not is_local():
        telegram_bot = telegram.Bot(token=os.getenv('TELEGRAM_TOKEN'))

    # Init Doctolib
    doctolib.doctolib_init(city)

    # Try to init Helios API
    if is_helios_enabled(city):
        helios.helios_init(city)

    # Try to init Jameda API
    if is_jameda_enabled(city):
        jameda.jameda_init(city)


# Wrapper class to provide delayed requests to avoid ip bans
class DelayedSession(Session):
    def __init__(self, min_delay_ms=200, max_delay_ms=1500):
        super().__init__()
        self.min_delay_ms = min_delay_ms
        self.max_delay_ms = max_delay_ms

    def get(self, url, **kwargs):
        self.random_delay()
        kwargs.setdefault('allow_redirects', True)
        return self.request('GET', url, **kwargs)

    def post(self, url, data=None, json=None, **kwargs):
        self.random_delay()
        return self.request('POST', url, data=data, json=json, **kwargs)

    def random_delay(self):
        sleep_time = random.randint(self.min_delay_ms, self.max_delay_ms)
        time.sleep(sleep_time/1000 + random.random())


def request(method, url, **kwargs):
    with DelayedSession() as session:
        return session.request(method=method, url=url, **kwargs)


def get(url, params=None, **kwargs):
    kwargs.setdefault('allow_redirects', True)
    return request('get', url, params=params, **kwargs)


def post(url, data=None, json=None, **kwargs):
    return request('post', url, data=data, json=json, **kwargs)
