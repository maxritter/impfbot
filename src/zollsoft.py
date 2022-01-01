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
    message = (
        message
        + f"für {vaccine_name} (Alle Impfungen) in München. Wählbare Tage: {vaccine_dates_str}."
    )
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

            slot_counter = 0
            for entry in result["termine"]:
                _, _, _, _, location, _, _, _, _, _ = entry
                slot_counter = slot_counter + 1

            if slot_counter > 0:
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
                    vaccination_id = "{}.{}.{}".format(date, time, location)
                    if (
                        not "antigen" in location.lower()
                        and not "antikörper" in location.lower()
                        and not "pcr" in location.lower()
                        and not "test" in location.lower()
                    ):
                        # Determine Vaccine
                        d = datetime.datetime.strptime(date, "%Y/%m/%d")
                        if (
                            "biontech" in location.lower()
                            or "impfungen" in location.lower()
                        ):
                            biontech_counter = biontech_counter + 1
                            biontech_dates.append(datetime.date.strftime(d, "%d.%m.%Y"))
                        elif "astrazeneca" in location.lower():
                            astra_counter = astra_counter + 1
                            astra_dates.append(datetime.date.strftime(d, "%d.%m.%Y"))
                        elif "moderna" in location.lower():
                            moderna_counter = moderna_counter + 1
                            moderna_dates.append(datetime.date.strftime(d, "%d.%m.%Y"))
                        elif (
                            "johnson" in location.lower()
                            or "janssen" in location.lower()
                        ) and not "bion" in location.lower():
                            johnson_counter = johnson_counter + 1
                            johnson_dates.append(datetime.date.strftime(d, "%d.%m.%Y"))
                        else:
                            helper.warn_log(
                                f"[Zollsoft] Unknown vaccination: {location.lower()}"
                            )

            # BioNTech
            vaccination_id = f"zollsoft.{unique_id}.biontech"
            if not vaccination_id in helper.airtable_id_count_dict:
                helper.airtable_id_count_dict[vaccination_id] = 0
            vaccination_count = helper.airtable_id_count_dict[vaccination_id]
            if biontech_counter > 0:
                # Update Airtable
                if vaccination_count == 0:
                    helper.create_airtable_entry(
                        vaccination_id,
                        "Alle Impfungen (BioNTech)",
                        biontech_counter,
                        booking_url,
                        "",
                        "Alle Impfungen",
                        "BioNTech",
                        biontech_dates,
                        "",
                        "München",
                        "Zollsoft",
                    )
                elif biontech_counter != vaccination_count:
                    helper.update_airtable_entry(
                        vaccination_id,
                        biontech_counter,
                        biontech_dates,
                    )

                # Send appointments to Doctolib
                if vaccination_count == 0 or biontech_counter > vaccination_count:
                    zollsoft_send_message(
                        city, biontech_counter, biontech_dates, "BioNTech", booking_url
                    )
                helper.airtable_id_count_dict[vaccination_id] = biontech_counter
            elif vaccination_count > 0:
                helper.delete_airtable_entry(vaccination_id)

            # AstraZeneca
            vaccination_id = f"zollsoft.{unique_id}.astra"
            if not vaccination_id in helper.airtable_id_count_dict:
                helper.airtable_id_count_dict[vaccination_id] = 0
            vaccination_count = helper.airtable_id_count_dict[vaccination_id]
            if astra_counter > 0:
                # Update Airtable
                if vaccination_count == 0:
                    helper.create_airtable_entry(
                        vaccination_id,
                        "Alle Impfungen (AstraZeneca)",
                        astra_counter,
                        booking_url,
                        "",
                        "Alle Impfungen",
                        "AstraZeneca",
                        astra_dates,
                        "",
                        "München",
                        "Zollsoft",
                    )
                elif astra_counter != vaccination_count:
                    helper.update_airtable_entry(
                        vaccination_id,
                        astra_counter,
                        astra_dates,
                    )

                # Send appointments to Doctolib
                if vaccination_count == 0 or astra_counter > vaccination_count:
                    zollsoft_send_message(
                        city, astra_counter, astra_dates, "AstraZeneca", booking_url
                    )
                helper.airtable_id_count_dict[vaccination_id] = astra_counter
            elif vaccination_count > 0:
                helper.delete_airtable_entry(vaccination_id)

            # Moderna
            vaccination_id = f"zollsoft.{unique_id}.moderna"
            if not vaccination_id in helper.airtable_id_count_dict:
                helper.airtable_id_count_dict[vaccination_id] = 0
            vaccination_count = helper.airtable_id_count_dict[vaccination_id]
            if moderna_counter > 0:
                # Update Airtable
                if vaccination_count == 0:
                    helper.create_airtable_entry(
                        vaccination_id,
                        "Alle Impfungen (Moderna)",
                        moderna_counter,
                        booking_url,
                        "",
                        "Alle Impfungen",
                        "Moderna",
                        moderna_dates,
                        "",
                        "München",
                        "Zollsoft",
                    )
                elif moderna_counter != vaccination_count:
                    helper.update_airtable_entry(
                        vaccination_id,
                        moderna_counter,
                        moderna_dates,
                    )

                # Send appointments to Doctolib
                if vaccination_count == 0 or moderna_counter > vaccination_count:
                    zollsoft_send_message(
                        city, moderna_counter, moderna_dates, "Moderna", booking_url
                    )
                helper.airtable_id_count_dict[vaccination_id] = moderna_counter
            elif vaccination_count > 0:
                helper.delete_airtable_entry(vaccination_id)

            # Johnson & Johnson
            vaccination_id = f"zollsoft.{unique_id}.johnson"
            if not vaccination_id in helper.airtable_id_count_dict:
                helper.airtable_id_count_dict[vaccination_id] = 0
            vaccination_count = helper.airtable_id_count_dict[vaccination_id]
            if johnson_counter > 0:
                # Update Airtable
                if vaccination_count == 0:
                    helper.create_airtable_entry(
                        vaccination_id,
                        "Alle Impfungen (Johnson & Johnson)",
                        johnson_counter,
                        booking_url,
                        "",
                        "Alle Impfungen",
                        "Johnson & Johnson",
                        johnson_dates,
                        "",
                        "München",
                        "Zollsoft",
                    )
                elif johnson_counter != vaccination_count:
                    helper.update_airtable_entry(
                        vaccination_id,
                        johnson_counter,
                        johnson_dates,
                    )

                # Send appointments to Doctolib
                if vaccination_count == 0 or johnson_counter > vaccination_count:
                    zollsoft_send_message(
                        city,
                        johnson_counter,
                        johnson_dates,
                        "Johnson & Johnson",
                        booking_url,
                    )
                helper.airtable_id_count_dict[vaccination_id] = johnson_counter
            elif vaccination_count > 0:
                helper.delete_airtable_entry(vaccination_id)

    except Exception as e:
        helper.error_log(f"[Zollsoft] General Error [{str(e)}]")
