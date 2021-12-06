import datetime
import requests
from src import helper
import threading


def zollsoft_send_message(city, slot_counter, vaccine_dates, vaccine_name, booking_url):
    # Construct message
    if slot_counter == 1:
        message = f'{slot_counter} freier Impftermin '
    else:
        message = f'{slot_counter} freie Impftermine '
    vaccine_dates_str = ", ".join(sorted(set(vaccine_dates)))
    message = message + \
        f'für {vaccine_name}. Wählbare Tage: {vaccine_dates_str}.'
    message_long = message + f' Hier buchen: {booking_url}\n'

    # Print message out on server
    helper.info_log(message)

    # Send message to telegram channels for the specific city
    t_all = threading.Thread(
        target=helper.send_channel_msg, args=(city, 'all', message_long))
    t_all.start()
    if vaccine_name == 'BioNTech' or vaccine_name == 'Moderna':
        t_mrna = threading.Thread(
            target=helper.send_channel_msg, args=(city, 'mrna', message_long))
        t_mrna.start()
    elif vaccine_name == 'AstraZeneca' or vaccine_name == 'Johnson & Johnson':
        t_vec = threading.Thread(
            target=helper.send_channel_msg, args=(city, 'vec', message_long))
        t_vec.start()


def zollsoft_check(city):
    try:
        unique_ids = ["6087dd08bd763", "607feb7a343fb", "600af8a904bee"]
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

            try:
                res = helper.post(
                    url, headers=headers, data=payload, timeout=helper.api_timeout_seconds)
                res.raise_for_status()
            except requests.exceptions.HTTPError as e:
                helper.warn_log(
                    f'[Zollsoft] HTTP issue during fetching data [{str(e)}]')
                continue
            except requests.exceptions.Timeout as e:
                helper.warn_log(
                    f'[Zollsoft] API is currently not reachable [{str(e)}]')
                continue
            except Exception as e:
                helper.error_log(
                    f'[Zollsoft] Error during fetch from API [{str(e)}]')
                continue

            result = res.json()
            nb_availabilities = len(result["termine"])

            if nb_availabilities > 0:
                vaccination_counter = 0
                for entry in result["termine"]:
                    _, _, _, _, location, _, _, _, _, _ = entry
                    vaccination_counter = vaccination_counter + 1
                if vaccination_counter <= 1:
                    continue
                # termine: [["2021\/05\/19", "12:28", "18172348282", "Lisa Schultes", "Pasing (Institutstra\u00dfe 14) | Corona-Impfung (AstraZeneca)", "7", "", "f", "f", "2021-05-16 18:44:22"]]
                biontech_dates = []
                biontech_counter = 0
                astra_dates = []
                astra_counter = 0
                moderna_dates = []
                moderna_counter = 0
                johnson_dates = []
                johnson_counter = 0
                for entry in result["termine"]:
                    date, time, _, _, location, _, _, _, _, _ = entry
                    vaccination_id = "{}.{}.{}".format(
                        date, time, location)
                    if vaccination_id not in helper.already_sent_ids and \
                            not "antigen" in location.lower() and not "antikörper" in location.lower() and \
                            not "pcr" in location.lower() and not "test" in location.lower():
                        # Determine Vaccine
                        d = datetime.datetime.strptime(date, '%Y/%m/%d')
                        if "biontech" in location.lower() or "impfungen" in location.lower():
                            biontech_counter = biontech_counter + 1
                            biontech_dates.append(
                                datetime.date.strftime(d, "%d.%m.%y"))
                        elif "astrazeneca" in location.lower():
                            astra_counter = astra_counter + 1
                            astra_dates.append(
                                datetime.date.strftime(d, "%d.%m.%y"))
                        elif "moderna" in location.lower():
                            moderna_counter = moderna_counter + 1
                            moderna_dates.append(
                                datetime.date.strftime(d, "%d.%m.%y"))
                        elif ("johnson" in location.lower() or "janssen" in location.lower()) and not "bion" in location.lower():
                            johnson_counter = johnson_counter + 1
                            johnson_dates.append(
                                datetime.date.strftime(d, "%d.%m.%y"))
                        else:
                            helper.warn_log(
                                f'[Zollsoft] Unknown vaccination: {location.lower()}')

                        helper.already_sent_ids.append(vaccination_id)

                # Eventually send out appointments
                if biontech_counter > 0:
                    zollsoft_send_message(
                        city, biontech_counter, biontech_dates, "BioNTech", booking_url)
                if astra_counter > 0:
                    zollsoft_send_message(
                        city, astra_counter, astra_dates, "AstraZeneca", booking_url)
                if moderna_counter > 0:
                    zollsoft_send_message(
                        city, moderna_counter, moderna_dates, "Moderna", booking_url)
                if johnson_counter > 0:
                    zollsoft_send_message(
                        city, johnson_counter, johnson_dates, "Johnson & Johnson", booking_url)

    except Exception as e:
        helper.error_log(f'[Zollsoft] General Error [{str(e)}]')
