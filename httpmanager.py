import requests
import json

remote_url = ""
device_id = ""
bearer = ""
api_key = ""
app_id = ""

def url(endpoint):
        return "{0}{1}".format(remote_url, endpoint)

def headers_with_headers(headers):
    new_headers = {}
    new_headers["Content-Type"] = "application/json"
    new_headers["X-BLGREQ-UDID"] = device_id
    new_headers["X-BLGREQ-SIGN"] = api_key
    new_headers["X-BLGREQ-APPID"] = app_id
    if bearer:
        new_headers["Authorization"] = "Bearer {0}".format(bearer)
    if headers:
        return dict(list(new_headers.items()) + list(headers.items()))
    else:
        return new_headers

def get(endpoint, parameters, headers):
        return requests.get(url(endpoint), params=parameters, headers=headers_with_headers(headers))

def post(endpoint, parameters, headers):
        return requests.post(url(endpoint), data=json.dumps(parameters), headers=headers_with_headers(headers))