import requests
import html
import re
import datetime
import json
from src import helper

headers = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "cache-control": "no-cache",
    "cookie": "PHPSESSID=fnj8qu0r38q3qi4gh2pdq0s1to",
    "origin": "https://termin.dachau-med.de",
    "pragma": "no-cache",
    "referer": "https://termin.dachau-med.de/impfung/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.114 Safari/537.36",
    "x-requested-with": "XMLHttpRequest",
}

session = helper.DelayedSession()

sln_list = [18, 19, 27, 39, 16072, 16069, 16066, 42608, 31, 33, 29, 16075, 35]

practice_list = [
    "MVZ Dachau (EG)",
    "MVZ Dachau (1. OG)",
    "MVZ Dachau (2. OG)",
    "MVZ Dachau (3. OG)",
    "Praxis Sulzemoos",
    "Praxis Bergkirchen" "Praxis Altstadt 01",
    "Praxis Altstadt 02",
    "Medizinisches Zentrum Eching",
    "Medizinisches Zentrum Neufahrn",
    "Medizinisches Zentrum Allach",
    "Praxis Rembold/Rinck-Pfister/Giuliani",
    "MVZ Patientenzentrum",
]

location_list = [
    "85221 Dachau",
    "85254 Sulzemoos",
    "85221 Dachau",
    "85221 Dachau",
    "85221 Dachau",
    "85221 Dachau",
    "85221 Dachau",
    "85221 Dachau",
    "80999 München",
    "85386 Eching",
    "85221 Dachau",
    "85375 Neufahrn",
    "85232 Bergkirchen",
]


def dachau_check(city):
    global session

    try:
        # Go through all possible appointments
        for i in range(0, len(sln_list)):
            # Construct payload
            payload = {
                "sln[shop]": str(sln_list[i]),
                "sln_step_page": "shop",
                "submit_shop": "next",
                "action": "salon",
                "method": "salonStep",
                "security": "b0d349bf50",
            }

            # Do the POST request
            try:
                res = session.post(
                    f"https://termin.dachau-med.de/impfung/wp-admin/admin-ajax.php",
                    headers=headers,
                    data=payload,
                )
                res.raise_for_status()
            except requests.exceptions.HTTPError as e:
                helper.warn_log(f"[Dachau] HTTP issue during API check [{str(e)}]")
                session = helper.DelayedSession()
                continue
            except requests.exceptions.Timeout as e:
                helper.warn_log(f"[Dachau] Timeout during API check [{str(e)}]")
                session = helper.DelayedSession()
                continue
            except Exception as e:
                helper.error_log(f"[Dachau] Error during API check [{str(e)}]")
                session = helper.DelayedSession()
                continue

            # Parse response and check if it has appointments
            try:
                data = res.json()
                raw_text = str(html.unescape(data["content"]))
                start = 'data-intervals="'
                end = 'input type="hidden"'
                start_index = re.search(start, raw_text).start()
                end_index = re.search(end, raw_text).end()
                section_of_text = raw_text[start_index:end_index]
                remove_end = section_of_text.split('">', 1)[0]
                string_data = remove_end.split('data-intervals="')[1]
                json_data = json.loads(string_data)
            except Exception as e:
                continue

            # Lookup vaccination count
            vaccination_id = f"dachau.{sln_list[i]}"
            if not vaccination_id in helper.airtable_id_count_dict:
                helper.airtable_id_count_dict[vaccination_id] = 0
            vaccination_count = helper.airtable_id_count_dict[vaccination_id]

            # Check how many slots we have
            slot_counter = len(json_data["times"])
            if slot_counter == 0:
                if vaccination_count > 0:
                    helper.delete_airtable_entry(vaccination_id)
                continue

            # Parse dates
            available_dates = []
            for date in json_data["dates"]:
                available_date = datetime.datetime.strptime(date, "%Y-%m-%d").strftime(
                    "%d.%m.%Y"
                )
                available_dates.append(available_date)

            # Update Airtable
            if vaccination_count == 0:
                helper.create_airtable_entry(
                    vaccination_id,
                    "Erst-, Zweit oder Auffrischungsimpfung (BioNTech)",
                    slot_counter,
                    "https://termin.dachau-med.de/impfung/",
                    practice_list[i],
                    "Alle Impfungen",
                    "BioNTech",
                    available_dates,
                    "",
                    location_list[i],
                    "Dachau",
                )
            elif slot_counter != vaccination_count:
                helper.update_airtable_entry(
                    vaccination_id,
                    slot_counter,
                    available_dates,
                )

            # Send appointments to Doctolib
            if vaccination_count == 0 or slot_counter > vaccination_count:
                # Construct message
                if slot_counter == 1:
                    message = f"{slot_counter} Termin "
                else:
                    message = f"{slot_counter} Termine "
                message = (
                    message
                    + f"für BioNTech (Erst-, Zweit oder Auffrischungsimpfung) in {location_list[i]}"
                )
                verbose_dates = ", ".join(sorted(set(available_dates)))
                message = message + f". Wählbare Tage: {verbose_dates}."
                message_long = (
                    message + f" {practice_list[i].upper()} in der Liste auswählen: "
                )
                message_long = message_long + "https://termin.dachau-med.de/impfung/"

                # Print message out on server
                helper.info_log(message)

                # Send message to telegram channels for the specific city
                helper.send_channel_msg(city, "mrna", message_long)
                helper.send_channel_msg(city, "all", message_long)

            helper.airtable_id_count_dict[vaccination_id] = slot_counter

    except Exception as e:
        helper.error_log(f"[Dachau] General Error [{str(e)}]")
