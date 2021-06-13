import dateutil.parser
import requests
import urllib.parse
import threading
from src import helper, database
from datetime import timedelta

jameda_session = None
jameda_locations = None
jameda_locations_fetched = False


def jameda_check(city):
    global jameda_locations, jameda_locations_fetched

    # Check if locations have been fetched
    if not jameda_locations_fetched:
        jameda_fetch_locations(city)
        if not jameda_locations_fetched:
            return

    # Go through all locations
    for location in jameda_locations:
        jameda_check_api(city, **location)


def jameda_check_api(city, profile_id, service_id, location, vaccine, **kwargs):
    global jameda_session

    try:
        url = f"https://booking-service.jameda.de/public/resources/{profile_id}/slots"
        params = {
            "serviceId": service_id,
        }

        try:
            res = jameda_session.get(
                url,
                params=params,
            )
            res.raise_for_status()
            result = res.json()
        except requests.exceptions.HTTPError as e:
            helper.warn_log(
                f'[Jameda] HTTP issue during API check [{str(e)}]')
            return
        except requests.exceptions.Timeout as e:
            helper.warn_log(
                f'[Jameda] API is currently not reachable [{str(e)}]')
            return
        except requests.exceptions.ConnectionError as e:
            helper.warn_log(
                f'[Jameda] API is currently not reachable [{str(e)}]')
            return
        except Exception as e:
            helper.error_log(
                f'[Jameda] Error during fetch from API [{str(e)}]')
            return

        if type(result) != list:
            # {'code': 2000, 'message': 'There are no open slots, because all slots have been booked already.'}
            return

        coupled_service_id = kwargs.get("coupled_service_id", None)

        spots = {
            "amount": 0,
            "dates": [],
        }
        # [{"slot":"2021-08-25T13:00:00+02:00","resources":[81157780]}]
        for entry in result:
            vaccination_id = "{}.{}.{}.{}".format(
                entry["slot"], profile_id, service_id, vaccine)
            if vaccination_id not in helper.already_sent_ids:
                dt = dateutil.parser.parse(entry["slot"])
                if coupled_service_id:
                    dt_min = dt.replace(hour=0, minute=0) + \
                        kwargs["coupled_service_min_offset"]
                    dt_max = dt.replace(hour=0, minute=0) + \
                        kwargs["coupled_service_max_offset"]
                    # this service can't be booked on its own!
                    # specifying from here is important because otherwise we only get stuff in the near future
                    # but we might need dates in the far future because of how AZ works
                    params = {
                        "serviceId": coupled_service_id,
                        "from": dt_min.isoformat(),
                    }
                    try:
                        res = jameda_session.get(
                            url,
                            params=params,
                        )
                        coupled_result = res.json()
                    except requests.exceptions.HTTPError as e:
                        helper.warn_log(
                            f'[Jameda] HTTP issue during API check [{str(e)}]')
                        continue
                    except requests.exceptions.Timeout as e:
                        helper.warn_log(
                            f'[Jameda] API is currently not reachable [{str(e)}]')
                        continue
                    except requests.exceptions.ConnectionError as e:
                        helper.warn_log(
                            f'[Jameda] API is currently not reachable [{str(e)}]')
                        continue
                    except Exception as e:
                        helper.error_log(
                            f'[Jameda] Error during fetch from API [{str(e)}]')
                        continue
                    if type(coupled_result) != list:
                        continue
                    # we need to check if there's any matching slots in the 2nd booking that depends on this first one
                    matching_second = False
                    for second in coupled_result:
                        dt_second = dateutil.parser.parse(second["slot"])
                        if dt_second > dt_max:
                            continue
                        matching_second = True
                        break
                    if not matching_second:
                        # no matching second appointment = this slot is useless to us, the UI will not let us book it
                        # let's rather let some slots go to waste because of no matching subsequent appointments than just leeting people book them on their own... wow
                        continue

                spots["amount"] += 1
                spots["dates"].append(dt.strftime("%d.%m.%y"))
                helper.already_sent_ids.append(vaccination_id)

        # We have found a valid appointment
        if spots["amount"] > 0:
            booking_url = f"https://www.jameda.de/profil/{profile_id}/"
            slot_counter = spots['amount']

            # Construct message
            if slot_counter == 1:
                message = f'{slot_counter} freier Impftermin '
            else:
                message = f'{slot_counter} freie Impftermine '
            vaccine_dates_str = ", ".join(sorted(set(spots["dates"])))
            message = message + \
                f'für {vaccine} in {location}. Wählbare Tage: {vaccine_dates_str}.'
            message_long = message + f' Hier buchen: {booking_url}'

            # Print message out on server
            helper.info_log(message)

           # Send message to telegram channels for the specific city
            if vaccine == 'BioNTech' or vaccine == 'Moderna':
                main_city = ''.join(
                    (x for x in city if not x.isdigit())).upper()
                if main_city == 'MUC':
                    helper.send_pushed_msg(message, booking_url)
                    t_all = threading.Thread(
                        target=helper.delayed_send_channel_msg, args=(city, 'all', message_long))
                    t_all.start()
                    t_mrna = threading.Thread(
                        target=helper.delayed_send_channel_msg, args=(city, 'mrna', message_long))
                    t_mrna.start()
                else:
                    helper.send_channel_msg(city, 'mrna', message_long)
                    helper.send_channel_msg(city, 'all', message_long)
            elif vaccine == 'AstraZeneca' or vaccine == 'Johnson & Johnson':
                helper.send_channel_msg(city, 'vec', message_long)
                helper.send_channel_msg(city, 'all', message_long)

            # Add to database
            database.insert_vaccination(
                vaccine, spots["amount"], city, "jameda")

    except Exception as e:
        helper.error_log(f'[Jameda] General error during check [{str(e)}]')


def jameda_fetch_locations(city):
    if not jameda_gather_locations(helper.conf[city]['city']):
        helper.warn_log('Unable to gather Jameda locations..')


def jameda_gather_locations(location):
    global jameda_session, jameda_locations, jameda_locations_fetched

    try:
        params = {
            "query": location,
            "echo": location,
        }
        # autocompletion api gives us the input we need in the location query step
        # it contains several results, as we're mainly focusing on bigger cities we'll just assume the top suggestion is the location we wanted
        try:
            res = jameda_session.get(
                "https://suche.jameda-elements.de/where-dev", params=params)
            res.raise_for_status()
            result = res.json()
        except requests.exceptions.HTTPError as e:
            helper.warn_log(
                f'[Jameda] HTTP issue during Locations Gather [{str(e)}]')
            return
        except requests.exceptions.Timeout as e:
            helper.warn_log(
                f'[Jameda] API is currently not reachable [{str(e)}]')
            return
        except Exception as e:
            helper.error_log(
                f'[Jameda] Error during fetch from API [{str(e)}]')
            return

        location_selection = None
        for suggestion in result["suggests"]:
            if suggestion["header"] == "Ort":
                for entry in suggestion["list"]:
                    location_selection = entry["select"]
                    break
            if location_selection is not None:
                break
        if location_selection is None:
            return []
        # this yields badly encoded query params for the location finder
        # geoball=11%2E558007%2C48%2E144836%2C0%2E5&geo=48%2E144836%5F11%2E558007%5F%5F0%5FM%FCnchen%5Fmuenchen%5FBayern%5F1

        params = {
            "query": "Corona-Impfung",
            "echo": "Corona-Impfung",
        }
        # autocompletion api also gives us the query params for what exactly a "Corona-Impfung" is in their system
        # there's also "Coronavirus-Schutzimpfung" but from all I gathered they yield the same doctors
        try:
            res = jameda_session.get(
                "https://suche.jameda-elements.de/what-dev", params=params)
            res.raise_for_status()
            result = res.json()
        except requests.exceptions.HTTPError as e:
            helper.warn_log(
                f'[Jameda] HTTP issue during Location Gather [{str(e)}]')
            return
        except requests.exceptions.Timeout as e:
            helper.warn_log(
                f'[Jameda] API is currently not reachable [{str(e)}]')
            return
        except Exception as e:
            helper.error_log(
                f'[Jameda] Error during fetch from API [{str(e)}]')
            return

        service_selection = None
        for suggestion in result["suggests"]:
            if suggestion["header"] == "Fachbereiche & Symptome":
                for entry in suggestion["list"]:
                    service_selection = entry["select"]
                    if "test" in entry["showSelect"].lower():
                        continue
                    break
            if service_selection is not None:
                break
        if service_selection is None:
            return []

        params = {
            "address_i": location,
            "new_search": "1",
            "output": "json",
            "version": "6.0.0",  # not sure where this is coming from, let's assume it stays static or has no meaning, most APIs don't actually check shit like this
        }
        params.update(urllib.parse.parse_qsl(location_selection))
        params.update(urllib.parse.parse_qsl(service_selection))
        headers = {
            "Referer": "https://www.jameda.de/corona-impftermine/behandlung/",
        }

        try:
            res = jameda_session.post(
                "https://www.jameda.de/arztsuche/",
                headers=headers,
                params=params,
            )
            res.raise_for_status()
        except requests.exceptions.HTTPError as e:
            helper.warn_log(
                f'[Jameda] HTTP issue during Location Gather [{str(e)}]')
            return
        except requests.exceptions.Timeout as e:
            helper.warn_log(
                f'[Jameda] API is currently not reachable [{str(e)}]')
            return
        except Exception as e:
            helper.error_log(
                f'[Jameda] Error during fetch from API [{str(e)}]')
            return

        jameda_locations = []
        for entry in res.json()["results"]:
            profile_id = entry["ref_id"]

            # let's ask nicely to get the service_id we need from elsewhere :)
            try:
                service_res = jameda_session.get(
                    f"https://booking-service.jameda.de/public/resources/{profile_id}/services"
                )
                service_result = service_res.json()
            except requests.exceptions.HTTPError as e:
                helper.warn_log(
                    f'[Jameda] HTTP issue during Location Gather [{str(e)}]')
                return
            except requests.exceptions.Timeout as e:
                helper.warn_log(
                    f'[Jameda] API is currently not reachable [{str(e)}]')
                return
            except Exception as e:
                helper.error_log(
                    f'[Jameda] Error during fetch from API [{str(e)}]')
                return

            if type(service_result) != list:
                # there's a fair amount of shit coming out of this API request sometimes
                # {'code': 404, 'message': 'Calendar Api: 404 is returned for request GET:/public/resources/81421339/services', 'originalError': {'status': 404, 'data': {'code': 404, 'message': 'The specified refId (81421339) does not have OTB available.'}}}
                continue

            couplings = []
            vaccines = []
            for service in service_result:
                service_id = service["id"]
                if service_id in couplings:
                    # this is not a service we can book on our own, it depends on us having booked another service first
                    continue

                title = service["title"].lower()
                if "corona" in title and not "antikörper" in title and \
                        not "test" in title and not "beratung" in title and \
                        not "nur" in title and not "außer" in title and \
                        not "zweitimpfung" in title and not "test" in title and \
                        not "impfberatung" in title:
                    if "johnson" in title or "janssen" in title:
                        vaccine = "Johnson & Johnson"
                    elif "astra" in title:
                        vaccine = "AstraZeneca"
                    elif "bion" in title:
                        vaccine = "BioNTech"
                    elif "modern" in title:
                        vaccine = "Moderna"
                    else:
                        vaccine = service["title"]
                        helper.warn_log(
                            f'[Jameda] Unknown vaccination for URL https://www.jameda.de/profil/{entry["ref_id"]}/ ({vaccine})')
                        continue

                    location = {
                        "profile_id": profile_id,
                        "location": f"{entry['plz']} {entry['ort']}",
                        "service_id": service_id,
                    }
                    if "followingCouplingLinks" in service:
                        # this service has a dependency to another service, i.e. Erstimpfung and Zweitimpfung coupled into one booking process
                        # we won't be able to book a Zweitimpfung on its own
                        # and we can't book the Erstimpfung without booking a Zweitimpfung, which has its own availability and logic for how much time must've passed between the slots
                        for coupling in service["followingCouplingLinks"]:
                            location.update(
                                {
                                    "coupled_service_id": coupling["serviceId"],
                                    "coupled_service_min_offset": timedelta(
                                        hours=coupling["minIntervalToPrevious"]
                                    ),
                                    "coupled_service_max_offset": timedelta(
                                        hours=coupling["maxIntervalToPrevious"]
                                    ),
                                }
                            )
                            couplings.append(coupling["serviceId"])
                    location["vaccine"] = vaccine

                    if vaccine in vaccines:
                        # some locations have overlapping vaccinations they offer
                        # e.g. https://www.jameda.de/profil/80085713/ has 2x Zweitimpfung and 1x Erstimpfung on the API *shrug
                        continue
                    if service["insuranceType"] != 'STATUTORY_AND_PRIVATE':
                        continue
                    jameda_locations.append(location)
                    helper.info_log(
                        f'Jameda Clinic {entry["name_kurz"]} at {entry["plz"]} {entry["ort"]} added!')

        jameda_locations_fetched = True
        return True

    except Exception as e:
        helper.error_log(f'[Jameda] General error during gather [{str(e)}]')
        return False


def jameda_init(city):
    global jameda_session

    jameda_session = requests.Session()
    jameda_session.headers = {
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9,de-DE;q=0.8,de;q=0.7",
        "cache-control": "no-cache",
        "origin": "https://www.jameda.de",
        "pragma": "no-cache",
        "referer": "https://www.jameda.de",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.114 Safari/537.36",
    }

    jameda_fetch_locations(city)
