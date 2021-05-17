import datetime
import requests
from pushover import Client
import time
import json

already_sent_ids = []

PUSHOVER_TOKEN = "aaa8hh4sncnbwhxx9hz9xwoknes7g1"
PUSHOVER_USER = "ufpz29yh4cmp626isi4sv3jvnntdj4"

with open('centers-url.txt') as centers_url_txt:
    centers_urls = centers_url_txt.readlines()
centers_urls = [center.strip() for center in centers_urls
                if not center.startswith("#")]

try:
    print("COVID-19 Vaccination Finder by Max Ritter")
    print("Searching for appointments now..")
    client = Client(PUSHOVER_USER, api_token=PUSHOVER_TOKEN)
    while True:
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

                visit_motives = [visit_motive for visit_motive in data["visit_motives"]
                                 if "Erste Impfung" in visit_motive["name"] or \
                                    "Erstimpfung" in visit_motive["name"] or \
                                    "1. Impfung" in visit_motive["name"] or \
                                    "1.Impfung" in visit_motive["name"]]
                if not visit_motives:
                    continue

                places = [place for place in data["places"]]
                if not places:
                    continue

                for place in places:

                    start_date = datetime.datetime.today().date().isoformat()
                    visit_motive_ids = visit_motives[0]["id"]
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
                    params = {
                        "start_date": start_date,
                        "visit_motive_ids": visit_motive_ids,
                        "insurance_sector": "public",
                        "allow_new_patients": True,
                        "agenda_ids": agenda_ids,
                        "practice_ids": practice_ids,
                        "limit": 7
                    }
                    response = requests.get(
                        "https://www.doctolib.de/availabilities.json",
                        params=params,
                    )
                    response.raise_for_status()
                    nb_availabilities = response.json()["total"]

                    message = datetime.datetime.now().strftime("%H:%M:%S") + " " + str(nb_availabilities) + \
                        " new appointments found: " + center_url + \
                        "?pid=practice-"+str(practice_ids)
                    if nb_availabilities > 0 and visit_motive_ids not in already_sent_ids:
                        already_sent_ids.append(visit_motive_ids)
                        print(message)
                        client.send_message(message, title="Covid-19 Vaccination MUC")

            except json.decoder.JSONDecodeError:
                print("Doctolib might be ko")
            except KeyError as e:
                print("KeyError: " + str(e))

        time.sleep(60)
except KeyboardInterrupt:
    print("Mischief managed.")
