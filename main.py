
import sys
import time
from src.helios import helios_check
from src.zollsoft import zollsoft_check
from src.doctolib import doctolib_check
from src import helper


def main(args=None):
    # Parameters
    if args is None:
        args = sys.argv[1:]
    city = args[0]

    # Initialization
    print(f'Init Impfbot for {city.upper()}..')
    helper.init(city)
    roundTime = time.time()
    clearTime = time.time()

    # Continously check the various APIs
    print(f'{city}: Searching for appointments now..')
    while True:
        # Show round time in local mode
        if helper.is_local() and (time.time() - roundTime > 1):
            print("Round time: " + str(int(time.time() - roundTime)) + " seconds")
            roundTime = time.time()

        # Clear buffer every hour, especially important for Helios
        if not helper.is_local() and (time.time() - clearTime >= (60 * 60)):
            helper.already_sent_ids.clear()
            f'{city}: Clearing buffer now..'
            clearTime = time.time()

        # For Munich, we have a separate API
        if city == 'muc1':
            zollsoft_check(city)
        # Check Helios clinics
        if helper.is_helios_enabled(city):
            helios_check(city)
        # Check Doctolib list
        doctolib_check(city)


if __name__ == "__main__":
    sys.exit(main())
