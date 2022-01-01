import sys
import time
import schedule
from src.zollsoft import zollsoft_check
from src.doctolib import doctolib_check
from src.jameda import jameda_check
from src.helios import helios_check
from src.dachau import dachau_check
from src import helper


def main(args=None):
    # Parameters
    if args is None:
        args = sys.argv[1:]
    city = args[0]

    # Initialization
    helper.init(city)
    schedule.every().day.at("20:00:00").do(helper.send_daily_stats, city)

    # Continously check the various APIs
    helper.info_log("Searching for appointments now..")
    start = time.time()
    while True:
        try:
            # Additional APIs to check
            if city == "muc":
                zollsoft_check(city)
            if city == "muc" or city == "agb":
                dachau_check(city)

            # Check Helios clinics
            if helper.is_helios_enabled(city):
                helios_check(city)

            # Check Jameda
            if helper.is_jameda_enabled(city):
                jameda_check(city)

            # Check Doctolib list
            doctolib_check(city)

            # Check if we need to send out our daily stats
            schedule.run_pending()

            # Print out elapsed time
            end = time.time()
            helper.info_log(f"Round completed in {round(end-start)} seconds")
            start = time.time()

        except Exception as e:
            helper.error_log(f"[General] Main loop error [{str(e)}]")
            continue


if __name__ == "__main__":
    sys.exit(main())
