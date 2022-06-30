#
# Copyright (c) 2022 Airbyte, Inc., all rights reserved.
#
from http import HTTPStatus
from unittest.mock import MagicMock, patch

import pytest
from airbyte_cdk.sources.declarative.requesters.retriers.default_retrier import (
    DefaultRetrier,
    HttpResponseFilter,
    NonRetriableResponseStatus,
    RetryResponseStatus,
)


@pytest.mark.parametrize(
    "test_name, http_code, response_headers, should_retry, backoff_time",
    [
        # ("test_bad_gateway", HTTPStatus.BAD_GATEWAY, {}, True, 60),
        # ("test_retry_after", HTTPStatus.BAD_GATEWAY, {"Retry-After": 120}, True, 120),
        # ("test_bad_gateway", HTTPStatus.BAD_GATEWAY, {"X-RateLimit-Reset": 1655804724}, True, 300.0),
    ],
)
@patch("time.time", return_value=1655804424.0)
def test_something(time_mock, test_name, http_code, response_headers, should_retry, backoff_time):
    response_mock = MagicMock()
    response_mock.status_code = http_code
    response_mock.headers = response_headers
    retrier = DefaultRetrier()
    assert retrier.should_retry(response_mock) == should_retry
    assert retrier.backoff_time(response_mock) == backoff_time


@pytest.mark.parametrize(
    "test_name, http_code, retry_response_filter, ignore_response_filter, response_headers, should_retry",
    [
        ("test_bad_gateway", HTTPStatus.BAD_GATEWAY, None, None, {}, RetryResponseStatus(None)),
        ("test_200", HTTPStatus.OK, None, None, {}, NonRetriableResponseStatus.Ok),
        ("test_3XX", HTTPStatus.PERMANENT_REDIRECT, None, None, {}, NonRetriableResponseStatus.Ok),
        ("test_403", HTTPStatus.FORBIDDEN, None, None, {}, NonRetriableResponseStatus.FAIL),
        (
            "test_403_ignore_error_message",
            HTTPStatus.FORBIDDEN,
            None,
            HttpResponseFilter(error_message_contain="found"),
            {},
            NonRetriableResponseStatus.IGNORE,
        ),
        (
            "test_403_dont_ignore_error_message",
            HTTPStatus.FORBIDDEN,
            None,
            HttpResponseFilter(error_message_contain="not_found"),
            {},
            NonRetriableResponseStatus.FAIL,
        ),
        ("test_429", HTTPStatus.TOO_MANY_REQUESTS, None, None, {}, RetryResponseStatus(None)),
        (
            "test_ignore_403",
            HTTPStatus.FORBIDDEN,
            None,
            HttpResponseFilter(http_codes=[HTTPStatus.FORBIDDEN]),
            {},
            NonRetriableResponseStatus.IGNORE,
        ),
        (
            "test_403_with_predicate",
            HTTPStatus.FORBIDDEN,
            HttpResponseFilter(predicate="{{ 'code' in decoded_response }}"),
            None,
            {},
            RetryResponseStatus(None),
        ),
        (
            "test_403_with_predicate",
            HTTPStatus.FORBIDDEN,
            HttpResponseFilter(predicate="{{ 'some_absent_field' in decoded_response }}"),
            None,
            {},
            NonRetriableResponseStatus.FAIL,
        ),
        ("test_retry_403", HTTPStatus.FORBIDDEN, HttpResponseFilter([HTTPStatus.FORBIDDEN]), None, {}, RetryResponseStatus(None)),
    ],
)
@patch("time.time", return_value=1655804424.0)
def test_default_retrier(time_mock, test_name, http_code, retry_response_filter, ignore_response_filter, response_headers, should_retry):
    response_mock = MagicMock()
    response_mock.status_code = http_code
    response_mock.headers = response_headers
    response_mock.json.return_value = {"code": "1000", "error": "found"}
    response_mock.ok = http_code < 400
    retrier = DefaultRetrier(retry_response_filter=retry_response_filter, ignore_response_filter=ignore_response_filter)
    assert retrier.should_retry(response_mock) == should_retry
    if isinstance(should_retry, RetryResponseStatus):
        assert retrier.backoff_time(response_mock) == should_retry.retry_in
