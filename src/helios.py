import requests
import datetime
import arrow
from src import helper

helios_session = None
helios_config = None
helios_locations = None


def helios_init():
    global helios_session, helios_config

    helios_session = requests.Session()
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
    res = helios_session.get(
        "https://patienten.helios-gesundheit.de/assets/environment/environment.json"
    )
    res.raise_for_status()
    helios_config["healthInsuranceTypeUUID"] = res.json()["environment"]["timerbee"][
        "defaultHealthInsuranceTypeUUID"
    ]

    # grab uuid for corona vaccinations
    res = helios_session.get(
        "https://api.patienten.helios-gesundheit.de/api/appointment/specialty"
    )
    res.raise_for_status()
    corona = [x for x in res.json() if x["name"] == "Corona-Impfung"].pop()
    # c619bfb1-9e18-404d-b960-dfac6c072490
    helios_config["specialtyUUID"] = corona["uuid"]
    helios_config["treatmentID"] = corona["oid"]  # 58


def parse_dt(arg):
    dt_naive = datetime.datetime.strptime(arg, "%Y-%m-%dT%H:%M:%S.%fZ")
    # turn naive into aware datetime. why are you this pointlessly complicated python stdlib!
    return datetime.datetime.combine(dt_naive.date(), dt_naive.time(), datetime.timezone.utc)


def helios_check(city):
    global helios_session, helios_config, helios_locations

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

            res = helios_session.post(
                "https://api.patienten.helios-gesundheit.de/api/appointment/booking/querytimeline",
                json=query,
            )
            res.raise_for_status()
            result = res.json()

            spots = {
                "amount": 0,
                "dates": [],
            }
            for entry in result:
                dt = parse_dt(entry["begin"])
                vaccination_id = "{}.{}.{}".format(
                    location["purposeName"], location['name'], str(dt))
                if vaccination_id not in helper.already_sent_ids:
                    spots["amount"] += 1
                    spots["dates"].append(dt.strftime("%d.%m.%y"))
                    helper.already_sent_ids.append(vaccination_id)

            if spots["amount"] > 0:
                dates = ", ".join(sorted(set(spots["dates"])))
                vaccine = location["purposeName"]
                if "biontech" in vaccine.lower():
                    vaccine = "BioNTech"
                elif "astra" in vaccine.lower():
                    vaccine = "AstraZeneca"
                elif "moderna" in vaccine.lower():
                    vaccine = "Moderna"
                elif "johnson" in vaccine.lower() or "janssen" in vaccine.lower():
                    vaccine = "Johnson & Johnson"
                else:
                    vaccine = "COVID-19 Impfstoff"

                url = f"https://patienten.helios-gesundheit.de/appointments/book-appointment?facility={location['facilityID']}&physician={location['physicianID']}&purpose={location['purposeID']}&resource={helios_config['treatmentID']}"
                message = f"Freie Impftermine für {vaccine} in {location['name']}. Wählbare Tage: {dates}. Hier buchen: {url}"

                # Print message out on server with city in front
                print(f'{city}: {message}')

                # Send message to telegram channel for the specific city
                helper.send_telegram_msg(city, message)

    except Exception as e:
        print(f'{city}: ERROR During Helios check - ' + str(e))


def helios_gather_locations(city, lat, lon, address, radius=50):
    global helios_session, helios_config, helios_locations

    query = {
        "gpsData": {
            "lat": lat,
            "lng": lon,
            "address": address,
        },
        "healthInsuranceTypeUUID": helios_config["healthInsuranceTypeUUID"],
        "radius": radius,
        "specialtyUUID": helios_config["specialtyUUID"],
    }

    try:
        res = helios_session.post(
            "https://api.patienten.helios-gesundheit.de/api/appointment/multitenant/resources/query",
            json=query,
        )
        res.raise_for_status()

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
                    print(f"{city}: Helios Location {helios_name} added!")
        return True

    except Exception as e:
        print(f'{city}: ERROR During Helios Gather Locations - ' + str(e))
        return False
