import os
import json
import datetime
import time
import random
from src import helper
from fake_headers import Headers

doctolib_headers = Headers(
    headers=False
)
doctolib_proxy = {
    'http': f"socks5://nugwbaeg-rotate:{os.getenv('PROXY_PASSWORD')}@p.webshare.io:80",
    'https': f"socks5://nugwbaeg-rotate:{os.getenv('PROXY_PASSWORD')}@p.webshare.io:80"
}
doctolib_urls = None


def doctolib_init(city):
    global doctolib_urls

    # Load URLs from File
    with open(f'data/{city}.txt') as url_txt:
        doctolib_urls = url_txt.readlines()
    doctolib_urls = [doctolib_url.strip() for doctolib_url in doctolib_urls]


def doctolib_determine_vaccines(visit_motive, vaccine_names, vaccine_ids, vaccine_days, vaccine_specialities):
    # Extract some information
    visit_motive_name = visit_motive['name'].lower()
    visit_motive_id = visit_motive['id']
    speciality_id = visit_motive['speciality_id']
    visit_motive_covid_vaccination = False
    try:
        visit_motive_covid_vaccination = visit_motive['first_shot_motive']
    except:
        pass

    # Check if this is a Covid vaccination
    if (visit_motive_covid_vaccination or
        "impfung" in visit_motive_name) and \
        (("bion" in visit_motive_name) or
            ("astra" in visit_motive_name and not "zweit" in visit_motive_name and not "2." in visit_motive_name) or
            ("modern" in visit_motive_name and not "zweit" in visit_motive_name and not "2." in visit_motive_name) or
            ("johnson" in visit_motive_name and not "zweit" in visit_motive_name and not "2." in visit_motive_name) or
            ("janssen" in visit_motive_name and not "zweit" in visit_motive_name and not "2." in visit_motive_name)):

        if "bion" in visit_motive_name and not "zweit" in visit_motive_name and not "2." in visit_motive_name:
            vaccine_names.append("BioNTech")
        elif "bion" in visit_motive_name and ("zweit" in visit_motive_name or "2." in visit_motive_name):
            vaccine_names.append("BioNTech (2. Impfung)")
        elif "astra" in visit_motive_name:
            vaccine_names.append("AstraZeneca")
        elif "modern" in visit_motive_name:
            vaccine_names.append("Moderna")
        elif "johnson" in visit_motive_name or "janssen" in visit_motive_name:
            vaccine_names.append("Johnson & Johnson")
        else:
            helper.error_log(
                f'[Doctolib] Unknown vaccination: {visit_motive_name}')

        vaccine_ids.append(visit_motive_id)
        vaccine_specialities.append(speciality_id)

        visit_motive_day = 0
        try:
            if(visit_motive['vaccination_days_range'] is not None and visit_motive['vaccination_days_range'] > 0):
                visit_motive_day = visit_motive['vaccination_days_range']
        except:
            pass
        vaccine_days.append(visit_motive_day)


def doctolib_check_availability(start_date, visit_motive_ids, agenda_ids, practice_ids):
    global doctolib_headers

    params = {
        "start_date": start_date,
        "visit_motive_ids": visit_motive_ids,
        "agenda_ids": agenda_ids,
        "insurance_sector": "public",
        "practice_ids": practice_ids,
        "destroy_temporary": "true",
        "limit": 14
    }

    repeat_counter = 0
    while True:
        if repeat_counter == 100:
            helper.warn_log(f'[Doctolib] Timeout during fetch of availabilities for start date {start_date},\
                            motives {visit_motive_ids}, agendas {agenda_ids} and practice {practice_ids}..')
            return None

        try:
            if not helper.is_local():
                response = helper.get(
                    "https://www.doctolib.de/availabilities.json",
                    params=params,
                    headers=doctolib_headers.generate(),
                    timeout=1,
                    proxies=doctolib_proxy
                )
            else:
                response = helper.get(
                    "https://www.doctolib.de/availabilities.json",
                    params=params,
                    headers=doctolib_headers.generate(),
                    timeout=1
                )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            repeat_counter = repeat_counter + 1
            continue


def doctolib_send_message(city, slot_counter, vaccine_name, vaccine_day, place_address, available_dates, doctolib_url, vaccine_speciality):
    if slot_counter == 1:
        message = f'{slot_counter} freier Impftermin '
    else:
        message = f'{slot_counter} freie Impftermine '
    message = message + f'für {vaccine_name} '
    if vaccine_day != 0:
        message = message + \
            f'mit Abstand zur 2. Impfung von {vaccine_day} Tagen '
    if len(place_address.split(",")) == 2:
        place_address_str = place_address.split(",")[1].strip()
        message = message + f'in {place_address_str}'
    verbose_dates = ", ".join(sorted(set(available_dates)))
    message = message + \
        f". Wählbare Tage: {verbose_dates}."
    message_long = message + \
        f" Hier buchen: {doctolib_url}?speciality_id={vaccine_speciality}&practitioner_id=any"

    # Print message out on server
    helper.info_log(message)

    # Send message to telegram channels for the specific city
    if vaccine_name == 'BioNTech' or vaccine_name == 'BioNTech (2. Impfung)' or vaccine_name == 'Moderna':
        helper.send_channel_msg(city, 'mrna', message_long)
        helper.send_channel_msg(city, 'all', message_long)
    elif vaccine_name == 'AstraZeneca' or vaccine_name == 'Johnson & Johnson':
        helper.send_channel_msg(city, 'vec', message_long)
        helper.send_channel_msg(city, 'all', message_long)


def doctolib_check(city):
    global doctolib_urls

    try:
        # Check all URLs in the city list
        for doctolib_url in doctolib_urls:
            time.sleep((60 * 5 + (random.random() * 60)) / 1000)

            # Get the center and do some basic checks
            center = doctolib_url.split("/")[5]
            try:
                with open(f'json/{center}.txt') as json_file:
                    json_data = json.load(json_file)
            except Exception as e:
                helper.error_log(
                    f"Unable to load JSON for center {center}, continue..")
                continue
            data = json_data["data"]
            visit_motives = [
                visit_motive for visit_motive in data["visit_motives"]]
            if not visit_motives:
                continue

            # Determine Vaccine
            vaccine_names = []
            vaccine_ids = []
            vaccine_specialities = []
            vaccine_days = []
            for visit_motive in visit_motives:
                # If new patients are not allowed, we can not take this one
                try:
                    if not visit_motive['allow_new_patients']:
                        continue
                except:
                    pass

                # Get information about name, ID and days
                doctolib_determine_vaccines(
                    visit_motive, vaccine_names, vaccine_ids, vaccine_days, vaccine_specialities)
            if len(vaccine_ids) == 0 or len(vaccine_names) == 0:
                continue

            # Extract places
            places = [place for place in data["places"]]
            if not places:
                continue

            # Go through the different vaccines and places for this center
            vaccine_counter = 0
            for vaccine_id in vaccine_ids:
                for place in places:
                    # Create some metainformation
                    start_date = datetime.datetime.today().date().isoformat()
                    visit_motive_ids = vaccine_id
                    practice_ids = place["practice_ids"][0]
                    place_address = place["full_address"]

                    # Create agends IDs
                    agendas = [agenda for agenda in data["agendas"]
                               if agenda["practice_id"] == practice_ids and
                               not agenda["booking_disabled"] and
                               visit_motive_ids in agenda["visit_motive_ids"]]
                    if not agendas:
                        continue
                    agenda_ids = "-".join([str(agenda["id"])
                                          for agenda in agendas])

                    # Check for availability
                    response_json = doctolib_check_availability(
                        start_date, visit_motive_ids, agenda_ids, practice_ids)
                    if response_json is None:
                        continue
                    nb_availabilities = response_json["total"]
                    if nb_availabilities == 0:
                        continue

                    # Parse all available dates
                    available_dates = []
                    slot_counter = 0
                    for availability in response_json["availabilities"]:
                        # Parse all available slots
                        for slot in availability["slots"]:
                            vaccination_id = "{}.{}.{}.{}".format(
                                visit_motive_ids, agenda_ids, practice_ids, slot)

                            # If appointment has not been sent out already
                            if vaccination_id not in helper.already_sent_ids:
                                d = datetime.datetime.strptime(
                                    availability.get("date"), '%Y-%m-%d')
                                available_dates.append(
                                    datetime.date.strftime(d, "%d.%m.%y"))
                                helper.already_sent_ids.append(vaccination_id)
                                slot_counter = slot_counter + 1
                    if slot_counter == 0:
                        continue

                    # Construct and send message and add to DB
                    vaccine_name = vaccine_names[vaccine_counter]
                    vaccine_day = vaccine_days[vaccine_counter]
                    vaccine_speciality = vaccine_specialities[vaccine_counter]
                    doctolib_send_message(
                        city, slot_counter, vaccine_name, vaccine_day, place_address, available_dates, doctolib_url, vaccine_speciality)

                vaccine_counter = vaccine_counter + 1

    except json.decoder.JSONDecodeError:
        helper.warn_log(
            '[Doctolib] Currently not responding, try again later..')
    except KeyError as e:
        helper.error_log(f'[Doctolib] Key Error [{str(e)}]')
    except Exception as e:
        helper.error_log(f'[Doctolib] General Error {center} [{str(e)}]')
