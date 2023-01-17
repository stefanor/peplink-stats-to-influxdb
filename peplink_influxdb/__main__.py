import argparse
import configparser

from influxdb import InfluxDBClient
from peplink_api.services import PepLinkClientService
import urllib3

from peplink_influxdb.monitor import Monitor


def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        "-c", "--config", type=open, default="config.ini", help="Configuration File"
    )
    args = p.parse_args()

    config = configparser.ConfigParser()
    config.read(args.config.name)

    influx = InfluxDBClient(
        host=config["influxdb"]["host"],
        port=config["influxdb"].getint("port"),
        username=config["influxdb"]["username"],
        password=config["influxdb"]["password"],
        database=config["influxdb"]["database"],
    )
    influx.create_database(config["influxdb"]["database"])
    influx.create_retention_policy(
        name="1yr", duration="365d", replication=1, default=True
    )
    influx.drop_retention_policy(name="autogen")

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    peplink = PepLinkClientService(
        config["peplink"]["url"],
        config["peplink"]["client_id"],
        config["peplink"]["client_secret"],
    )

    m = Monitor(influx, peplink, config["monitor"].getint("interval"))
    # To confirm that everything works:
    m.run_once()
    m.sleep()
    m.run_forever()


if __name__ == "__main__":
    main()
