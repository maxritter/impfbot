import datetime
import requests
import telegram
import time
import json
import sys

already_sent_ids = []

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
                                 if "erste impfung" in visit_motive["name"].lower() or
                                    "erstimpfung" in visit_motive["name"].lower() or
                                    "einzelimpfung" in visit_motive["name"].lower() or
                                    ("biontech" in visit_motive["name"].lower() and not "zweit" in visit_motive["name"].lower()) or
                                    ("astrazeneca" in visit_motive["name"].lower() and not "zweit" in visit_motive["name"].lower()) or
                                    ("moderna" in visit_motive["name"].lower() and not "zweit" in visit_motive["name"].lower()) or
                                    ("johnson" in visit_motive["name"].lower() and not "zweit" in visit_motive["name"].lower()) or
                                    ("janssen" in visit_motive["name"].lower() and not "zweit" in visit_motive["name"].lower())]
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
                        "agenda_ids": agenda_ids,
                        "practice_ids": practice_ids,
                        "limit": 21
                    }
                    response = requests.get(
                        "https://www.doctolib.de/availabilities.json",
                        params=params,
                    )
                    response.raise_for_status()
                    nb_availabilities = response.json()["total"]

                    vaccination_id = "{}.{}.{}".format(
                        visit_motive_ids, agenda_ids, practice_ids)
                    if nb_availabilities > 0 and vaccination_id not in already_sent_ids:

                        if nb_availabilities == 1:
                            message = str(nb_availabilities) + \
                                " freier Impftermin: " + center_url + \
                                "?pid=practice-"+str(practice_ids)
                        else:
                            message = str(nb_availabilities) + \
                                " freie Impftermine: " + center_url + \
                                "?pid=practice-"+str(practice_ids)

                        print(sys.argv[1] + ": " + message)
                        telegram_bot.sendMessage(
                            chat_id=sys.argv[4], text=message)
                        already_sent_ids.append(vaccination_id)

            except json.decoder.JSONDecodeError:
                print("Doctolib might be ko")
            except KeyError as e:
                print("KeyError: " + str(e))

except KeyboardInterrupt:
    print("Mischief managed.")
