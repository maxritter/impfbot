import arrow
import requests
import threading
import datetime
from src import helper


def samedi_send_message(city, slot_counter, vaccine_dates, vaccine_name, booking_url):
    # Construct message
    if slot_counter == 1:
        message = f'{slot_counter} Termin '
    else:
        message = f'{slot_counter} Termine '
    vaccine_dates_str = ", ".join(sorted(set(vaccine_dates)))
    message = message + \
        f'für {str(vaccine_name).upper()}. Verfügbare Termine: {vaccine_dates_str}.'
    message_long = message + f' Hier buchen: {booking_url}'

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


def samedi_check(city):
    headers = {
        "accept": "application/json",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
        "connection": "keep-alive",
        "host": "patient.samedi.de",
                "origin": "https://termin.samedi.de",
                "pragma": "no-cache",
                "referer": "https://termin.samedi.de/",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.114 Safari/537.36"
    }

    try:
        client_id = "8f0hsw1v0x676r5pqbf4fecv3fo7s5l"
        date_start = arrow.now().format('YYYY-MM-DD')
        date_end = arrow.now().shift(days=14).format('YYYY-MM-DD')
        event_urls = [
            "https://termin.samedi.de/b/praxis-dr-abbushi/impfen1astra/1-termin/0-astrazeneca-1-termin?insuranceId=public",
            "https://termin.samedi.de/b/praxis-dr-abbushi/impfen1jj/1-termin-johnson-johnson/astrazeneca-1-termin--4?insuranceId=public",
            "https://termin.samedi.de/b/praxis-dr-abbushi/impfen1bion/1-termin-biontech/biontech-1-termin--3?insuranceId=public"
        ]
        event_names = ["AstraZeneca", "Johnson & Johnson", "BioNTech"]
        event_category_ids = ["90357", "92294", "92289"]
        event_type_ids = ["252282", "254522", "254916"]

        # Go through the different vaccines and construct the URL
        for event_counter in range(0, len(event_names)):
            url = f"https://patient.samedi.de/api/booking/v3/times?client_id={client_id}&api_key=TESTING&source=bw_v3&event_category_id={event_category_ids[event_counter]}&event_type_id={event_type_ids[event_counter]}&from={date_start}&to={date_end}&insurance_id=public&born_on=1992-09-22"

            # Send the GET request
            try:
                res = helper.get(
                    url, headers=headers, timeout=helper.api_timeout_seconds)
                res.raise_for_status()
            except requests.exceptions.HTTPError as e:
                continue
            except requests.exceptions.Timeout as e:
                helper.warn_log(
                    f'[Samedi] API is currently not reachable [{str(e)}]')
                continue
            except Exception as e:
                helper.error_log(
                    f'[Samedi] Error during fetch from API [{str(e)}]')
                continue

            # Parse response and check if there are availabilities
            result = res.json()
            nb_availabilities = len(result["data"])
            if nb_availabilities == 0:
                continue

            # Fetch all slots
            vaccine_dates = []
            for availability_counter in range(0, nb_availabilities):
                try:
                    # Create datetime and vaccination ID
                    dt_naive = datetime.datetime.strptime(
                        result["data"][availability_counter]["time"], "%Y-%m-%dT%H:%M:%S%z")
                    dt = datetime.datetime.combine(
                        dt_naive.date(), dt_naive.time(), datetime.timezone.utc)
                    vaccination_id = "{}.{}.{}".format(
                        event_category_ids[event_counter], event_type_ids[event_counter], dt.strftime("%d.%m.%y-%H:%M"))

                    # If appointment has not been sent out already
                    if vaccination_id not in helper.already_sent_ids:
                        vaccine_dates.append(dt.strftime("%d.%m.%y"))
                        helper.already_sent_ids.append(vaccination_id)
                except Exception as e:
                    helper.error_log(
                        f'[Samedi] Error getting time for appointment [{str(e)}]')
                    continue
            if len(vaccine_dates) == 0:
                continue

            # Send the message out and add to DB
            samedi_send_message(city, len(vaccine_dates), vaccine_dates,
                                event_names[event_counter], event_urls[event_counter])

    except Exception as e:
        helper.error_log(f'[Samedi] General Error [{str(e)}]')
