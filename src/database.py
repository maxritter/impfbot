import psycopg2
import os
from src import helper


def connect_db():
    if helper.is_local():
        return None

    db_user = 'igagjeizjhukhy'
    db_password = os.getenv(f'DATABASE_PASSWORD')
    db_host = 'ec2-52-213-167-210.eu-west-1.compute.amazonaws.com'
    db_dbname = 'da9mphrrv08do4'
    db_port = 5432

    try:
        db_conn = psycopg2.connect(
            user=db_user, password=db_password, host=db_host, port=db_port, database=db_dbname)
        return db_conn
    except Exception as e:
        helper.error_log(f'[Database] Connection Error [{str(e)}]')

    return None


def insert_vaccination(vaccine, num, city, platform):
    global db_conn, db_initialized

    if helper.is_local():
        return

    db_conn = connect_db()
    if db_conn is None:
        helper.error_log(
            f'[Database] Unable to write entry to DB, as connection failed..')

    vaccine_name = vaccine
    if vaccine_name == "BioNTech (2. Impfung)":
        vaccine_name = "BioNTech"
    elif vaccine_name == "Johnson & Johnson":
        vaccine_name = "Johnson"

    main_city = ''.join((x for x in city if not x.isdigit())).upper()

    try:
        cur = db_conn.cursor()
        cur.execute(
            f"INSERT INTO public.stats(vaccine, num, city, platform) VALUES ('{vaccine_name}', {num}, '{main_city}', '{platform}')")
        db_conn.commit()
        cur.close()
        db_conn.close()
    except Exception as e:
        helper.error_log(f'[Database] Insert vaccination error [{str(e)}]')
