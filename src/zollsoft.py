import datetime
import requests
from src import helper
import threading


def zollsoft_send_message(city, slot_counter, vaccine_dates, vaccine_name, booking_url):
    # Construct message
    if slot_counter == 1:
        message = f"{slot_counter} Termin "
    else:
        message = f"{slot_counter} Termine "
    vaccine_dates_str = ", ".join(sorted(set(vaccine_dates)))
    message = message + f"für {vaccine_name}. Wählbare Tage: {vaccine_dates_str}."
    message_long = message + f" Hier buchen: {booking_url}\n"

    # Print message out on server
    helper.info_log(message)

    # Send message to telegram channels for the specific city
    t_all = threading.Thread(
        target=helper.send_channel_msg, args=(city, "all", message_long)
    )
    t_all.start()
    if vaccine_name == "BioNTech" or vaccine_name == "Moderna":
        t_mrna = threading.Thread(
            target=helper.send_channel_msg, args=(city, "mrna", message_long)
        )
        t_mrna.start()
    elif vaccine_name == "AstraZeneca" or vaccine_name == "Johnson & Johnson":
        t_vec = threading.Thread(
            target=helper.send_channel_msg, args=(city, "vec", message_long)
        )
        t_vec.start()


def zollsoft_check(city):
    try:
        unique_ids = ["6087dd08bd763", "607feb7a343fb", "600af8a904bee"]
        for unique_id in unique_ids:
            booking_url = "https://onlinetermine.zollsoft.de/patientenTermine.php?uniqueident={}".format(
                unique_id
            )
            url = "https://onlinetermine.zollsoft.de/includes/searchTermine_app_feature.php"
            headers = {
                "accept": "*/*",
                "accept-language": "en-US,en;q=0.9",
                "cache-control": "no-cache",
                "cookie": "sec_session_id=caa60b6cfa29689425205c27f21a1ca8",
                "origin": "https://onlinetermine.zollsoft.de",
                "pragma": "no-cache",
                "referer": "https://onlinetermine.zollsoft.de/patientenTermine.php?uniqueident={}".format(
                    unique_id
                ),
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
                    url,
                    headers=headers,
                    data=payload,
                    timeout=helper.api_timeout_seconds,
                )
                res.raise_for_status()
                result = res.json()
            except requests.exceptions.HTTPError as e:
                helper.warn_log(
                    f"[Zollsoft] HTTP issue during fetching data [{str(e)}]"
                )
                continue
            except requests.exceptions.Timeout as e:
                helper.warn_log(f"[Zollsoft] API is currently not reachable [{str(e)}]")
                continue
            except Exception as e:
                helper.error_log(f"[Zollsoft] Error during fetch from API [{str(e)}]")
                continue

            # termine: [["2021\/05\/19", "12:28", "18172348282", "Lisa Schultes", "Pasing (Institutstra\u00dfe 14) | Corona-Impfung (AstraZeneca)", "7", "", "f", "f", "2021-05-16 18:44:22"]]
            vaccination_names_dict = {}
            available_dates_dict = {}
            vaccination_counter_dict = {}
            for entry in result["termine"]:
                date, _, _, _, title, _, _, _, _, _ = entry
                if not helper.title_is_vaccination(title):
                    continue
                available_date = datetime.datetime.strptime(date, "%Y/%m/%d").strftime(
                    "%d.%m.%Y"
                )
                if not title in available_dates_dict:
                    available_dates_dict[title] = []
                available_dates_dict[title].append(available_date)
                if not title in vaccination_names_dict:
                    vaccination_names_dict[title] = []
                vaccination_names_dict[title].append(title)
                if not title in vaccination_counter_dict:
                    vaccination_counter_dict[title] = 0
                vaccination_counter_dict[title] = vaccination_counter_dict[title] + 1

            for vaccine_name in vaccination_names_dict.keys():
                # Lookup vaccination count
                slot_counter = vaccination_counter_dict[vaccine_name]
                available_dates = available_dates_dict[vaccine_name]
                vaccination_id = f"zollsoft.{unique_id}.{vaccine_name}"
                if not vaccination_id in helper.airtable_id_count_dict:
                    helper.airtable_id_count_dict[vaccination_id] = 0
                vaccination_count = helper.airtable_id_count_dict[vaccination_id]

                # No slots
                if slot_counter == 0:
                    if vaccination_count > 0:
                        helper.delete_airtable_entry(vaccination_id)
                    continue

                vaccine_compound = helper.get_vaccine_compound(vaccine_name)
                vaccine_type = helper.get_vaccine_type(vaccine_name)
                if "|" in vaccine_name:
                    try:
                        practice_address = vaccine_name.split("|")[0]
                        vaccine_name = vaccine_name.split("|")[1]
                        practice = practice_address.split("(")[0]
                        address = practice_address.split("(")[1].split(")")[0]
                    except Exception:
                        practice = "Verschiedene Praxen"
                        address = "Verschiedene Standorte"
                else:
                    practice = "Verschiedene Praxen"
                    address = "Verschiedene Standorte"

                # Update Airtable
                if vaccination_count == 0:
                    helper.create_airtable_entry(
                        vaccination_id,
                        vaccine_name,
                        slot_counter,
                        booking_url,
                        practice,
                        vaccine_type,
                        vaccine_compound,
                        available_dates,
                        address,
                        "80331 München",
                        "Zollsoft",
                    )
                elif slot_counter != vaccination_count:
                    helper.update_airtable_entry(
                        vaccination_id,
                        slot_counter,
                        available_dates,
                    )

                # Send appointments to Doctolib
                if vaccination_count == 0 or slot_counter > vaccination_count:
                    zollsoft_send_message(
                        city,
                        slot_counter,
                        available_dates,
                        vaccine_name,
                        booking_url,
                    )

                helper.airtable_id_count_dict[vaccination_id] = slot_counter

    except Exception as e:
        helper.error_log(f"[Zollsoft] General Error [{str(e)}]")
