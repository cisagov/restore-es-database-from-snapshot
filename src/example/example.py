#!/usr/bin/env python

"""example is an example Python library and tool.

Usage:
  example [--log-level=LEVEL]
  example (-h | --help)

Options:
  -h --help              Show this message.
  --log-level=LEVEL      If specified, then the log level will be set to
                         the specified value.  Valid values are "debug", "info",
                         "warning", "error", and "critical". [default: warning]
"""

from datetime import datetime
import logging
import sys

import boto3
import curator
import docopt
from elasticsearch import Elasticsearch, RequestsHttpConnection
import requests
from requests_aws4auth import AWS4Auth

# from ._version import __version__

DEFAULT_ECHO_MESSAGE = "Hello World from the example default!"


def example_div(x, y):
    """Print some logging messages."""
    logging.debug("This is a debug message")
    logging.info("This is an info message")
    logging.warning("This is a warning message")
    logging.error("This is an error message")
    logging.critical("This is a critical message")
    return x / y


def main():
    """Set up logging and call the example function."""
    args = docopt.docopt(__doc__)  # ,version=__version__)
    # Set up logging
    log_level = args["--log-level"]
    try:
        logging.basicConfig(
            format="%(asctime)-15s %(levelname)s %(message)s", level=log_level.upper()
        )
    except ValueError:
        logging.critical(
            f'"{log_level}" is not a valid logging level.  Possible values '
            "are debug, info, warning, and error."
        )
        return 1

    host = "search-dmarc-import-elasticsearch-dtbgkfx23yppmjmothuy6t7wd4.us-east-1.es.amazonaws.com"
    region = "us-east-1"
    service = "es"
    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        region,
        service,
        session_token=credentials.token,
    )
    # Build the Elasticsearch client.
    es = Elasticsearch(
        hosts=[{"host": host, "port": 443}],
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        # Deleting snapshots can take a while, so keep the connection
        # open for long enough to get a response.
        timeout=360,
    )

    try:
        # response = requests.get("https://{}/_snapshot?pretty".format(host),
        #                         auth=awsauth,
        #                         headers={'Content-Type': 'application/json'},
        #                         timeout=300)
        # print(response.json())

        # Get the last 10 snapshots in the repository before the
        # 08/31/2019 power outage
        snapshot_list = curator.SnapshotList(es, repository="cs-automated-enc")
        snapshot_list.filter_by_age(
            source="creation_date",
            direction="older",
            epoch=datetime(2019, 8, 31, 14).timestamp(),
            unit="hours",
            unit_count=3,
        )
        snapshot_list.filter_by_count(10, exclude=False)
        # print(snapshot_list.snapshots)

        # Get the list of indices
        # index_list = curator.IndexList(es)
        # print(index_list.all_indices)

        # Delete the dmarc_aggregate_reports index
        # delete_indices_action = curator.DeleteIndices(index_list)
        # delete_indices_action.do_action()

        # Restore the last good snapshot
        #
        # Sadly AWS ES does not support
        # /_snapshot/cs-automated-enc/_verify, so this doesn't work.
        # restore_action = curator.Restore(snapshot_list, "2019-08-31t12-34-01.a1f9be8b-1814-404f-a551-a7a1a4e651a9", indices=["dmarc_aggregate_reports"])
        # restore_action.do_action()

        response = requests.post(
            "https://{}/_snapshot/cs-automated-enc/{}/_restore".format(
                host, "2019-08-31t12-34-01.a1f9be8b-1814-404f-a551-a7a1a4e651a9"
            ),
            auth=awsauth,
            headers={"Content-Type": "application/json"},
            timeout=600,
        )
        print(response.json())
    except (
        curator.exceptions.SnapshotInProgress,
        curator.exceptions.NoSnapshots,
        curator.exceptions.FailedExecution,
    ) as e:
        print(e)

    # Stop logging and clean up
    logging.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
