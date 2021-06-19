import platform
import telegram
import tweepy
import time
import sys
import os
import csv
import urllib.request
import datetime
import pytz
import logging
import requests
from logging import Formatter
from logging.handlers import SysLogHandler
from src import database, helios, doctolib, jameda

# Global variables
api_timeout_seconds = 10
local_timezone = pytz.timezone('Europe/Berlin')
already_sent_ids = None
telegram_bot = None
twitter_bot = None
logger = None
conf = {'muc1': {'all_id': -1001464001536, 'mrna_id': -1001126966895, 'vec_id': -1001161931395, 'lat': -1, 'lng': -1, 'address': '', 'city': ''},
        'muc2': {'all_id': -1001464001536, 'mrna_id': -1001126966895, 'vec_id': -1001161931395, 'lat': -1, 'lng': -1, 'address': '', 'city': ''},
        'muc3': {'all_id': -1001464001536, 'mrna_id': -1001126966895, 'vec_id': -1001161931395, 'lat': -1, 'lng': -1, 'address': '', 'city': ''},
        'muc4': {'all_id': -1001464001536, 'mrna_id': -1001126966895, 'vec_id': -1001161931395, 'lat': -1, 'lng': -1, 'address': '', 'city': ''},
        'muc5': {'all_id': -1001464001536, 'mrna_id': -1001126966895, 'vec_id': -1001161931395, 'lat': -1, 'lng': -1, 'address': '', 'city': ''},
        'muc6': {'all_id': -1001464001536, 'mrna_id': -1001126966895, 'vec_id': -1001161931395, 'lat': -1, 'lng': -1, 'address': '', 'city': ''},
        'muc7': {'all_id': -1001464001536, 'mrna_id': -1001126966895, 'vec_id': -1001161931395, 'lat': 48.13836, 'lng': 11.57939, 'address': '80333 Muenchen Altstadt-Lehel', 'city': 'München'},
        'nue': {'all_id': -1001159218767, 'mrna_id': -1001446237946, 'vec_id': -1001181035310, 'lat': 49.4514, 'lng': 11.07471, 'address': '90402 Nuernberg Lorenz', 'city': 'Nürnberg'},
        'str1': {'all_id': -1001315735957, 'mrna_id': -1001374316872, 'vec_id': -1001347549449, 'lat': 48.7767, 'lng': 9.18015, 'address': '70173 Stuttgart Mitte', 'city': 'Stuttgart'},
        'str2': {'all_id': -1001315735957, 'mrna_id': -1001374316872, 'vec_id': -1001347549449, 'lat': -1, 'lng': -1, 'address': '', 'city': ''},
        'agb': {'all_id': -1001432733051, 'mrna_id': -1, 'vec_id': -1, 'lat': 48.36989, 'lng': 10.90017, 'address': '86150 Augsburg Innenstadt', 'city': 'Augsburg'},
        'cgn1': {'all_id': -1001439806320, 'mrna_id': -1001346411243, 'vec_id': -1001440545907, 'lat': 50.93893, 'lng': 6.95752, 'address': '50667 Koeln Altstadt-Nord', 'city': 'Köln'},
        'cgn2': {'all_id': -1001439806320, 'mrna_id': -1001346411243, 'vec_id': -1001440545907, 'lat': -1, 'lng': -1, 'address': '', 'city': ''},
        'dus': {'all_id': -1001441637885, 'mrna_id': -1001170209652, 'vec_id': -1001371958170, 'lat': 51.22591, 'lng': 6.77356, 'address': '40213 Duesseldorf Altstadt', 'city': 'Düsseldorf'},
        'ber1': {'all_id': -1001311147212, 'mrna_id': -1001238768507, 'vec_id': -1001407959008, 'lat': 52.52003, 'lng': 13.40489, 'address': '10178 Berlin Mitte', 'city': 'Berlin'},
        'ber2': {'all_id': -1001311147212, 'mrna_id': -1001238768507, 'vec_id': -1001407959008, 'lat': -1, 'lng': -1, 'address': '', 'city': ''},
        'ber3': {'all_id': -1001311147212, 'mrna_id': -1001238768507, 'vec_id': -1001407959008, 'lat': -1, 'lng': -1, 'address': '', 'city': ''},
        'ffm': {'all_id': -1001238323633, 'mrna_id': -1001314044312, 'vec_id': -1001150816653, 'lat': 50.1126, 'lng': 8.68343, 'address': '60311 Frankfurt am Main Innenstadt', 'city': 'Frankfurt'},
        'hh': {'all_id': -1001237010945, 'mrna_id': -1001251036735, 'vec_id': -1001235895701, 'lat': 53.55, 'lng': 10, 'address': '20457 Hamburg Hamburg-Altstadt', 'city': 'Hamburg'},
        'lej': {'all_id': -1001487955448, 'mrna_id': -1001460759342, 'vec_id': -1001451326581, 'lat': 51.33983, 'lng': 12.37541, 'address': '04109 Leipzig Zentrum', 'city': 'Leipzig'},
        'bre': {'all_id': -1001224145181, 'mrna_id': -1, 'vec_id': -1, 'lat': 53.0778, 'lng': 8.80385, 'address': '28195 Bremen Altstadt', 'city': 'Bremen'},
        'h': {'all_id': -1001486720744, 'mrna_id': -1, 'vec_id': -1, 'lat': 52.37387, 'lng': 9.73779, 'address': '30161 Hannover Mitte', 'city': 'Hannover'},
        'drs': {'all_id': -1001165597953, 'mrna_id': -1, 'vec_id': -1, 'lat': 51.05174, 'lng': 13.73729, 'address': '01067 Dresden Innere Altstadt', 'city': 'Dresden'},
        'ka': {'all_id': -1001436511356, 'mrna_id': -1, 'vec_id': -1, 'lat': 49.00934, 'lng': 8.3962, 'address': '76137 Karlsruhe Innenstadt-West', 'city': 'Karlsruhe'},
        'erf': {'all_id': -1001183027974, 'mrna_id': -1, 'vec_id': -1, 'lat': 50.97961, 'lng': 11.02388, 'address': '99084 Erfurt Altstadt', 'city': 'Erfurt'},
        'wue': {'all_id': -1001410779884, 'mrna_id': -1, 'vec_id': -1, 'lat': 49.79471, 'lng': 9.93163, 'address': '97070 Wuerzburg Altstadt', 'city': 'Würzburg'},
        'md': {'all_id': -1001183191239, 'mrna_id': -1, 'vec_id': -1, 'lat': 52.1277, 'lng': 11.63815, 'address': '39104 Magdeburg Altstadt', 'city': 'Magdeburg'},
        'dtm': {'all_id': -1001168900922, 'mrna_id': -1001312226933, 'vec_id': -1001163809419, 'lat': 51.51422, 'lng': 7.46509, 'address': '44137 Dortmund Mitte', 'city': 'Dortmund'},
        'ess': {'all_id': -1001398889913, 'mrna_id': -1001230771678, 'vec_id': -1001435263461, 'lat': 51.4564, 'lng': 7.00999, 'address': '45127 Essen Innenstadt', 'city': 'Essen'},
        'bs': {'all_id': -1001333251690, 'mrna_id': -1, 'vec_id': -1, 'lat': 52.26382, 'lng': 10.52242, 'address': '38100 Braunschweig Innenstadt', 'city': 'Braunschweig'},
        'bfe': {'all_id': -1001326829050, 'mrna_id': -1, 'vec_id': -1, 'lat': 52.02465, 'lng': 8.54159, 'address': '33602 Bielefeld Innenstadt', 'city': 'Bielefeld'},
        'goe': {'all_id': -1001428055753, 'mrna_id': -1, 'vec_id': -1, 'lat': 51.53305, 'lng': 9.93527, 'address': '37073 Goettingen Goettingen', 'city': 'Göttingen'},
        'sn': {'all_id': -1001444953581, 'mrna_id': -1, 'vec_id': -1, 'lat': 53.62727, 'lng': 11.41548, 'address': '19053 Schwerin Altstadt', 'city': 'Schwerin'},
        'ko': {'all_id': -1001473711809, 'mrna_id': -1, 'vec_id': -1, 'lat': 50.35225, 'lng': 7.59298, 'address': '56068 Koblenz Mitte', 'city': 'Koblenz'},
        'da': {'all_id': -1001199440597, 'mrna_id': -1, 'vec_id': -1, 'lat': 49.87333, 'lng': 8.65666, 'address': '64283 Darmstadt Darmstadt', 'city': 'Darmstadt'},
        'co': {'all_id': -1001290443403, 'mrna_id': -1, 'vec_id': -1, 'lat': 50.25944, 'lng': 10.96027, 'address': '96450 Coburg Coburg', 'city': 'Coburg'},
        'ke': {'all_id': -1001240810276, 'mrna_id': -1, 'vec_id': -1, 'lat': 47.7267, 'lng': 10.31688, 'address': '87439 Kempten (Allgaeu) Kempten', 'city': 'Kempten'},
        'ul': {'all_id': -1001346082516, 'mrna_id': -1, 'vec_id': -1, 'lat': 48.40137, 'lng': 9.99204, 'address': '89073 Ulm Mitte', 'city': 'Ulm'},
        'dui': {'all_id': -1001481729705, 'mrna_id': -1, 'vec_id': -1, 'lat': 51.43501, 'lng': 6.76115, 'address': '47051 Duisburg Altstadt', 'city': 'Duisburg'},
        'ms': {'all_id': -1001427604433, 'mrna_id': -1, 'vec_id': -1, 'lat': 51.9622, 'lng': 7.62719, 'address': '48143 Muenster Centrum', 'city': 'Münster'},
        'bn': {'all_id': -1001391425907, 'mrna_id': -1, 'vec_id': -1, 'lat': 50.72194, 'lng': 7.08833, 'address': '53115 Bonn Poppelsdorf', 'city': 'Bonn'},
        'rgb': {'all_id': -1, 'mrna_id': -1, 'vec_id': -1, 'lat': 49.017804, 'lng': 12.101659, 'address': '93047 Regensburg', 'city': 'Regensburg'}
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

    vaccinations_all = database.get_vaccinations_last_day(city)
    if not vaccinations_all:
        return
    msg = f"💉 TÄGLICHE STATISTIK {datetime.datetime.today().strftime('%d.%m.%Y')} 💉\n\n"
    msg = msg + f"Der Bot hat für euch in {city_name} in den letzten 24h "
    msg = msg + \
        f"insgesamt {vaccinations_all} Impftermine gefunden, darunter\n"

    vaccinations_astra = database.get_vaccinations_last_day(
        city, 'AstraZeneca')
    if vaccinations_astra:
        astra_perc = (vaccinations_astra / (vaccinations_all * 1.0)) * 100.0
        msg = msg + \
            f"{vaccinations_astra} ({str(round(astra_perc, 1)).replace('.', ',')}%) Impftermin(e) mit AstraZeneca 🇬🇧\n"

    vaccinations_biontech = database.get_vaccinations_last_day(
        city, 'BioNTech')
    if vaccinations_biontech:
        biontech_perc = (vaccinations_biontech /
                         (vaccinations_all * 1.0)) * 100.0
        msg = msg + \
            f"{vaccinations_biontech} ({str(round(biontech_perc, 1)).replace('.', ',')}%) Impftermin(e) mit BioNTech 🇩🇪\n"

    vaccinations_johnson = database.get_vaccinations_last_day(city, 'Johnson')
    if vaccinations_johnson:
        johnson_perc = (vaccinations_johnson /
                        (vaccinations_all * 1.0)) * 100.0
        msg = msg + \
            f"{vaccinations_johnson} ({str(round(johnson_perc, 1)).replace('.', ',')}%) Impftermin(e) mit Johnson & Johnson 🇧🇪\n"

    vaccinations_moderna = database.get_vaccinations_last_day(city, 'Moderna')
    if vaccinations_moderna:
        moderna_perc = (vaccinations_moderna /
                        (vaccinations_all * 1.0)) * 100.0
        msg = msg + \
            f"{vaccinations_moderna} ({str(round(moderna_perc, 1)).replace('.', ',')}%) Impftermin(e) mit Moderna 🇺🇸\n"

    vaccinations_yesterday = database.get_vaccinations_previous_day(city)
    if vaccinations_yesterday:
        diff = abs(vaccinations_all - vaccinations_yesterday)
        if vaccinations_all >= vaccinations_yesterday:
            comp = "mehr"
            symbol = "📈"
            perc = str(round(
                (vaccinations_all / (vaccinations_yesterday * 1.0) * 100.0) - 100.0, 1)).replace('.', ',')
        else:
            comp = "weniger"
            symbol = "📉"
            perc = str(round((vaccinations_yesterday /
                              (vaccinations_all * 1.0) * 100.0) - 100.0, 1)).replace('.', ',')
        msg = msg + \
            f"Das sind {diff} Impftermine ({perc}%) {comp} als gestern {symbol}"

    vaccinations_last_week = database.get_vaccinations_previous_week(city)
    if vaccinations_last_week:
        diff = abs(vaccinations_all - vaccinations_last_week)
        if vaccinations_all >= vaccinations_last_week:
            comp = "mehr"
            symbol = "📈"
            perc = str(round(
                (vaccinations_all / (vaccinations_last_week * 1.0) * 100.0) - 100.0, 1)).replace('.', ',')
        else:
            comp = "weniger"
            symbol = "📉"
            perc = str(round((vaccinations_last_week /
                              (vaccinations_all * 1.0) * 100.0) - 100.0, 1)).replace('.', ',')
        msg = msg + \
            f" und {diff} Impftermine ({perc}%) {comp} als vor einer Woche {symbol}"

    msg = msg + f"\n\nHier findet ihr die Live-Statistik über alle von den Bots gefundenen Impftermine pro Tag, Stadt und Typ 📊:"
    msg = msg + "https://bit.ly/2ShKt41"

    impfstatus_data = impfstatus_get_current_data(
        "https://impfdashboard.de/static/data/germany_vaccinations_timeseries_v2.tsv")
    bar_erst = impfstatus_generate_progressbar(
        float(impfstatus_data.get('impf_quote_erst')))
    bar_voll = impfstatus_generate_progressbar(
        float(impfstatus_data.get('impf_quote_voll')))
    msg = msg + f"\n\nDie Impfstatistik für ganz Deutschland 🇩🇪:\n"
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

    # Wait some time, so people can read the message
    time.sleep(120)


def send_channel_msg(city, type, msg):
    global telegram_bot, twitter_bot

    # Send to Telegram
    channel_id = conf[city][f'{type}_id']
    if not is_local() and channel_id is not None and channel_id != -1:
        try:
            telegram_bot.sendMessage(chat_id=channel_id, text=msg)
        except Exception as e:
            error_log(f'[Telegram] Error during message send [{str(e)}]')

    # Send to Twitter
    if not is_local() and twitter_bot is not None and len(msg) <= 225:
        try:
            twitter_bot.update_status(datetime.datetime.now().astimezone(local_timezone).strftime(
                "%d.%m.%Y %H:%M:%S: ") + msg + " #Impfung #COVID19 #Corona #vaccine")
        except tweepy.TweepError as e:
            if e.api_code != 187:
                error_log(f'[Twitter] Error during message send [{str(e)}]')
        except Exception as e:
            error_log(f'[Twitter] Error during message send [{str(e)}]')


def init(city):
    global telegram_bot, twitter_bot, already_sent_ids, conf

    # For local env, load secrets from file
    if is_local():
        from dotenv import load_dotenv
        load_dotenv(verbose=True)

    # General inits
    already_sent_ids = []
    init_logger(city)
    info_log('Init Impfbot..')

    # Init Telegram and Twitter
    telegram_bot = telegram.Bot(token=os.getenv('TELEGRAM_TOKEN'))
    twitter_city = ''.join((x for x in city if not x.isdigit())).upper()
    twitter_token = os.getenv(f'TWITTER_{twitter_city}_TOKEN')
    twitter_token_secret = os.getenv(f'TWITTER_{twitter_city}_TOKEN_SECRET')
    if twitter_token and twitter_token_secret:
        twitter_auth = tweepy.OAuthHandler(
            os.getenv('TWITTER_CUSTOMER_KEY'), os.getenv('TWITTER_CUSTOMER_SECRET'))
        twitter_auth.set_access_token(twitter_token, twitter_token_secret)
        twitter_bot = tweepy.API(twitter_auth)
    else:
        warn_log("Twitter is not enabled for this city..")

    # Init Doctolib
    doctolib.doctolib_init(city)

    # Try to init Helios API
    if is_helios_enabled(city):
        helios.helios_init(city)

    # Try to init Jameda API
    if is_jameda_enabled(city):
        jameda.jameda_init(city)
