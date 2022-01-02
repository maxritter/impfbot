import platform
from requests.sessions import Session
import telegram
import random
import time
import sys
import os
import csv
import urllib.request
from pyairtable import Table
from pyairtable.formulas import match
from dotenv import load_dotenv
import datetime
import pytz
import logging
from logging import Formatter
from logging.handlers import SysLogHandler
from src import helios, doctolib, jameda

# Global variables
api_timeout_seconds = 10
airtable_api_key = os.environ["AIRTABLE_API_KEY"]
airtable_base_id = "appLWz5gLNlhjhN94"
airtable_id_count_dict = {}
local_timezone = pytz.timezone("Europe/Berlin")
telegram_bot = None
airtable_table = None
logger = None
conf = {
    "agb": {
        "table_id": "tblWu2oUn2k4KmVzs",
        "all_id": -1001432733051,
        "mrna_id": -1,
        "vec_id": -1,
        "lat": 48.36989,
        "lng": 10.90017,
        "address": "86150 Augsburg Innenstadt",
        "city": "Augsburg",
    },
    "ber": {
        "table_id": "tblWSQ9lRQjSR1vrY",
        "all_id": -1001311147212,
        "mrna_id": -1001238768507,
        "vec_id": -1001407959008,
        "lat": 52.52003,
        "lng": 13.40489,
        "address": "10178 Berlin Mitte",
        "city": "Berlin",
    },
    "bfe": {
        "table_id": "tbl4xuMB8dfvpw7Sq",
        "all_id": -1001326829050,
        "mrna_id": -1,
        "vec_id": -1,
        "lat": 52.02465,
        "lng": 8.54159,
        "address": "33602 Bielefeld Innenstadt",
        "city": "Bielefeld",
    },
    "bn": {
        "table_id": "tblShufjKzCmESOyB",
        "all_id": -1001391425907,
        "mrna_id": -1,
        "vec_id": -1,
        "lat": 50.72194,
        "lng": 7.08833,
        "address": "53115 Bonn Poppelsdorf",
        "city": "Bonn",
    },
    "bre": {
        "table_id": "tblgw0gy4I5JlF18z",
        "all_id": -1001224145181,
        "mrna_id": -1,
        "vec_id": -1,
        "lat": 53.0778,
        "lng": 8.80385,
        "address": "28195 Bremen Altstadt",
        "city": "Bremen",
    },
    "cgn": {
        "table_id": "tblMnfEDGdwpIRkI3",
        "all_id": -1001439806320,
        "mrna_id": -1001346411243,
        "vec_id": -1001440545907,
        "lat": 50.93893,
        "lng": 6.95752,
        "address": "50667 Koeln Altstadt-Nord",
        "city": "Köln",
    },
    "co": {
        "table_id": "tbl7vbvyX4fxsOP0Z",
        "all_id": -1001290443403,
        "mrna_id": -1,
        "vec_id": -1,
        "lat": 50.25944,
        "lng": 10.96027,
        "address": "96450 Coburg Coburg",
        "city": "Coburg",
    },
    "drs": {
        "table_id": "tblcn27JmkgRLvwj0",
        "all_id": -1001165597953,
        "mrna_id": -1,
        "vec_id": -1,
        "lat": 51.05174,
        "lng": 13.73729,
        "address": "01067 Dresden Innere Altstadt",
        "city": "Dresden",
    },
    "dtm": {
        "table_id": "tblZGNlEHN4OLgBJp",
        "all_id": -1001168900922,
        "mrna_id": -1001312226933,
        "vec_id": -1001163809419,
        "lat": 51.51422,
        "lng": 7.46509,
        "address": "44137 Dortmund Mitte",
        "city": "Dortmund",
    },
    "dus": {
        "table_id": "tblpXiQ8SgCngeLLK",
        "all_id": -1001441637885,
        "mrna_id": -1001170209652,
        "vec_id": -1001371958170,
        "lat": 51.22591,
        "lng": 6.77356,
        "address": "40213 Duesseldorf Altstadt",
        "city": "Düsseldorf",
    },
    "erf": {
        "table_id": "tblVmGYPancDHUuS6",
        "all_id": -1001183027974,
        "mrna_id": -1,
        "vec_id": -1,
        "lat": 50.97961,
        "lng": 11.02388,
        "address": "99084 Erfurt Altstadt",
        "city": "Erfurt",
    },
    "ess": {
        "table_id": "tbl4SkHZHPSSGaKpe",
        "all_id": -1001398889913,
        "mrna_id": -1001230771678,
        "vec_id": -1001435263461,
        "lat": 51.4564,
        "lng": 7.00999,
        "address": "45127 Essen Innenstadt",
        "city": "Essen",
    },
    "ffm": {
        "table_id": "tblAKfzNRHildk6Q3",
        "all_id": -1001238323633,
        "mrna_id": -1001314044312,
        "vec_id": -1001150816653,
        "lat": 50.1126,
        "lng": 8.68343,
        "address": "60311 Frankfurt am Main Innenstadt",
        "city": "Frankfurt",
    },
    "goe": {
        "table_id": "tblVskOGZP8TUxnqn",
        "all_id": -1001428055753,
        "mrna_id": -1,
        "vec_id": -1,
        "lat": 51.53305,
        "lng": 9.93527,
        "address": "37073 Goettingen Goettingen",
        "city": "Göttingen",
    },
    "hh": {
        "table_id": "tblOMrxuTFRDYDXYg",
        "all_id": -1001237010945,
        "mrna_id": -1001251036735,
        "vec_id": -1001235895701,
        "lat": 53.55,
        "lng": 10,
        "address": "20457 Hamburg Hamburg-Altstadt",
        "city": "Hamburg",
    },
    "ka": {
        "table_id": "tbl3gXTmGtpH6PTgo",
        "all_id": -1001436511356,
        "mrna_id": -1,
        "vec_id": -1,
        "lat": 49.00934,
        "lng": 8.3962,
        "address": "76137 Karlsruhe Innenstadt-West",
        "city": "Karlsruhe",
    },
    "ko": {
        "table_id": "tblXDkqewnS4zkqAZ",
        "all_id": -1001473711809,
        "mrna_id": -1,
        "vec_id": -1,
        "lat": 50.35225,
        "lng": 7.59298,
        "address": "56068 Koblenz Mitte",
        "city": "Koblenz",
    },
    "lej": {
        "table_id": "tblua8aYOFXo1ckyF",
        "all_id": -1001487955448,
        "mrna_id": -1001460759342,
        "vec_id": -1001451326581,
        "lat": 51.33983,
        "lng": 12.37541,
        "address": "04109 Leipzig Zentrum",
        "city": "Leipzig",
    },
    "md": {
        "table_id": "tbl0c6QH3LBZ4EHpD",
        "all_id": -1001183191239,
        "mrna_id": -1,
        "vec_id": -1,
        "lat": 52.1277,
        "lng": 11.63815,
        "address": "39104 Magdeburg Altstadt",
        "city": "Magdeburg",
    },
    "ms": {
        "table_id": "tblRqSz9O8529G5Ux",
        "all_id": -1001427604433,
        "mrna_id": -1,
        "vec_id": -1,
        "lat": 51.9622,
        "lng": 7.62719,
        "address": "48143 Muenster Centrum",
        "city": "Münster",
    },
    "muc": {
        "table_id": "tblc5cYM4bputqPyf",
        "all_id": -1001464001536,
        "mrna_id": -1001126966895,
        "vec_id": -1001161931395,
        "lat": 48.13836,
        "lng": 11.57939,
        "address": "80333 Muenchen Altstadt-Lehel",
        "city": "München",
    },
    "nue": {
        "table_id": "tblg4MsEmObYEUNQx",
        "all_id": -1001159218767,
        "mrna_id": -1001446237946,
        "vec_id": -1001181035310,
        "lat": 49.4514,
        "lng": 11.07471,
        "address": "90402 Nuernberg Lorenz",
        "city": "Nürnberg",
    },
    "str": {
        "table_id": "tbltzZiRg9DdIOFwG",
        "all_id": -1001315735957,
        "mrna_id": -1001374316872,
        "vec_id": -1001347549449,
        "lat": 48.7767,
        "lng": 9.18015,
        "address": "70173 Stuttgart Mitte",
        "city": "Stuttgart",
    },
}


def is_local():
    if "WSL2" in platform.platform() or "manjaro" in platform.platform():
        return True
    return False


def error_handler(type, value, tb):
    logger.exception("Uncaught exception: {0}".format(str(value)))


def init_logger(city):
    global logger

    log_format = f"[%(levelname)s] [{city.upper()}] %(message)s"

    logger = logging.getLogger(city)
    logger.propagate = False
    logger.setLevel(logging.INFO)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(Formatter(log_format))
    logger.addHandler(console_handler)

    # For cluster monitoring, use papertrail.com that also alerts on errors
    if not is_local():
        papertrail_handler = SysLogHandler(address=("logs2.papertrailapp.com", 51309))
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
    return (
        conf[city]["lat"] != -1
        and conf[city]["lng"] != -1
        and conf[city]["address"] != ""
    )


def is_jameda_enabled(city):
    return conf[city]["city"] != ""


def title_is_vaccination(title, doctolib_motive_vaccination=False):
    if doctolib_motive_vaccination or "impfung" in title.lower() and (
        "johnson" in title.lower()
        or "janssen" in title.lower()
        or "astra" in title.lower()
        or "bion" in title.lower()
        or "modern" in title.lower()
    ):
        return True
    return False


def impfstatus_generate_progressbar(percentage):
    num_chars = 10
    num_filled = round(percentage * num_chars)
    num_empty = num_chars - num_filled
    display_percentage = str(round(percentage * 100, 1)).replace(".", ",")
    msg = "{}{} {}%".format("▓" * num_filled, "░" * num_empty, display_percentage)
    return msg


def impfstatus_get_current_data(url):
    tsvstream = urllib.request.urlopen(url)
    tsv_file_lines = tsvstream.read().decode("utf-8").splitlines()
    tsv_data_lines = csv.DictReader(tsv_file_lines, delimiter="\t")
    # skip to last line
    for line_dict in tsv_data_lines:
        pass
    return line_dict


def send_daily_stats(city):
    if is_local():
        return

    city_name = conf[city]["city"]
    if city_name == "":
        return
    info_log(f"Sending out daily stats for city {city_name}..")

    msg = f"💉 TÄGLICHE STATISTIK {datetime.datetime.today().strftime('%d.%m.%Y')} FÜR 🇩🇪 💉\n\n"
    impfstatus_data = impfstatus_get_current_data(
        "https://impfdashboard.de/static/data/germany_vaccinations_timeseries_v2.tsv"
    )
    bar_erst = impfstatus_generate_progressbar(
        float(impfstatus_data.get("impf_quote_erst"))
    )
    bar_voll = impfstatus_generate_progressbar(
        float(impfstatus_data.get("impf_quote_voll"))
    )
    msg = msg + f"{bar_erst} haben mindestens eine Impfdosis\n"
    msg = msg + f"{bar_voll} sind bereits vollständig geimpft\n\n"

    msg = msg + "Ich arbeite an diesem Projekt in meiner freien Zeit, "
    msg = msg + "über eine kleine Spende würde ich mich sehr freuen ❤️\n"
    msg = msg + "Das Projekt unterstützen: https://ko-fi.com/maxritter. Vielen Dank 🙏"

    # Send to Telegram channels
    channel_ids = [conf[city]["all_id"], conf[city]["mrna_id"], conf[city]["vec_id"]]
    for channel_id in channel_ids:
        if channel_id is not None and channel_id != -1:
            try:
                telegram_bot.sendMessage(chat_id=channel_id, text=msg)
            except Exception as e:
                error_log(f"[Telegram] Error during message send [{str(e)}]")


def get_airtable_entries():
    global airtable_id_count_dict, airtable_table

    try:
        airtable_entries = airtable_table.all()
        for entry in airtable_entries:
            try:
                airtable_id_count_dict[entry["fields"]["ID"]] = entry["fields"][
                    "Anzahl"
                ]
            except Exception as e:
                error_log(f"[Airtable] Error during get entry: [{str(e)}]")

    except Exception as e:
        error_log(f"[Airtable] Error during get entries: [{str(e)}]")


def delete_airtable_entry(vaccination_id):
    global airtable_id_count_dict, airtable_table

    if not airtable_table:
        return

    try:
        formula = match({"ID": vaccination_id})
        entry = airtable_table.first(formula=formula)
        if entry:
            info_log(f"Deleting Airtable record with ID {vaccination_id}..")
            if not is_local():
                airtable_table.delete(entry["id"])
            airtable_id_count_dict[vaccination_id] = 0
        else:
            warn_log(f"Unable to delete Airtable record with ID {vaccination_id}..")
    except Exception as e:
        error_log(f"[Airtable] Error during delete: [{str(e)}]")


def update_airtable_entry(
    vaccination_id,
    count,
    available_dates,
):
    global airtable_id_count_dict, airtable_table

    if not airtable_table:
        return

    try:
        formula = match({"ID": vaccination_id})
        entry = airtable_table.first(formula=formula)
        if entry:
            info_log(f"Updating Airtable record with ID {vaccination_id}..")
            if not is_local():
                airtable_table.update(
                    entry["id"],
                    {
                        "Termine": ", ".join(sorted(set(available_dates))),
                        "Anzahl": count,
                    },
                )
        else:
            warn_log(f"Unable to update Airtable record with ID {vaccination_id}..")
    except Exception as e:
        error_log(f"[Airtable] Error during update: [{str(e)}]")


def create_airtable_entry(
    vaccination_id,
    name,
    count,
    url,
    practice,
    type,
    compound,
    available_dates,
    address,
    city,
    platform,
):
    global airtable_id_count_dict, airtable_table

    if not airtable_table:
        return

    try:
        info_log(f"Creating Airtable record with ID {vaccination_id}..")
        if not is_local():
            airtable_table.create(
                {
                    "Name": name,
                    "Adresse": address,
                    "Stadt": city,
                    "Impfstoff": compound,
                    "Impftyp": type,
                    "Termine": ", ".join(sorted(set(available_dates))),
                    "Praxis": practice,
                    "Anzahl": count,
                    "Link": url,
                    "Plattform": platform,
                    "ID": vaccination_id,
                    "Kinder": check_kinder(name),
                }
            )
    except Exception as e:
        error_log(f"[Airtable] Error during create: [{str(e)}]")


def send_channel_msg(city, type, msg):
    global telegram_bot

    # Send to Telegram
    channel_id = conf[city][f"{type}_id"]
    if not is_local() and channel_id is not None and channel_id != -1:
        try:
            telegram_bot.sendMessage(chat_id=channel_id, text=msg)
        except Exception as e:
            error_log(f"[Telegram] Error during message send [{str(e)}]")


def get_vaccine_compound(vaccine_name):
    if "bion" in vaccine_name.lower() or "pfizer" in vaccine_name.lower():
        vaccine_compound = "BioNTech"
    elif "modern" in vaccine_name.lower():
        vaccine_compound = "Moderna"
    elif "astra" in vaccine_name.lower():
        vaccine_compound = "AstraZeneca"
    elif "janssen" in vaccine_name.lower() or "johnson" in vaccine_name.lower():
        vaccine_compound = "Johnson & Johnson"
    else:
        vaccine_compound = "Unbekannt"
    return vaccine_compound


def check_vaccine(condition, vaccine_name):
    return condition in vaccine_name.lower()


def check_kinder(vaccine_name):
    has_kinder = (
        "kinder" in vaccine_name.lower()
        or "5" in vaccine_name.lower()
        or "11" in vaccine_name.lower()
        or "12" in vaccine_name.lower()
        or "16" in vaccine_name.lower()
    )
    return has_kinder


def get_vaccine_type(vaccine_name):
    if (
        (check_vaccine("1.", vaccine_name) or check_vaccine("erst", vaccine_name))
        and (check_vaccine("2.", vaccine_name) or check_vaccine("zweit", vaccine_name))
        and (
            check_vaccine("3.", vaccine_name)
            or check_vaccine("dritt", vaccine_name)
            or check_vaccine("auffrischung", vaccine_name)
            or check_vaccine("booster", vaccine_name)
        )
    ) or check_vaccine("alle", vaccine_name):
        vaccine_type = "Alle Impfungen"
    elif (
        check_vaccine("1.", vaccine_name) or check_vaccine("erst", vaccine_name)
    ) and (check_vaccine("2.", vaccine_name) or check_vaccine("zweit", vaccine_name)):
        vaccine_type = "Erst- & Zweitimpfung"
    elif check_vaccine("1.", vaccine_name) or check_vaccine("erst", vaccine_name):
        vaccine_type = "Erstimpfung"
    elif check_vaccine("2.", vaccine_name) or check_vaccine("zweit", vaccine_name):
        vaccine_type = "Zweitimpfung"
    elif (
        check_vaccine("3.", vaccine_name)
        or check_vaccine("dritt", vaccine_name)
        or check_vaccine("auffrischung", vaccine_name)
        or check_vaccine("booster", vaccine_name)
    ):
        vaccine_type = "Auffrischungsimpfung"
    elif check_vaccine("einzel", vaccine_name):
        vaccine_type = "Einzelimpfung"
    else:
        vaccine_type = "Alle Impfungen"
    return vaccine_type


def init(city):
    global telegram_bot, conf, airtable_table

    # Load secrets from file
    load_dotenv(verbose=True)

    # General inits
    init_logger(city)
    info_log("Init Impfbot..")
    airtable_table_id = conf[city]["table_id"]
    if airtable_api_key and airtable_base_id and airtable_table_id:
        airtable_table = Table(airtable_api_key, airtable_base_id, airtable_table_id)
        get_airtable_entries()
    else:
        error_log(f"[Airtable] Settings could not be loaded for city: {city}")

    # Init Telegram Bot
    if not is_local():
        telegram_bot = telegram.Bot(token=os.getenv("TELEGRAM_TOKEN"))

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
        kwargs.setdefault("allow_redirects", True)
        return self.request("GET", url, **kwargs)

    def post(self, url, data=None, json=None, **kwargs):
        self.random_delay()
        return self.request("POST", url, data=data, json=json, **kwargs)

    def random_delay(self):
        sleep_time = random.randint(self.min_delay_ms, self.max_delay_ms)
        time.sleep(sleep_time / 1000 + random.random())


def request(method, url, **kwargs):
    with DelayedSession() as session:
        return session.request(method=method, url=url, **kwargs)


def get(url, params=None, **kwargs):
    kwargs.setdefault("allow_redirects", True)
    return request("get", url, params=params, **kwargs)


def post(url, data=None, json=None, **kwargs):
    return request("post", url, data=data, json=json, **kwargs)
