#!/usr/bin/env python3

import random
import requests
import time

from bs4 import BeautifulSoup
from datetime import datetime

BASE_URL = "https://digitalfactory.randstadservices.com/ImpfFinder"


def check_api(session, base_payload, center_id, date):
    # example payload to request appointments for locations near #32 (Kehl)
    # {
    #     "versionInfo": {
    #         "moduleVersion": "9duPMrzTPteEOciME5AvEg",
    #         "apiVersion": "Obmq4HsAvzCAIl5P5x8pdQ"
    #     },
    #     "viewName": "MainFlow.VaccineAppointments",
    #     "inputParameters": {
    #         "ValidCenterLocations": {
    #             "List": [{
    #                     "CenterLocationId": "32",
    #                     "Distance": "0.06717551733352597"
    #                 }
    #             ]
    #         },
    #         "IsAstraZeneca": true,
    #         "IsPfizer": true,
    #         "IsModerna": true,
    #         "Date": "2021-05-18"
    #     }
    # }

    # there are 32 different locations we can request by listing them in the ValidCenterLocations bit
    # we could probably just list all 32 locations in one go, but a real requestor wouldn't, so depends a bit on how you want to play this

    # avoid any pass by reference weirdness
    payload = base_payload.copy()
    payload.update(
        {
            "viewName": "MainFlow.VaccineAppointments",
            "inputParameters": {
                "ValidCenterLocations": {
                    "List": [
                        {
                            "CenterLocationId": center_id,
                            "Distance": str(
                                random.random() * 5
                            ),  # we're always within 5km of any center, duh
                        }
                    ]
                },
                "IsAstraZeneca": True,
                "IsPfizer": True,
                "IsModerna": True,
                "Date": date,
            },
        }
    )
    headers = {
        "accept": "application/json",
    }

    res = session.post(
        f"{BASE_URL}/screenservices/VaccineBuddyMobile_CS/ActionGet_AppointmentsByDistance",
        headers=headers,
        json=payload,
    )
    res.raise_for_status()
    result = res.json()
    # example response:
    # {
    #     "versionInfo": {
    #         "hasModuleVersionChanged": false,
    #         "hasApiVersionChanged": false
    #     },
    #     "data": {
    #         "AppointmentList": {
    #             "List": [],
    #             "EmptyListItem": {
    #                 "DateTime": "1900-01-01T00:00:00",
    #                 "AppointmentCount": "0",
    #                 "City": "",
    #                 "Address": "",
    #                 "QRData": "",
    #                 "IsReservedCount": "0",
    #                 "VaccineTypeId": 0,
    #                 "VaccineName": "",
    #                 "Pin": "",
    #                 "CenterLocationId": "0",
    #                 "AppointmentId": "0",
    #                 "AppointmentDefinitionId": "0",
    #                 "DoctorName": ""
    #             }
    #         }
    #     }
    # }

    if (
        result["versionInfo"]["hasModuleVersionChanged"]
        or result["versionInfo"]["hasApiVersionChanged"]
    ):
        # bail out, reset session, re-do stuff :)
        return False

    # here starts the guessing :)
    # probably makes sense to dry-run it a bit until you can catch a real result to know what it actually looks like
    appointments = result["data"]["AppointmentList"]["List"]
    print(f"{datetime.now()} - Found {len(appointments)} appointments")

    for entry in appointments:
        print(
            f"{datetime.now()}: {entry['DateTime']} {entry['AppointmentCount']} appointments with {entry['VaccineName']} at {entry['Address']} in {entry['City']} with {entry['DoctorName']}"
        )


def init_session():
    session = requests.Session()
    session.headers = {
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9,de-DE;q=0.8,de;q=0.7",
        "cache-control": "no-cache",
        "origin": "https://digitalfactory.randstadservices.com",
        "pragma": "no-cache",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.114 Safari/537.36",
    }
    start_url = f"{BASE_URL}/VaccineAppointments?IsShowCase=false"
    res = session.get(start_url)
    res.raise_for_status()
    soup = BeautifulSoup(res.content, "lxml")

    session.headers.update(
        {
            "referer": start_url,
        }
    )

    init_script_url = None
    for script in soup.find_all("script"):
        if script.get("src", "").startswith("scripts/OutSystems.js"):
            init_script_url = f"{BASE_URL}/{script.get('src')}"
            break

    if not init_script_url:
        raise RuntimeError(
            "Couldn't find init script - we need this to gather the CSRF token"
        )

    res = session.get(init_script_url)
    res.raise_for_status()

    # this will be a bit ugly but we need the anonymous CSRF token (static) and it's defined in this file
    # as we can assume this could change at some point once this potentially versioned .js gets updated, lets do it properly and grab it from there
    csrf_token = res.text.split("e.AnonymousCSRFToken=")[1].split(",")[0].strip('"')

    if csrf_token == "T6C+9iB49TLra4jEsMeSckDMNhQ=":
        # i'm not entirely sure where this cookie comes from, it's probably generated within the OutSystems.js as well based on
        # function I() { return "nr2" + U.userProviderName; }
        # in that script. userProviderName is from ImpfFinder.appDefinition.js and set to Users, so this is definitely connected, but I don't quite see what gets set from where right now
        # as such let's just assume for now as long as the anonymous csrf token doesn't change the cookie won't change either, it has no expiry set
        # decoded cookie: nr1Users=lid=Anonymous;tuu=0;exp=0;rhs=XBC1ss1nOgYW1SmqUjSxLucVOAg=;hmc=RhbOGMMjzYEgnPn0Xh6Eig3X7ys=; nr2Users=crf=T6C+9iB49TLra4jEsMeSckDMNhQ=;uid=0;unm=
        session.headers.update(
            {
                "cookie": "nr1Users=lid%3dAnonymous%3btuu%3d0%3bexp%3d0%3brhs%3dXBC1ss1nOgYW1SmqUjSxLucVOAg%3d%3bhmc%3dRhbOGMMjzYEgnPn0Xh6Eig3X7ys%3d; nr2Users=crf%3dT6C%2b9iB49TLra4jEsMeSckDMNhQ%3d%3buid%3d0%3bunm%3d",
                "X-CSRFToken": csrf_token,
            }
        )
    else:
        raise RuntimeError(
            "CSRF token has changed from previous default, best to re-check current cookie payload"
        )

    return session


if __name__ == "__main__":
    session = init_session()

    # gather the module version, this appears to be based on the current time in microseconds
    res = session.get(
        f"https://digitalfactory.randstadservices.com/ImpfFinder/moduleservices/moduleversioninfo?{int(time.time() * 1000)}"
    )
    module_version = res.json()["versionToken"]

    # I'm pretty sure the parameter here is injected from the service worker framework they use
    # I'm too lazy right now to check out what it does and if it makes a difference
    # this might just be for front-end caching decisions, because the parameter has no influence on the file they serve, so let's just go with it for now
    # the returned apiVersion already changed while I was reversing this, so we might need to actually refresh this more often than just on the initial load...
    res = session.get(
        "https://digitalfactory.randstadservices.com/ImpfFinder/scripts/VaccineBuddyMobile_CS.controller.js?qeauwrkI2ElBIGhNPJO0LQ"
    )
    api_version = (
        res.text.split(
            "screenservices/VaccineBuddyMobile_CS/ActionGet_AppointmentsByDistance"
        )[1]
        .split(",")[1]
        .strip()
        .strip('"')
    )

    base_payload = {
        "versionInfo": {
            "moduleVersion": module_version,
            "apiVersion": api_version,
        },
    }

    # we have all the info we need now to perform requests like normal users would :)
    # this basically needs more logic to iterate over several dates and/or locations
    # locations are listed below, date format is YYYY-MM-DD
    while True:
        if not check_api(session, base_payload, 32, "2021-05-24"):
            session = init_session()
        time.sleep(60 * 60 + (random.random() * 60))


# locations as provided from the https://digitalfactory.randstadservices.com/ImpfFinder/screenservices/VaccineBuddyMobile_CS/ActionGetCenterLocation endpoint
# we can use the IDs to query for appointments in the said location/city
#    {
#        "versionInfo": {
#            "hasModuleVersionChanged": false,
#            "hasApiVersionChanged": false
#        },
#        "data": {
#            "CenterLocations": {
#                "List": [{
#                        "Id": "1",
#                        "StreetAddress": "Ziegelstraße",
#                        "StreetAddressNumber": "",
#                        "PostalCode": "10117",
#                        "City": "Berlin",
#                        "PhoneNumber": "",
#                        "Email": "",
#                        "Longitude": "13.39239640",
#                        "Latitude": "52.52324130",
#                        "StateId": 0,
#                        "DisplayName": ""
#                    }, {
#                        "Id": "2",
#                        "StreetAddress": "Helfmann-Park - ",
#                        "StreetAddressNumber": "2",
#                        "PostalCode": "65760",
#                        "City": "Eschborn",
#                        "PhoneNumber": "0123456789",
#                        "Email": "info@arzt.de",
#                        "Longitude": "8.58267870",
#                        "Latitude": "50.13890310",
#                        "StateId": 0,
#                        "DisplayName": ""
#                    }, {
#                        "Id": "3",
#                        "StreetAddress": "Allerstraße",
#                        "StreetAddressNumber": "38",
#                        "PostalCode": "12049",
#                        "City": "Berlin",
#                        "PhoneNumber": "",
#                        "Email": "",
#                        "Longitude": "13.42412070",
#                        "Latitude": "52.47474330",
#                        "StateId": 0,
#                        "DisplayName": ""
#                    }, {
#                        "Id": "4",
#                        "StreetAddress": "Helfmann-Park - ",
#                        "StreetAddressNumber": "4",
#                        "PostalCode": "65760",
#                        "City": "Eschborn",
#                        "PhoneNumber": "0123456789",
#                        "Email": "info@arzt.de",
#                        "Longitude": "8.58267870",
#                        "Latitude": "50.13890310",
#                        "StateId": 0,
#                        "DisplayName": ""
#                    }, {
#                        "Id": "5",
#                        "StreetAddress": "Helfmann-Park - ",
#                        "StreetAddressNumber": "5",
#                        "PostalCode": "65760",
#                        "City": "Eschborn",
#                        "PhoneNumber": "0123456789",
#                        "Email": "info@arzt.de",
#                        "Longitude": "8.58267870",
#                        "Latitude": "50.13890310",
#                        "StateId": 0,
#                        "DisplayName": ""
#                    }, {
#                        "Id": "6",
#                        "StreetAddress": "Helfmann-Park - ",
#                        "StreetAddressNumber": "6",
#                        "PostalCode": "65760",
#                        "City": "Eschborn",
#                        "PhoneNumber": "0123456789",
#                        "Email": "info@arzt.de",
#                        "Longitude": "8.58267870",
#                        "Latitude": "50.13890310",
#                        "StateId": 0,
#                        "DisplayName": ""
#                    }, {
#                        "Id": "7",
#                        "StreetAddress": "Helfmann-Park - ",
#                        "StreetAddressNumber": "7",
#                        "PostalCode": "65760",
#                        "City": "Eschborn",
#                        "PhoneNumber": "0123456789",
#                        "Email": "info@arzt.de",
#                        "Longitude": "8.58267870",
#                        "Latitude": "50.13890310",
#                        "StateId": 0,
#                        "DisplayName": ""
#                    }, {
#                        "Id": "8",
#                        "StreetAddress": "Helfmann-Park",
#                        "StreetAddressNumber": "",
#                        "PostalCode": "65760",
#                        "City": "",
#                        "PhoneNumber": "",
#                        "Email": "",
#                        "Longitude": "8.58218278",
#                        "Latitude": "50.13807870",
#                        "StateId": 0,
#                        "DisplayName": ""
#                    }, {
#                        "Id": "9",
#                        "StreetAddress": "Helfmann-Park - ",
#                        "StreetAddressNumber": "9",
#                        "PostalCode": "65760",
#                        "City": "Eschborn",
#                        "PhoneNumber": "0123456789",
#                        "Email": "info@arzt.de",
#                        "Longitude": "8.58267870",
#                        "Latitude": "50.13890310",
#                        "StateId": 0,
#                        "DisplayName": ""
#                    }, {
#                        "Id": "10",
#                        "StreetAddress": "",
#                        "StreetAddressNumber": "",
#                        "PostalCode": "84094",
#                        "City": "",
#                        "PhoneNumber": "",
#                        "Email": "",
#                        "Longitude": "11.79983838",
#                        "Latitude": "48.71797980",
#                        "StateId": 0,
#                        "DisplayName": ""
#                    }, {
#                        "Id": "11",
#                        "StreetAddress": "Helfmann-Park - ",
#                        "StreetAddressNumber": "11",
#                        "PostalCode": "65760",
#                        "City": "Eschborn",
#                        "PhoneNumber": "0123456789",
#                        "Email": "info@arzt.de",
#                        "Longitude": "8.58267870",
#                        "Latitude": "50.13890310",
#                        "StateId": 0,
#                        "DisplayName": ""
#                    }, {
#                        "Id": "12",
#                        "StreetAddress": "Helfmann-Park - ",
#                        "StreetAddressNumber": "12",
#                        "PostalCode": "65760",
#                        "City": "Eschborn",
#                        "PhoneNumber": "0123456789",
#                        "Email": "info@arzt.de",
#                        "Longitude": "8.58267870",
#                        "Latitude": "50.13890310",
#                        "StateId": 0,
#                        "DisplayName": ""
#                    }, {
#                        "Id": "13",
#                        "StreetAddress": "Helfmann-Park - ",
#                        "StreetAddressNumber": "13",
#                        "PostalCode": "65760",
#                        "City": "Eschborn",
#                        "PhoneNumber": "0123456789",
#                        "Email": "info@arzt.de",
#                        "Longitude": "8.58267870",
#                        "Latitude": "50.13890310",
#                        "StateId": 0,
#                        "DisplayName": ""
#                    }, {
#                        "Id": "14",
#                        "StreetAddress": "Theaterstraße",
#                        "StreetAddressNumber": "12",
#                        "PostalCode": "97070",
#                        "City": "Würzburg",
#                        "PhoneNumber": "",
#                        "Email": "",
#                        "Longitude": "9.93450510",
#                        "Latitude": "49.79613850",
#                        "StateId": 0,
#                        "DisplayName": "12, Theaterstraße, Altstadt, Würzburg Altstadt, Würzburg, Bayern, 97070, Deutschland"
#                    }, {
#                        "Id": "15",
#                        "StreetAddress": "Kochstraße",
#                        "StreetAddressNumber": "42",
#                        "PostalCode": "04275",
#                        "City": "Leipzig",
#                        "PhoneNumber": "",
#                        "Email": "",
#                        "Longitude": "12.37127210",
#                        "Latitude": "51.31991240",
#                        "StateId": 0,
#                        "DisplayName": "Allgemeinmedizin, 42, Kochstraße, Südvorstadt, Süd, Leipzig, Sachsen, 04275, Deutschland"
#                    }, {
#                        "Id": "16",
#                        "StreetAddress": "Aesculap-Platz",
#                        "StreetAddressNumber": "",
#                        "PostalCode": "78532",
#                        "City": "",
#                        "PhoneNumber": "",
#                        "Email": "",
#                        "Longitude": "8.80231940",
#                        "Latitude": "47.98070120",
#                        "StateId": 0,
#                        "DisplayName": "Aesculap-Platz, Tuttlingen, Verwaltungsgemeinschaft Tuttlingen, Landkreis Tuttlingen, Baden-Württemberg, 78532, Deutschland"
#                    }, {
#                        "Id": "17",
#                        "StreetAddress": "",
#                        "StreetAddressNumber": "",
#                        "PostalCode": "78112",
#                        "City": "",
#                        "PhoneNumber": "",
#                        "Email": "",
#                        "Longitude": "8.33302470",
#                        "Latitude": "48.12576420",
#                        "StateId": 0,
#                        "DisplayName": "St. Georgen im Schwarzwald, Schwarzwald-Baar-Kreis, Baden-Württemberg, 78112, Deutschland"
#                    }, {
#                        "Id": "18",
#                        "StreetAddress": "Lessingstraße",
#                        "StreetAddressNumber": "9",
#                        "PostalCode": "01904",
#                        "City": "",
#                        "PhoneNumber": "",
#                        "Email": "",
#                        "Longitude": "14.31714590",
#                        "Latitude": "51.09221040",
#                        "StateId": 0,
#                        "DisplayName": "Dr. med. Franziska Paetzold, 9, Lessingstraße, Viehbighäuser, Neukirch/Lausitz, Bautzen, Sachsen, 01904, Deutschland"
#                    }, {
#                        "Id": "19",
#                        "StreetAddress": "Joliot-Curie-Straße",
#                        "StreetAddressNumber": "1",
#                        "PostalCode": "02826",
#                        "City": "",
#                        "PhoneNumber": "",
#                        "Email": "",
#                        "Longitude": "14.99237490",
#                        "Latitude": "51.15444370",
#                        "StateId": 0,
#                        "DisplayName": "Dr. Hedrich+Samborski+Czerczuk, 1, Joliot-Curie-Straße, Innenstadt, Görlitz, Sachsen, 02826, Deutschland"
#                    }, {
#                        "Id": "20",
#                        "StreetAddress": "",
#                        "StreetAddressNumber": "",
#                        "PostalCode": "88427",
#                        "City": "",
#                        "PhoneNumber": "",
#                        "Email": "",
#                        "Longitude": "9.65965154",
#                        "Latitude": "47.99197795",
#                        "StateId": 0,
#                        "DisplayName": "Liebherr-Mischtechnik, Sennhof, Bad Schussenried, Verwaltungsgemeinschaft Bad Schussenried, Landkreis Biberach, Baden-Württemberg, 88427, Deutschland"
#                    }, {
#                        "Id": "21",
#                        "StreetAddress": "Biesnitzer Straße",
#                        "StreetAddressNumber": "77a",
#                        "PostalCode": "02826",
#                        "City": "",
#                        "PhoneNumber": "",
#                        "Email": "",
#                        "Longitude": "14.97278540",
#                        "Latitude": "51.14361245",
#                        "StateId": 0,
#                        "DisplayName": "77a, Biesnitzer Straße, Südstadt, Görlitz, Sachsen, 02826, Deutschland"
#                    }, {
#                        "Id": "22",
#                        "StreetAddress": "Wiesenstraße",
#                        "StreetAddressNumber": "5",
#                        "PostalCode": "32756",
#                        "City": "",
#                        "PhoneNumber": "",
#                        "Email": "",
#                        "Longitude": "8.87676289",
#                        "Latitude": "51.93873790",
#                        "StateId": 0,
#                        "DisplayName": "5, Wiesenstraße, Detmold-Nord, Detmold, Kreis Lippe, Nordrhein-Westfalen, 32756, Deutschland"
#                    }, {
#                        "Id": "23",
#                        "StreetAddress": "Elbweg",
#                        "StreetAddressNumber": "13",
#                        "PostalCode": "01824",
#                        "City": "Rathen",
#                        "PhoneNumber": "",
#                        "Email": "",
#                        "Longitude": "14.07882450",
#                        "Latitude": "50.95586720",
#                        "StateId": 0,
#                        "DisplayName": "Arztpraxis Dres. Wegner, 13, Elbweg, Oberrathen, Kurort Rathen, Rathen, Königstein/Sächs. Schw., Sächsische Schweiz-Osterzgebirge, Sachsen, 01824, Deutschland"
#                    }, {
#                        "Id": "24",
#                        "StreetAddress": "Dresdner Straße",
#                        "StreetAddressNumber": "9",
#                        "PostalCode": "01824",
#                        "City": "",
#                        "PhoneNumber": "",
#                        "Email": "",
#                        "Longitude": "14.06906420",
#                        "Latitude": "50.91932320",
#                        "StateId": 0,
#                        "DisplayName": "Praxis für Allgemeinmedizin, 9, Dresdner Straße, Halbestadt, Pfaffendorf, Königstein, Königstein/Sächs. Schw., Sächsische Schweiz-Osterzgebirge, Sachsen, 01824, Deutschland"
#                    }, {
#                        "Id": "25",
#                        "StreetAddress": "Schussenstraße",
#                        "StreetAddressNumber": "3",
#                        "PostalCode": "88212",
#                        "City": "",
#                        "PhoneNumber": "",
#                        "Email": "",
#                        "Longitude": "9.61451530",
#                        "Latitude": "47.78457540",
#                        "StateId": 0,
#                        "DisplayName": "Praxis Groh Rick, 3, Schussenstraße, In den Ziegelhöfen, Nordstadt, Ravensburg, Verwaltungsverband Mittleres Schussental, Landkreis Ravensburg, Baden-Württemberg, 88212, Deutschland"
#                    }, {
#                        "Id": "26",
#                        "StreetAddress": "Greiffeneggring",
#                        "StreetAddressNumber": "1",
#                        "PostalCode": "79098",
#                        "City": "Freiburg im Breisgau",
#                        "PhoneNumber": "",
#                        "Email": "",
#                        "Longitude": "7.85377310",
#                        "Latitude": "47.99225850",
#                        "StateId": 0,
#                        "DisplayName": "1, Greiffeneggring, Altstadt-Mitte, Altstadt, Freiburg im Breisgau, Baden-Württemberg, 79098, Deutschland"
#                    }, {
#                        "Id": "27",
#                        "StreetAddress": "Seffnerstraße",
#                        "StreetAddressNumber": "1",
#                        "PostalCode": "06217",
#                        "City": "",
#                        "PhoneNumber": "",
#                        "Email": "",
#                        "Longitude": "11.99676560",
#                        "Latitude": "51.36003460",
#                        "StateId": 0,
#                        "DisplayName": "1, Seffnerstraße, Neumarkt (Vorstadt), Merseburg, Saalekreis, Sachsen-Anhalt, 06217, Deutschland"
#                    }, {
#                        "Id": "28",
#                        "StreetAddress": "Vennhofallee",
#                        "StreetAddressNumber": "52",
#                        "PostalCode": "33689",
#                        "City": "Bielefeld",
#                        "PhoneNumber": "",
#                        "Email": "",
#                        "Longitude": "8.58293940",
#                        "Latitude": "51.94769360",
#                        "StateId": 0,
#                        "DisplayName": "Dr. med. Andrea Klempin, 52, Vennhofallee, Kracks Hof, Sennestadt, Bielefeld, Nordrhein-Westfalen, 33689, Deutschland"
#                    }, {
#                        "Id": "29",
#                        "StreetAddress": "Erwin-Rommel-Straße",
#                        "StreetAddressNumber": "4",
#                        "PostalCode": "91058",
#                        "City": "Erlangen",
#                        "PhoneNumber": "",
#                        "Email": "",
#                        "Longitude": "11.02650490",
#                        "Latitude": "49.58135830",
#                        "StateId": 0,
#                        "DisplayName": "Dr. Irmtraud Pribylla, 4, Erwin-Rommel-Straße, Sebaldussiedlung, Erlangen, Bayern, 91058, Deutschland"
#                    }, {
#                        "Id": "30",
#                        "StreetAddress": "Maximilianstraße",
#                        "StreetAddressNumber": "11",
#                        "PostalCode": "83471",
#                        "City": "",
#                        "PhoneNumber": "",
#                        "Email": "",
#                        "Longitude": "13.00148693",
#                        "Latitude": "47.63062195",
#                        "StateId": 0,
#                        "DisplayName": "11, Maximilianstraße, Kranzbichl, Mitterbach, Berchtesgaden, Landkreis Berchtesgadener Land, Bayern, 83471, Deutschland"
#                    }, {
#                        "Id": "31",
#                        "StreetAddress": "Kaiser-Maximilian-Platz",
#                        "StreetAddressNumber": "",
#                        "PostalCode": "87629",
#                        "City": "",
#                        "PhoneNumber": "",
#                        "Email": "",
#                        "Longitude": "10.70120489",
#                        "Latitude": "47.56957970",
#                        "StateId": 0,
#                        "DisplayName": "Kaiser-Maximilian-Platz, Am Riesenanger, Füssen, Landkreis Ostallgäu, Bayern, 87629, Deutschland"
#                    }, {
#                        "Id": "32",
#                        "StreetAddress": "Parkstraße",
#                        "StreetAddressNumber": "3",
#                        "PostalCode": "77694",
#                        "City": "",
#                        "PhoneNumber": "",
#                        "Email": "",
#                        "Longitude": "7.83397817",
#                        "Latitude": "48.60227380",
#                        "StateId": 0,
#                        "DisplayName": "3, Parkstraße, Auenheim, Kehl, Ortenaukreis, Baden-Württemberg, 77694, Deutschland"
#                    }
#                ]
#            }
#        }
#    }
