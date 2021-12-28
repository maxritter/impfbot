from enum import unique
import os
import json
import datetime
import time
import random
from src import helper
from fake_headers import Headers

doctolib_headers = Headers(headers=False)
doctolib_proxy = {
    "http": f"socks5://nugwbaeg-rotate:{os.getenv('PROXY_PASSWORD')}@p.webshare.io:80",
    "https": f"socks5://nugwbaeg-rotate:{os.getenv('PROXY_PASSWORD')}@p.webshare.io:80",
}
doctolib_urls = None


def doctolib_init(city):
    global doctolib_urls

    # Load URLs from File
    with open(f"data/{city}.txt") as url_txt:
        doctolib_urls = url_txt.readlines()
    doctolib_urls = [doctolib_url.strip() for doctolib_url in doctolib_urls]


def doctolib_determine_vaccines(
    visit_motive, vaccine_names, vaccine_ids, vaccine_specialities
):
    # Extract some information
    visit_motive_name = visit_motive["name"].lower()
    visit_motive_id = visit_motive["id"]
    speciality_id = visit_motive["speciality_id"]
    visit_motive_covid_vaccination = False
    try:
        visit_motive_covid_vaccination = visit_motive["first_shot_motive"]
    except:
        pass

    # Check if this is a Covid vaccination
    if (visit_motive_covid_vaccination or "impfung" in visit_motive_name) and (
        ("bion" in visit_motive_name)
        or ("astra" in visit_motive_name)
        or ("modern" in visit_motive_name)
        or ("johnson" in visit_motive_name)
        or ("janssen" in visit_motive_name)
    ):
        vaccine_names.append(visit_motive_name)
        vaccine_ids.append(visit_motive_id)
        vaccine_specialities.append(speciality_id)


def doctolib_check_availability(start_date, visit_motive_ids, agenda_ids, practice_ids):
    global doctolib_headers

    params = {
        "start_date": start_date,
        "visit_motive_ids": visit_motive_ids,
        "agenda_ids": agenda_ids,
        "insurance_sector": "public",
        "practice_ids": practice_ids,
        "destroy_temporary": "true",
        "limit": 14,
    }

    repeat_counter = 0
    while True:
        if repeat_counter == 10:
            helper.warn_log(
                f"[Doctolib] Timeout during fetch of availabilities for start date {start_date},\
                            motives {visit_motive_ids}, agendas {agenda_ids} and practice {practice_ids}.."
            )
            return None

        try:
            if not helper.is_local():
                response = helper.get(
                    "https://www.doctolib.de/availabilities.json",
                    params=params,
                    headers=doctolib_headers.generate(),
                    timeout=1,
                    proxies=doctolib_proxy,
                )
            else:
                response = helper.get(
                    "https://www.doctolib.de/availabilities.json",
                    params=params,
                    headers=doctolib_headers.generate(),
                    timeout=1,
                )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            repeat_counter = repeat_counter + 1
            continue


def doctolib_send_message(
    city,
    slot_counter,
    vaccine_name,
    place_address,
    date,
    doctolib_url,
    vaccine_speciality,
):
    if slot_counter == 1:
        message = f"{slot_counter} Termin "
    else:
        message = f"{slot_counter} Termine "
    message = message + f"für {str(vaccine_name).upper()} am {date}"
    if len(place_address.split(",")) == 2:
        place_address_str = place_address.split(",")[1].strip()
        message = message + f" in {place_address_str.upper()}."
    message_long = (
        message
        + f". Hier buchen: {doctolib_url}?speciality_id={vaccine_speciality}&practitioner_id=any"
    )

    # Print message out on server
    helper.info_log(message)

    # Send message to telegram channels for the specific city
    if "bion" in vaccine_name or "modern" in vaccine_name:
        helper.send_channel_msg(city, "mrna", message_long)
        helper.send_channel_msg(city, "all", message_long)
    elif (
        "astra" in vaccine_name
        or "johnson" in vaccine_name
        or "janssen" in vaccine_name
    ):
        helper.send_channel_msg(city, "vec", message_long)
        helper.send_channel_msg(city, "all", message_long)


def doctolib_check(city):
    global doctolib_urls

    try:
        # Check all URLs in the city list
        for doctolib_url in doctolib_urls:
            # sleep_time = random.randint(200, 1500)
            # time.sleep(sleep_time / 1000 + random.random())

            # Get the center and do some basic checks
            center = doctolib_url.split("/")[5]
            try:
                with open(f"json/{center}.txt") as json_file:
                    json_data = json.load(json_file)
            except Exception as e:
                helper.error_log(f"Unable to load JSON for center {center}, continue..")
                continue
            data = json_data["data"]
            visit_motives = [visit_motive for visit_motive in data["visit_motives"]]
            if not visit_motives:
                continue

            # Determine Vaccine
            vaccine_names = []
            vaccine_ids = []
            vaccine_specialities = []
            for visit_motive in visit_motives:
                # If new patients are not allowed, we can not take this one
                try:
                    if not visit_motive["allow_new_patients"]:
                        continue
                except:
                    pass

                # Get information about name, ID and days
                doctolib_determine_vaccines(
                    visit_motive, vaccine_names, vaccine_ids, vaccine_specialities
                )
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
                    practice_name = place["formal_name"]

                    # Create agends IDs
                    agendas = [
                        agenda
                        for agenda in data["agendas"]
                        if agenda["practice_id"] == practice_ids
                        and not agenda["booking_disabled"]
                        and visit_motive_ids in agenda["visit_motive_ids"]
                    ]
                    if not agendas:
                        continue
                    agenda_ids = "-".join([str(agenda["id"]) for agenda in agendas])

                    # Check for availability
                    response_json = doctolib_check_availability(
                        start_date, visit_motive_ids, agenda_ids, practice_ids
                    )
                    if response_json is None:
                        continue
                    nb_availabilities = response_json["total"]
                    if nb_availabilities == 0:
                        continue

                    total_dict = {}
                    unsent_dict = {}
                    for availability in response_json["availabilities"]:
                        available_date = datetime.datetime.strptime(
                            availability.get("date"), "%Y-%m-%d"
                        ).strftime("%d.%m.%Y")
                        unsent_dict[available_date] = 0
                        total_dict[available_date] = 0
                        for slot in availability["slots"]:
                            vaccination_id = "{}.{}.{}.{}".format(
                                visit_motive_ids, agenda_ids, practice_ids, slot
                            )

                            if vaccination_id not in helper.already_sent_ids:
                                unsent_dict[available_date] = (
                                    unsent_dict[available_date] + 1
                                )
                                helper.already_sent_ids.append(vaccination_id)

                            total_dict[available_date] = total_dict[available_date] + 1

                    # Construct and send message
                    vaccine_name = vaccine_names[vaccine_counter]
                    vaccine_speciality = vaccine_specialities[vaccine_counter]
                    vaccine_compound = helper.get_vaccine_compound(vaccine_name)
                    vaccine_type = helper.get_vaccine_type(vaccine_name)

                    # Send unsent appointments to Doctolib
                    for date in unsent_dict:
                        if unsent_dict[date] > 0:
                            slot_counter = total_dict[date]
                            doctolib_send_message(
                                city,
                                slot_counter,
                                vaccine_name,
                                place_address,
                                date,
                                doctolib_url,
                                vaccine_speciality,
                            )

                    # Update all airtable entries
                    for date in total_dict:
                        slot_counter = total_dict[date]
                        id = "{}.{}.{}.{}".format(
                            visit_motive_ids, agenda_ids, practice_ids, date
                        )
                        current_date = datetime.datetime.strptime(date, "%d.%m.%Y")
                        helper.update_airtable_entry(
                            id,
                            city,
                            slot_counter,
                            doctolib_url,
                            practice_name,
                            vaccine_type,
                            vaccine_compound,
                            current_date,
                            place_address,
                            "Doctolib",
                        )

                vaccine_counter = vaccine_counter + 1

    except json.decoder.JSONDecodeError:
        helper.warn_log("[Doctolib] Currently not responding, try again later..")
    except KeyError as e:
        helper.error_log(f"[Doctolib] Key Error [{str(e)}]")
    except Exception as e:
        helper.error_log(f"[Doctolib] General Error {center} [{str(e)}]")
