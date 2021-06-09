
import sys
import schedule
from src.zollsoft import zollsoft_check
from src.doctolib import doctolib_check
from src.samedi import samedi_check
from src.jameda import jameda_check
from src.helios import helios_check
from src import helper


def main(args=None):
    # Parameters
    if args is None:
        args = sys.argv[1:]
    city = args[0]

    # Initialization
    helper.init(city)
    schedule.every().day.at("20:15:00").do(helper.send_daily_stats, city)

    # Continously check the various APIs
    helper.info_log('Searching for appointments now..')
    while True:
        try:
            # For Munich, we have additional APIs to check
            if city == 'muc6':
                zollsoft_check(city)
                samedi_check(city)                

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

        except Exception as e:
            helper.error_log(f'[General] Main loop error [{str(e)}]')
            continue


if __name__ == "__main__":
    sys.exit(main())
