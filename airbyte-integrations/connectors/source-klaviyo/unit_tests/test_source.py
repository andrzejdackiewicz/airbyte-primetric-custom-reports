#
# Copyright (c) 2023 Airbyte, Inc., all rights reserved.
#

import pendulum
import pytest
from source_klaviyo.source import SourceKlaviyo


@pytest.mark.parametrize(
    "status_code, response, is_connection_successful, error_msg",
    (
        (200, "", True, None),
        (
            400,
            "Bad request",
            False,
            "HTTPError('400 Client Error: None for url: https://a.klaviyo.com/api/v1/metrics?api_key=***&count=100')",
        ),
        (
            403,
            "Forbidden",
            False,
            "HTTPError('403 Client Error: None for url: https://a.klaviyo.com/api/v1/metrics?api_key=***&count=100')",
        ),
    ),
)
def test_check_connection(requests_mock, status_code, response, is_connection_successful, error_msg):
    requests_mock.register_uri(
        "GET",
        "https://a.klaviyo.com/api/v1/metrics?api_key=api_key&count=100",
        status_code=status_code,
        json={"end": 1, "total": 1} if 200 >= status_code < 300 else {},
    )
    source = SourceKlaviyo()
    success, error = source.check_connection(logger=None, config={"api_key": "api_key"})
    assert success is is_connection_successful
    assert error == error_msg


def test_streams():
    source = SourceKlaviyo()
    config = {"api_key": "some_key", "start_date": pendulum.datetime(2020, 10, 10).isoformat()}
    streams = source.streams(config)
    expected_streams_number = 8
    assert len(streams) == expected_streams_number

    # ensure only unique stream names are returned
    assert len({stream.name for stream in streams}) == expected_streams_number
