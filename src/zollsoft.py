import datetime
import requests
import time
from src import helper


def zollsoft_send_message(city, vaccine_dates, vaccine_name, booking_url):
    if len(vaccine_dates) > 0:
        message = "Freie Impftermine für {} in München. Wählbare Tage: {}. Hier buchen: {}".format(
            vaccine_name, ", ".join(sorted(set(vaccine_dates))), booking_url)

        # Print message out on server
        helper.info_log(message)

        # Send message to telegram channels for the specific city
        helper.send_telegram_msg(city, 'all', message)
        if vaccine_name == 'BioNTech' or vaccine_name == 'Moderna':
            helper.send_telegram_msg(city, 'mrna', message)
        elif vaccine_name == 'AstraZeneca' or vaccine_name == 'Johnson & Johnson':
            helper.send_telegram_msg(city, 'vec', message)


def zollsoft_check(city):
    try:
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

            try:
                res = requests.post(
                    url, headers=headers, data=payload, timeout=helper.api_timeout_seconds)
                res.raise_for_status()
            except requests.exceptions.HTTPError as e:
                helper.warn_log(
                    f'[Zollsoft] HTTP issue during fetching data [{str(e)}]')
                return
            except requests.exceptions.Timeout as e:
                helper.warn_log(
                    f'[Zollsoft] API is currently not reachable [{str(e)}]')
                return
            except Exception as e:
                helper.error_log(
                    f'[Zollsoft] Error during fetch from API [{str(e)}]')
                return

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
                    if vaccination_id not in helper.already_sent_ids and "2. Corona-Impfung" not in location:
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
                        helper.already_sent_ids.append(vaccination_id)

                # Eventually send out appointments
                zollsoft_send_message(
                    city, biontech_dates, "BioNTech", booking_url)
                zollsoft_send_message(
                    city, astra_dates, "AstraZeneca", booking_url)
                zollsoft_send_message(
                    city, moderna_dates, "Moderna", booking_url)
                zollsoft_send_message(
                    city, johnson_dates, "Johnson & Johnson", booking_url)

    except Exception as e:
        helper.error_log(f'[Zollsoft] General Error [{str(e)}]')
