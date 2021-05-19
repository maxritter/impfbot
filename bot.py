import datetime
import requests
import telegram
import time
import json
import sys

already_sent_ids = []


def check_hnomedic_api():
    url = "https://onlinetermine.zollsoft.de/includes/searchTermine_app_feature.php"
    headers = {
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
        "cache-control": "no-cache",
        "cookie": "sec_session_id=caa60b6cfa29689425205c27f21a1ca8",
        "origin": "https://onlinetermine.zollsoft.de",
        "pragma": "no-cache",
        "referer": "https://onlinetermine.zollsoft.de/patientenTermine.php?uniqueident=6087dd08bd763",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.114 Safari/537.36",
        "x-requested-with": "XMLHttpRequest",
    }
    payload = {
        "versichert": "",
        "terminsuche": "",
        "uniqueident": "6087dd08bd763",
    }

    res = requests.post(url, headers=headers, data=payload)
    res.raise_for_status()
    result = res.json()
    nb_availabilities = len(result["termine"])

    if nb_availabilities > 0:
        # termine: [["2021\/05\/19", "12:28", "18172348282", "Lisa Schultes", "Pasing (Institutstra\u00dfe 14) | Corona-Impfung (AstraZeneca)", "7", "", "f", "f", "2021-05-16 18:44:22"]]
        for entry in result["termine"]:
            date, time, _, _, location, _, _, _, _, _ = entry
            vaccination_id = "{}.{}.{}".format(
                date, time, location)
            if vaccination_id not in already_sent_ids:
                # Determine Vaccine
                vaccine = "COVID-19 Impfstoff"
                if "biontech" in location.lower():
                    vaccine = "BioNTech"
                elif "astrazeneca" in location.lower():
                    vaccine = "AstraZeneca"
                elif "moderna" in location.lower():
                    vaccine = "Moderna"
                elif "johnson" in location.lower() or "janssen" in location.lower():
                    vaccine = "Johnson & Johnson"

                # Construct message
                message = "1 freier Impftermin für {} am {} um {} Uhr".format(
                    vaccine, date, time)
                if len(location.split("|")) == 2:
                    message = message + \
                        " in {}".format(
                            location.split("|")[0].strip())
                message = message + \
                    ". Hier buchen: https://onlinetermine.zollsoft.de/patientenTermine.php?uniqueident=6087dd08bd763"

                # Print message out on server with city in front
                print(sys.argv[1] + ": " + message)

                # Send message to telegram channel for the specific city
                telegram_bot.sendMessage(
                    chat_id=sys.argv[4], text=message)

                # Do not send it out again for 60 minutes
                already_sent_ids.append(vaccination_id)


with open(sys.argv[2]) as centers_url_txt:
    centers_urls = centers_url_txt.readlines()
centers_urls = [center.strip() for center in centers_urls
                if not center.startswith("#")]

try:
    print("Searching for appointments in {} now..".format(sys.argv[1]))

    telegram_bot = telegram.Bot(token=sys.argv[3])
    t = time.time()

    while True:
        # Eventually clear list
        if time.time()-t > 3600:
            print("Clearing list now..")
            already_sent_ids.clear()
            t = time.time()

        # For Munich, we have an additional API
        if sys.argv[1] == 'Munich':
            try:
                check_hnomedic_api()
            except Exception as e:
                print("ERROR during HNOMedic check: " + str(e))

        # Check Doctolib
        for center_url in centers_urls:
            try:
                center = center_url.split("/")[5]
                raw_data = requests.get(
                    "https://www.doctolib.de/booking/{}.json".format(center))
                json_data = raw_data.json()
                if json_data.get("status") == 404:
                    print("Center {} not found".format(center))
                    print(json_data)
                    continue
                data = json_data["data"]
                visit_motives = [
                    visit_motive for visit_motive in data["visit_motives"]]
                if not visit_motives:
                    continue

                # Determine Vaccine
                vaccine_names = []
                vaccine_ids = []
                vaccine_days = []
                for visit_motive in visit_motives:
                    # If new patients are not allowed, we can not take this one
                    try:
                        if not visit_motive['allow_new_patients']:
                            continue
                    except:
                        pass

                    # Extract some information
                    visit_motive_name = visit_motive['name'].lower()
                    visit_motive_id = visit_motive['id']
                    visit_motive_covid_vaccination = False
                    try:
                        visit_motive_covid_vaccination = visit_motive['first_shot_motive']
                    except:
                        pass

                    # Check if this is a Covid vaccination
                    if "erste impfung" in visit_motive_name or \
                        "erstimpfung" in visit_motive_name or \
                        "einzelimpfung" in visit_motive_name or \
                        ("biontech" in visit_motive_name and not "zweit" in visit_motive_name) or \
                        ("astrazeneca" in visit_motive_name and not "zweit" in visit_motive_name) or \
                        ("moderna" in visit_motive_name and not "zweit" in visit_motive_name) or \
                        ("johnson" in visit_motive_name and not "zweit" in visit_motive_name) or \
                        ("janssen" in visit_motive_name and not "zweit" in visit_motive_name) or \
                            visit_motive_covid_vaccination:

                        if "biontech" in visit_motive_name:
                            vaccine_names.append("BioNTech")
                        elif "astrazeneca" in visit_motive_name:
                            vaccine_names.append("AstraZeneca")
                        elif "moderna" in visit_motive_name:
                            vaccine_names.append("Moderna")
                        elif "johnson" in visit_motive_name or "janssen" in visit_motive_name:
                            vaccine_names.append("Johnson & Johnson")
                        else:
                            vaccine_names.append("COVID-19 Impfstoff")

                        vaccine_ids.append(visit_motive_id)

                        visit_motive_day = 0
                        try:
                            if(visit_motive['vaccination_days_range'] is not None and visit_motive['vaccination_days_range'] > 0):
                                visit_motive_day = visit_motive['vaccination_days_range']
                        except:
                            pass
                        vaccine_days.append(visit_motive_day)

                if len(vaccine_ids) == 0 or len(vaccine_names) == 0:
                    continue

                places = [place for place in data["places"]]
                if not places:
                    continue

                vaccine_counter = 0
                for vaccine_id in vaccine_ids:
                    for place in places:

                        start_date = datetime.datetime.today().date().isoformat()
                        visit_motive_ids = vaccine_id
                        practice_ids = place["practice_ids"][0]
                        place_name = place["formal_name"]
                        place_address = place["full_address"]

                        agendas = [agenda for agenda in data["agendas"]
                                   if agenda["practice_id"] == practice_ids and
                                   not agenda["booking_disabled"] and
                                   visit_motive_ids in agenda["visit_motive_ids"]]
                        if not agendas:
                            continue

                        agenda_ids = "-".join([str(agenda["id"])
                                               for agenda in agendas])
                        headers = {
                            "accept": "*/*",
                            "accept-language": "en-US,en;q=0.9",
                            "cache-control": "no-cache",
                            "origin": "https://www.doctolib.de/",
                            "pragma": "no-cache",
                            "referer": "https://www.doctolib.de/",
                            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.114 Safari/537.36",
                        }
                        params = {
                            "start_date": start_date,
                            "visit_motive_ids": visit_motive_ids,
                            "agenda_ids": agenda_ids,
                            "practice_ids": practice_ids,
                            "insurance_sector": "public",
                            "destroy_temporary": "true",
                            "limit": 7
                        }

                        try:
                            response = requests.get(
                                "https://www.doctolib.de/availabilities.json",
                                params=params,
                                headers=headers
                            )
                            response.raise_for_status()
                            nb_availabilities = response.json()["total"]
                        except Exception as e:
                            print("ERROR during Doctolib check: " + str(e))
                            continue

                        vaccination_id = "{}.{}.{}".format(
                            visit_motive_ids, agenda_ids, practice_ids)

                        # Appointment(s) found
                        if nb_availabilities > 0 and vaccination_id not in already_sent_ids:
                            # Construct message
                            message = str(nb_availabilities)
                            if nb_availabilities == 1:
                                message = message + " freier Impftermin "
                            else:
                                message = message + " freie Impftermine "
                            message = message + \
                                "für {} ".format(
                                    vaccine_names[vaccine_counter])
                            if vaccine_days[vaccine_counter] != 0:
                                message = message + "mit Abstand zur 2. Impfung von {} Tagen ".format(
                                    vaccine_days[vaccine_counter])
                            if len(place_address.split(",")) == 2:
                                message = message + \
                                    "in {}".format(
                                        place_address.split(",")[1].strip())
                            message = message + \
                                ". Hier buchen: {}?pid=practice-{}".format(center_url,
                                                                           practice_ids)

                            # Print message out on server with city in front
                            print(sys.argv[1] + ": " + message)

                            # Send message to telegram channel for the specific city
                            telegram_bot.sendMessage(
                                chat_id=sys.argv[4], text=message)

                            # Do not send it out again for 60 minutes
                            already_sent_ids.append(vaccination_id)

                    vaccine_counter = vaccine_counter + 1

            except json.decoder.JSONDecodeError:
                print("Doctolib might be ko")
            except KeyError as e:
                print("KeyError: " + str(e))

except KeyboardInterrupt:
    print("Mischief managed.")
