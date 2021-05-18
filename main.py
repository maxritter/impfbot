import datetime
import requests
import telegram
import time
import json
import pytz

already_sent_ids = []

timezone = pytz.timezone("Europe/Berlin")

TELEGRAM_MUC_TOKEN = "1851471777:AAHqNrWPAuvr7w5QRrjrnGvr0VJaWVC4BCo"
TELEGRAM_MUC_CHAT_ID = "-1001464001536"

with open('centers-url.txt') as centers_url_txt:
    centers_urls = centers_url_txt.readlines()
centers_urls = [center.strip() for center in centers_urls
                if not center.startswith("#")]

try:
    print("COVID-19 Vaccination Finder by Max Ritter")
    print("Searching for appointments now..")
    telegram_bot = telegram.Bot(token=TELEGRAM_MUC_TOKEN)
    t=time.time()
    while True:
        # Eventually clear list
        if time.time()-t>3600:
            print("Clearing list now..")
            already_sent_ids.clear()
            t=time.time()

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
                                 if "erste impfung" in visit_motive["name"].lower() or \
                                    "erstimpfung" in visit_motive["name"].lower() or \
                                    "1. impfung" in visit_motive["name"].lower() or \
                                    "1.impfung" in visit_motive["name"].lower() or \
                                    ("biontech" in visit_motive["name"].lower() and not ("zweit" in visit_motive["name"].lower() or "2." in visit_motive["name"].lower())) or \
                                    ("astrazeneca" in visit_motive["name"].lower() and not ("zweit" in visit_motive["name"].lower() or "2." in visit_motive["name"].lower())) or \
                                    ("moderna" in visit_motive["name"].lower() and not ("zweit" in visit_motive["name"].lower() or "2." in visit_motive["name"].lower())) or \
                                    ("johnson" in visit_motive["name"].lower() and not ("zweit" in visit_motive["name"].lower() or "2." in visit_motive["name"].lower()))]
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

                    d = datetime.datetime.now()
                    message = timezone.localize(d).strftime("%H:%M:%S") + " - " + str(nb_availabilities) + \
                        " freie Impftermine: " + center_url + \
                        "?pid=practice-"+str(practice_ids)

                    vaccination_id = "{}.{}.{}".format(visit_motive_ids, agenda_ids, practice_ids)
                    if nb_availabilities > 0 and vaccination_id not in already_sent_ids:
                        already_sent_ids.append(vaccination_id)
                        print(message)
                        telegram_bot.sendMessage(chat_id=TELEGRAM_MUC_CHAT_ID, text=message)

            except json.decoder.JSONDecodeError:
                print("Doctolib might be ko")
            except KeyError as e:
                print("KeyError: " + str(e))

except KeyboardInterrupt:
    print("Mischief managed.")
