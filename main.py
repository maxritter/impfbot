
import sys
import time
from src import helios
from src.zollsoft import zollsoft_check
from src.doctolib import doctolib_check
from src import helper


def main(args=None):
    # Parameters
    if args is None:
        args = sys.argv[1:]
    city = args[0]

    # Initialization
    helper.init(city)
    roundTime = time.time()
    clearTime = time.time()

    # Continously check the various APIs
    helper.info_log('Searching for appointments now..')
    while True:
        try:
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
                helios.helios_check(city)

            # Check Doctolib list
            doctolib_check(city)

            # Wait at least 10 seconds between the rounds
            if int(time.time() - roundTime) < 10:
                time.sleep(abs(10 - int(time.time() - roundTime)))

            # Show round time in local mode
            if helper.is_local():
                helper.info_log(
                    f'Round time: {int(time.time() - roundTime)} seconds')
            roundTime = time.time()

        except Exception as e:
            helper.error_log(f'[General] Main loop error [{str(e)}]')
            continue


if __name__ == "__main__":
    sys.exit(main())
