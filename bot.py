import datetime
import requests
import telegram
import time
import json
import sys

already_sent_ids = []


def send_zollsoft_msg(vaccine_dates, vaccine_name, booking_url):
    if len(vaccine_dates) > 0:
        num_dates = len(vaccine_dates)
        message = str(num_dates)
        if num_dates == 1:
            message = message + " freier Impftermin "
        else:
            message = message + " freie Impftermine "
        message = message + "für {} in München. Verfügbare Termine: {}. Hier buchen: {}".format(
            vaccine_name, ", ".join(list(set(vaccine_dates))), booking_url)
        print(sys.argv[1] + ": " + message)
        telegram_bot.sendMessage(
            chat_id=sys.argv[4], text=message)


def check_zollsoft_api():
    unique_ids = ["6087dd08bd763", "607feb7a343fb"]
    for unique_id in unique_ids:
        booking_url = "https://onlinetermine.zollsoft.de/patientenTermine.php?uniqueident={}".format(
            unique_id)
        url = "https://onlinetermine.zollsoft.de/includes/searchTermine_app_feature.php"
        headers = {
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9",
            "cache-control": "no-cache",
            "cookie": "sec_session_id=caa60b6cfa29689425205c27f21a1ca8",
            "origin": "https://onlinetermine.zollsoft.de",
            "pragma": "no-cache",
            "referer": "https://onlinetermine.zollsoft.de/patientenTermine.php?uniqueident={}".format(unique_id),
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.114 Safari/537.36",
            "x-requested-with": "XMLHttpRequest",
        }
        payload = {
            "versichert": "",
            "terminsuche": "",
            "uniqueident": unique_id,
        }

        res = requests.post(url, headers=headers, data=payload)
        res.raise_for_status()
        result = res.json()
        nb_availabilities = len(result["termine"])

        if nb_availabilities > 0:
            # termine: [["2021\/05\/19", "12:28", "18172348282", "Lisa Schultes", "Pasing (Institutstra\u00dfe 14) | Corona-Impfung (AstraZeneca)", "7", "", "f", "f", "2021-05-16 18:44:22"]]
            biontech_dates = []
            astra_dates = []
            moderna_dates = []
            johnson_dates = []
            for entry in result["termine"]:
                date, _, _, _, location, _, _, _, _, _ = entry
                vaccination_id = "{}.{}.{}".format(
                    date, time, location)
                if vaccination_id not in already_sent_ids and "2. Corona-Impfung" not in location:
                    # Determine Vaccine
                    d = datetime.datetime.strptime(date, '%Y/%m/%d')
                    if "biontech" in location.lower():
                        biontech_dates.append(
                            datetime.date.strftime(d, "%d.%m.%y"))
                    elif "astrazeneca" in location.lower():
                        astra_dates.append(
                            datetime.date.strftime(d, "%d.%m.%y"))
                    elif "moderna" in location.lower():
                        moderna_dates.append(
                            datetime.date.strftime(d, "%d.%m.%y"))
                    elif "johnson" in location.lower() or "janssen" in location.lower():
                        johnson_dates.append(
                            datetime.date.strftime(d, "%d.%m.%y"))

                    # Do not send it out again for 60 minutes
                    already_sent_ids.append(vaccination_id)

            # Eventually send out appointments
            send_zollsoft_msg(biontech_dates, "BioNTech", booking_url)
            send_zollsoft_msg(astra_dates, "AstraZeneca", booking_url)
            send_zollsoft_msg(moderna_dates, "Moderna", booking_url)
            send_zollsoft_msg(johnson_dates, "Johnson & Johnson", booking_url)


with open(sys.argv[2]) as centers_url_txt:
    centers_urls = centers_url_txt.readlines()
centers_urls = [center.strip() for center in centers_urls
                if not center.startswith("#")]

try:
    print(sys.argv[1] + ": Searching for appointments now..")

    telegram_bot = telegram.Bot(token=sys.argv[3])
    t = time.time()

    while True:
        print(sys.argv[1] + ": Starting a new round at " +
              str(datetime.datetime.now()))

        # Eventually clear list
        if time.time()-t > 3600:
            already_sent_ids.clear()
            t = time.time()

        # For Munich, we have an additional Zollsoft API
        if sys.argv[1] == 'Munich1':
            try:
                check_zollsoft_api()
            except Exception as e:
                print(sys.argv[1] +
                      ": ERROR during Zollsoft API check - " + str(e))

        # Check Doctolib
        for center_url in centers_urls:
            try:
                center = center_url.split("/")[5]
                raw_data = requests.get(
                    "https://www.doctolib.de/booking/{}.json".format(center))
                json_data = raw_data.json()
                if json_data.get("status") == 404:
                    print(sys.argv[1] + ": " +
                          "Center {} not found".format(center))
                    print(sys.argv[1] + ": " + json_data)
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
                    if (visit_motive_covid_vaccination or
                        "erste impfung" in visit_motive_name or
                        "erstimpfung" in visit_motive_name or
                        "einzelimpfung" in visit_motive_name) and \
                        (("biontech" in visit_motive_name and not "zweit" in visit_motive_name) or
                         ("astrazeneca" in visit_motive_name and not "zweit" in visit_motive_name) or
                         ("moderna" in visit_motive_name and not "zweit" in visit_motive_name) or
                         ("johnson" in visit_motive_name and not "zweit" in visit_motive_name) or
                         ("janssen" in visit_motive_name and not "zweit" in visit_motive_name)):

                        if "biontech" in visit_motive_name:
                            vaccine_names.append("BioNTech")
                        elif "astrazeneca" in visit_motive_name:
                            vaccine_names.append("AstraZeneca")
                        elif "moderna" in visit_motive_name:
                            vaccine_names.append("Moderna")
                        elif "johnson" in visit_motive_name or "janssen" in visit_motive_name:
                            vaccine_names.append("Johnson & Johnson")
                        else:
                            continue

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
                            "limit": 14
                        }

                        try:
                            response = requests.get(
                                "https://www.doctolib.de/availabilities.json",
                                params=params,
                                headers=headers
                            )
                            response.raise_for_status()
                            nb_availabilities = response.json()["total"]
                            availabilities = response.json()["availabilities"]
                        except Exception as e:
                            print(
                                sys.argv[1] + ": ERROR during Doctolib check - " + str(e))
                            continue

                        vaccination_id = "{}.{}.{}".format(
                            visit_motive_ids, agenda_ids, practice_ids)

                        # Appointment(s) found
                        if nb_availabilities > 0 and vaccination_id not in already_sent_ids:
                            # Parse all available dates
                            all_available_dates = []
                            for availability in availabilities:
                                if len(availability["slots"]) > 0:
                                    d = datetime.datetime.strptime(
                                        availability.get("date"), '%Y-%m-%d')
                                    all_available_dates.append(
                                        datetime.date.strftime(d, "%d.%m.%y"))
                            if len(all_available_dates) == 0:
                                continue

                            # Construct message
                            message = str(nb_availabilities)
                            if nb_availabilities == 1:
                                message = message + " freier Impftermin in den nächsten 14 Tagen "
                            else:
                                message = message + " freie Impftermine in den nächsten 14 Tagen "
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
                            if all_available_dates:
                                verbose_dates = ", ".join(all_available_dates)
                                message = message + \
                                    f". Verfügbare Termine: {verbose_dates}"
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
                print(sys.argv[1] + ": Doctolib might be ko")
            except KeyError as e:
                print(sys.argv[1] + ": KeyError - " + str(e))
            except Exception as e:
                print(sys.argv[1] +
                      ": ERROR during Doctolib check - " + str(e))


except KeyboardInterrupt:
    print("Mischief managed.")
