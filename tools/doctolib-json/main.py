import requests
import json
import sys
from os import walk

doctolib_headers = {
    "accept": "*/*",
    "accept-language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
    "cache-control": "no-cache",
    "origin": "https://www.doctolib.de/",
    "pragma": "no-cache",
    "referer": "https://www.doctolib.de/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
}

def main():
    city_files = []
    for (_, _, filenames) in walk('../../data/'):
        city_files.extend(filenames)
        break

    for city_file in city_files:
        print(f"\n\n*** PROCESSING CITY FILE: {city_file} ***\n\n")

        # Load URLs from File
        with open(f'../../data/{city_file}') as url_txt:
            print(f"Opening: ../../data/{city_file}")
            doctolib_urls = url_txt.readlines()
        doctolib_urls = [doctolib_url.strip() for doctolib_url in doctolib_urls]

        # Check all URLs in the city list
        for doctolib_url in doctolib_urls:
            # Get the center and do some basic checks
            center = doctolib_url.split("/")[5]
            print(center)
            request_url = f'https://www.doctolib.de/booking/{center}.json'
            try:
                raw_data = requests.get(
                    request_url,
                    headers=doctolib_headers,
                    timeout=10)
                raw_data.raise_for_status()
            except Exception as e:
                print(
                    f'[Doctolib] General issue during fetch of bookings for center {center} [{str(e)}]')
                continue
            json_data = raw_data.json()
            with open(f'../../json/{center}.txt', 'w') as outfile:
                json.dump(json_data, outfile)

if __name__ == "__main__":
    sys.exit(main())