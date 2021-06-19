import requests
import html
import re
import json
import datetime
from src import helper, database

headers = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "cache-control": "no-cache",
    "cookie": "PHPSESSID=f3jcojijof3kjlr52ri9f5ld17",
    "origin": "https://termin.dachau-med.de",
    "pragma": "no-cache",
    "referer": "https://termin.dachau-med.de/impfung/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.114 Safari/537.36",
    "x-requested-with": "XMLHttpRequest",
}

session = requests.Session()

sln_list = [
    23865,
    15087,
    27,
    29,
    33,
    23839,
    18,
    23842,
    39,
    19,
    31,
    35,
    22445,
    23799,
    19,
    23796,
    33,
    22456,
    18,
    23792,
    27,
    22448,
    29,
    31,
    18,
    16069,
    16072,
    16075,
    19,
    27,
    39,
    35,
    29,
    31,
    33,
    16066
]
vaccine_list = [
    "Johnson & Johnson",
    "Johnson & Johnson",
    "Johnson & Johnson",
    "Johnson & Johnson",
    "Johnson & Johnson",
    "Johnson & Johnson",
    "Johnson & Johnson",
    "Johnson & Johnson",
    "Johnson & Johnson",
    "Johnson & Johnson",
    "Johnson & Johnson",
    "Johnson & Johnson",
    "BioNTech",
    "BioNTech",
    "BioNTech",
    "BioNTech",
    "BioNTech",
    "BioNTech",
    "BioNTech",
    "BioNTech",
    "BioNTech",
    "BioNTech",
    "BioNTech",
    "BioNTech",
    "BioNTech (2. Impfung)",
    "BioNTech (2. Impfung)",
    "BioNTech (2. Impfung)",
    "BioNTech (2. Impfung)",
    "BioNTech (2. Impfung)",
    "BioNTech (2. Impfung)",
    "BioNTech (2. Impfung)",
    "BioNTech (2. Impfung)",
    "BioNTech (2. Impfung)",
    "BioNTech (2. Impfung)",
    "BioNTech (2. Impfung)",
    "BioNTech (2. Impfung)"
]

location_list = [
    "MVZ Dachau (EG) [85221 Dachau]",
    "Praxis Rembold/Rinck-Pfister/Giuliani [85221 Dachau]",
    "Medizinisches Zentrum Eching [85386 Eching]",
    "Medizinisches Zentrum Neufahrn-Eching [85375 Neufahrn]",
    "MVZ Dachau (1. OG) [85221 Dachau]",
    "MVZ Dachau (2. OG) [85221 Dachau]",
    "MVZ Dachau (3. OG) [85221 Dachau]",
    "MVZ Patientenzentrum [85221 Dachau]",
    "Medizinisches Zentrum Allach [80999 München]",
    "Praxis Altstadt [85221 Dachau]",
    "Praxis Bergkirchen [85232 Bergkirchen]",
    "Praxis Sulzemoos [85254 Sulzemoos]",
    "MVZ Dachau (EG) [85221 Dachau]",
    "Praxis Sulzemoos [85254 Sulzemoos]",
    "Praxis Altstadt [85221 Dachau]",
    "Praxis Rembold/Rinck-Pfister/Giuliani [85221 Dachau]",
    "MVZ Dachau (1. OG) [85221 Dachau]",
    "MVZ Dachau (2. OG) [85221 Dachau]",
    "MVZ Dachau (3. OG) [85221 Dachau]",
    "Medizinisches Zentrum Allach [80999 München]",
    "Medizinisches Zentrum Eching [85386 Eching]",
    "MVZ Patientenzentrum [85221 Dachau]",
    "Medizinisches Zentrum Neufahrn-Eching [85375 Neufahrn]",
    "Praxis Bergkirchen [85232 Bergkirchen]",
    "MVZ Dachau (EG) [85221 Dachau]",
    "Praxis Bergkirchen [85232 Bergkirchen]",
    "Praxis Sulzemoos [85254 Sulzemoos]",
    "Praxis Rembold/Rinck-Pfister/Giuliani [85221 Dachau]",
    "MVZ Dachau (1. OG) [85221 Dachau]",
    "MVZ Dachau (2. OG) [85221 Dachau]",
    "MVZ Dachau (3. OG) [85221 Dachau]",
    "MVZ Patientenzentrum [85221 Dachau]",
    "Medizinisches Zentrum Allach [80999 München]",
    "Medizinisches Zentrum Eching [85386 Eching]",
    "Medizinisches Zentrum Neufahrn-Eching [85375 Neufahrn]",
    "Praxis Altstadt [85221 Dachau]"
]

def dachau_check(city):
    global session

    try:
        # Go through all possible appointments
        for i in range(0, len(sln_list)):
            # Construct payload
            payload = {'sln[shop]': str(sln_list[i]),
                       'sln_step_page': 'shop',
                       'submit_shop': 'next',
                       'action': 'salon',
                       'method': 'salonStep',
                       'security': 'b0d349bf50'
                       }

            # Do the POST request
            vaccine_name = vaccine_list[i]
            if vaccine_name == "Johnson & Johnson":
                url = "impfungen02"
            elif vaccine_name == "BioNTech":
                url = "impfungen03"
            elif vaccine_name == "BioNTech (2. Impfung)":
                url = "impfung"
            else:
                continue
            try:
                res = session.post(
                    f'https://termin.dachau-med.de/{url}/wp-admin/admin-ajax.php', headers=headers, data=payload)
                res.raise_for_status()
            except requests.exceptions.HTTPError as e:
                helper.warn_log(
                    f'[Dachau] HTTP issue during API check [{str(e)}]')
                session = requests.Session()
                continue
            except requests.exceptions.Timeout as e:
                helper.warn_log(
                    f'[Dachau] Timeout during API check [{str(e)}]')
                session = requests.Session()
                continue
            except Exception as e:
                helper.error_log(
                    f'[Dachau] Error during API check [{str(e)}]')
                session = requests.Session()
                continue

            # Parse response and check if it has appointments
            try:
                data = res.json()
                raw_text = str(html.unescape(data["content"]))
                start = 'data-intervals=\"'
                end = 'input type=\"hidden\"'
                start_index = re.search(start, raw_text).start()
                end_index = re.search(end, raw_text).end()
                section_of_text = raw_text[start_index:end_index]
                remove_end = section_of_text.split('">', 1)[0]
                string_data = remove_end.split('data-intervals="')[1]
                json_data = json.loads(string_data)
            except:
                continue
            
            # Create metadata
            available_dates = []
            for date_str in json_data['dates']:
                d = datetime.datetime.strptime(date_str, '%Y-%m-%d')
                available_dates.append(datetime.date.strftime(d, "%d.%m.%y"))

            slot_counter = len(json_data['times'])

            # Construct message
            if slot_counter == 1:
                message = f'{slot_counter} freier Impftermin '
            else:
                message = f'{slot_counter} freie Impftermine '
            message = message + f'für {vaccine_name} in {location_list[i]}'

            verbose_dates = ", ".join(sorted(set(available_dates)))
            message = message + \
                f". Wählbare Tage: {verbose_dates}."
            message_long = message + " Hier buchen und Praxis in der Liste auswählen: "

            if vaccine_name == "Johnson & Johnson":
                message_long = message_long + "https://termin.dachau-med.de/impfungen02/"
            elif vaccine_name == "BioNTech":
                message_long = message_long + "https://termin.dachau-med.de/impfungen03/"
            elif vaccine_name == "BioNTech (2. Impfung)":
                message_long = message_long + "https://termin.dachau-med.de/impfung/"

            # Print message out on server
            helper.info_log(message_long)

            # Send message to telegram channels for the specific city
            if vaccine_name == 'BioNTech' or vaccine_name == 'BioNTech (2. Impfung)':
                helper.send_channel_msg(city, 'mrna', message_long)
                helper.send_channel_msg(city, 'all', message_long)
                database.insert_vaccination(
                    vaccine_name, slot_counter, city, "dachau")
            elif vaccine_name == 'Johnson & Johnson':
                helper.send_channel_msg(city, 'vec', message_long)
                helper.send_channel_msg(city, 'all', message_long)
                database.insert_vaccination(
                    vaccine_name, slot_counter, city, "dachau")
    except Exception as e:
        helper.error_log(f'[Dachau] General Error [{str(e)}]')
