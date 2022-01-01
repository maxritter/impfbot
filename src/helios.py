import requests
import datetime
import arrow
from src import helper

helios_session = None
helios_config = None
helios_locations = None
helios_init_completed = False
helios_locations_fetched = False


def helios_init_session():
    global helios_session, helios_config, helios_init_completed

    helios_session = helper.DelayedSession()
    helios_session.headers = {
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9,de-DE;q=0.8,de;q=0.7",
        "cache-control": "no-cache",
        "origin": "https://patienten.helios-gesundheit.de",
        "pragma": "no-cache",
        "referer": "https://patienten.helios-gesundheit.de/appointments/book-appointment",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.114 Safari/537.36",
    }

    helios_config = {}

    # grab default uuid for what I assume is public health care
    try:
        res = helios_session.get(
            "https://patienten.helios-gesundheit.de/assets/environment/environment.json",
            timeout=helper.api_timeout_seconds,
        )
        res.raise_for_status()
    except requests.exceptions.HTTPError as e:
        helper.warn_log(
            f"[Helios] HTTP issue during fetch of environment variables for session [{str(e)}]"
        )
        return False
    except requests.exceptions.Timeout as e:
        helper.warn_log(
            f"[Helios] Timeout during fetch of environment variables for session [{str(e)}]"
        )
        return False
    except Exception as e:
        helper.error_log(
            f"[Helios] Error during fetch of environment variables for session [{str(e)}]"
        )
        return False

    helios_config["healthInsuranceTypeUUID"] = res.json()["environment"]["timerbee"][
        "defaultHealthInsuranceTypeUUID"
    ]

    # grab uuid for corona vaccinations
    try:
        res = helios_session.get(
            "https://api.patienten.helios-gesundheit.de/api/appointment/lookup/purposecategories",
            timeout=helper.api_timeout_seconds,
        )
        res.raise_for_status()
    except requests.exceptions.HTTPError as e:
        helper.warn_log(
            f"[Helios] HTTP issue during fetch of UUID for Corona Vaccinations [{str(e)}]"
        )
        return False
    except requests.exceptions.Timeout as e:
        helper.warn_log(
            f"[Helios] Timeout during fetch of UUID for Corona Vaccinations [{str(e)}]"
        )
        return False
    except Exception as e:
        helper.error_log(
            f"[Helios] Error during fetch of UUID for Corona Vaccinations [{str(e)}]"
        )
        return False

    corona = [x for x in res.json()["kvps"] if x["value"] == "Corona-Impfung"].pop()
    # 341094cb-8239-4a8e-b526-828108e46a05
    helios_config["purposeCategoryUUID"] = corona["key"]
    helios_config["treatmentID"] = corona["oid"]  # 12
    helios_init_completed = True
    return True


def helios_gather_locations(lat, lng, address, radius=50):
    global helios_session, helios_config, helios_locations, helios_locations_fetched

    # Check if init has been completed before
    if not helios_init_completed:
        helios_init_session()
        if not helios_init_completed:
            return False

    query = {
        "gpsData": {
            "lat": lat,
            "lng": lng,
            "address": address,
        },
        "healthInsuranceTypeUUID": helios_config["healthInsuranceTypeUUID"],
        "radius": radius,
        "purposeCategoryUUID": helios_config["purposeCategoryUUID"],
    }

    try:
        try:
            res = helios_session.post(
                "https://api.patienten.helios-gesundheit.de/api/appointment/multitenant/resources/query",
                json=query,
                timeout=helper.api_timeout_seconds,
            )
            res.raise_for_status()
        except requests.exceptions.HTTPError as e:
            helper.warn_log(
                f"[Helios] HTTP issue during gathering of locations [{str(e)}]"
            )
            return False
        except requests.exceptions.Timeout as e:
            helper.warn_log(
                f"[Helios] Timeout during gathering of locations [{str(e)}]"
            )
            return False
        except Exception as e:
            helper.error_log(f"[Helios] Error during gathering of locations [{str(e)}]")
            return False

        # store just the stuff we care about and need for the next step
        helios_locations = []
        for entry in res.json():
            # the resource match will LIKELY always just be one entry with one or multiple purposes, if not we can deal with it as well though
            # although technically the appointment query allows us to specify a list of resourceUUIDs, it's probably not important
            for resource in entry["resourceMatches"]:
                # this is a double nested list of possible purposes you could have to go to this location
                # it will probably contain several purposes if one locations offers an AZ vaccination and a Biontec one
                # as both those should match the specialtyUUID "Corona Impfung" but would be different appointments in the following steps
                # we'll turn locations into unique pairs of location+vaccine so if one location offers AZ+Biontec it'll show as 2 different "locations" in this list
                for purpose in resource["possiblePurposes"]:
                    helios_locations.append(
                        {
                            "name": entry["tenantName"],  # MVZ Goltzstraße 38
                            "facilityID": entry["tenant"]["oid"],  # 13
                            # 22367
                            "physicianID": resource["resource"]["oid"],
                            "purposeName": purpose[
                                "name"
                            ],  # "Corona-Impfung (Astrazeneca)"
                            "purposeID": purpose["oid"],
                            "purposeCategoryUUID": purpose[
                                "purposeCategoryUUID"
                            ],  # e840cc42-9bd5-4030-8c46-badc5c9d0872
                            "resourceUUIDs": [
                                resource["resource"]["uuid"]
                            ],  # [cff71820-29da-48a3-a4ea-871a01c31157]
                            "userGroupUUID": entry[
                                "userGroupUUID"
                            ],  # ef323855-2955-4c3a-a0eb-c157608a1e5c
                        }
                    )
                    helios_name = entry["tenantName"]
                    helper.info_log(f"Helios Location {helios_name} added!")
        helios_locations_fetched = True
        return True

    except Exception as e:
        helper.error_log(f"[Helios] General error during gather [{str(e)}]")
        return False


def helios_fetch_locations(city):
    if not helios_gather_locations(
        helper.conf[city]["lat"], helper.conf[city]["lng"], helper.conf[city]["address"]
    ):
        helper.warn_log("Unable to gather Helios locations..")


def helios_check(city):
    global helios_session, helios_config, helios_locations, helios_init_completed, helios_locations_fetched

    # Check if init has been completed
    if not helios_init_completed:
        helios_init_session()
        if not helios_init_completed:
            return False
    try:
        _ = helios_config["treatmentID"]
    except Exception:
        helper.warn_log("[Helios] Init was not completed during check, try to init..")
        helios_init_completed = False
        helios_init_session()
        if not helios_init_completed:
            return False

    # Check if locations have been fetched
    if not helios_locations_fetched:
        helios_fetch_locations(city)
        if not helios_locations_fetched:
            return False
    for location in helios_locations:
        try:
            _ = location["facilityID"]
        except Exception:
            helper.warn_log(
                "[Helios] Locations were not found during check, try to fetch.."
            )
            helios_locations_fetched = False
            helios_fetch_locations(city)
            if not helios_locations_fetched:
                return False

    try:
        for location in helios_locations:
            query = {
                "userGroupUuid": location["userGroupUUID"],
                "resourceUuids": location["resourceUUIDs"],
                "purposeQuery": {
                    "puroseCategoryUUID": location["purposeCategoryUUID"],
                },
                "begin": arrow.now().isoformat(),
                "end": arrow.now().shift(days=14).isoformat(),
            }

            try:
                res = helios_session.post(
                    "https://api.patienten.helios-gesundheit.de/api/appointment/booking/querytimeline",
                    json=query,
                    timeout=helper.api_timeout_seconds,
                )
                res.raise_for_status()
                result = res.json()
            except requests.exceptions.HTTPError as e:
                helper.warn_log(
                    f"[Helios] HTTP issue during checking Helios API, try to reinit the session [{str(e)}]"
                )
                helios_init_session()
                return
            except requests.exceptions.Timeout as e:
                helper.warn_log(
                    f"[Helios] Timeout during checking Helios API [{str(e)}]"
                )
                return
            except Exception as e:
                helper.warn_log(
                    f"[Helios] General issue during checking Helios API [{str(e)}]"
                )
                return

            # Lookup vaccination count
            vaccination_id = f"{location['facilityID']}.{location['physicianID']}.{location['purposeID']}"
            if not vaccination_id in helper.airtable_id_count_dict:
                helper.airtable_id_count_dict[vaccination_id] = 0
            vaccination_count = helper.airtable_id_count_dict[vaccination_id]

            # Check how many slots we have
            slot_counter = len(result)
            if slot_counter == 0:
                if vaccination_count > 0:
                    helper.delete_airtable_entry(vaccination_id)
                continue

            # Parse dates
            available_dates = []
            for entry in result:
                dt_naive = datetime.datetime.strptime(
                    entry["begin"], "%Y-%m-%dT%H:%M:%S.%fZ"
                )
                dt = datetime.datetime.combine(
                    dt_naive.date(), dt_naive.time(), datetime.timezone.utc
                )
                available_date = dt.strftime("%d.%m.%Y")
                available_dates.append(available_date)

            vaccine_name = location["purposeName"]
            vaccine_compound = helper.get_vaccine_compound(vaccine_name)
            vaccine_type = helper.get_vaccine_type(vaccine_name)
            url = f"https://patienten.helios-gesundheit.de/appointments/book-appointment?facility={location['facilityID']}&physician={location['physicianID']}&purpose={location['purposeID']}&resource={helios_config['treatmentID']}"
            
            # Update Airtable
            if vaccination_count == 0:
                helper.create_airtable_entry(
                    vaccination_id,
                    vaccine_name,
                    slot_counter,
                    url,
                    location['name'],
                    vaccine_type,
                    vaccine_compound,
                    available_dates,
                    "",
                    location['name'],
                    "Helios",
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
                verbose_dates = ", ".join(sorted(set(available_dates)))
                message = (
                    message
                    + f"für {vaccine_name} in {location['name']}. Wählbare Tage: { verbose_dates}."
                )
                message_long = message + f" Hier buchen: {url}"

                # Print message out on server
                helper.info_log(message)

                # Send message to telegram channels for the specific city
                helper.send_channel_msg(city, "all", message_long)
                if vaccine_compound == "BioNTech" or vaccine_compound == "Moderna":
                    helper.send_channel_msg(city, "mrna", message_long)

                elif (
                    vaccine_compound == "AstraZeneca"
                    or vaccine_compound == "Johnson & Johnson"
                ):
                    helper.send_channel_msg(city, "vec", message_long)
            
            helper.airtable_id_count_dict[vaccination_id] = slot_counter

    except Exception as e:
        helper.error_log(f"[Helios] General error during check [{str(e)}]")


def helios_init(city):
    retry_counter = 0
    while True:
        if helios_init_session():
            break
        helper.warn_log("[Helios] Unable to init Helios API, try again..")
        retry_counter = retry_counter + 1
        if retry_counter >= 3:
            helper.warn_log("[Helios] Unable to init Helios API, start without..")
            break

    if helios_init_completed:
        helios_fetch_locations(city)
