# -*- coding: utf-8 -*-

# Copyright (c) 2016 James Gardiner

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


from datetime import datetime
from functools import wraps
from time import sleep
import os
import requests

__version__=1.0


class Service(object):

    def __init__(self):
        self._BASE_URI = "https://api.companieshouse.gov.uk/"
        self._DOCUMENT_URI = "https://document-api.companieshouse.gov.uk/"

    @classmethod
    def rate_limit(cls, func):
        """Rate limit a function using the headers returned by the API."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            ret = func(*args, **kwargs)
            return ret
        return wrapper

    def get_session(self, token=None, env=None):
        access_token = (
            token or
            (env or os.environ).get('CompaniesHouseKey') or
            (env or os.environ).get('COMPANIES_HOUSE_KEY'))
        session = requests.Session()

        session.params.update(access_token=access_token)

        # CH API requires a key only, which is passed as the username
        session.headers.update(
            {'User-Agent': ' '.join(
                [self.product_token, requests.utils.default_user_agent()])})
        session.auth = (access_token, '')
        return session

    @property
    def product_token(self):
        """A product token for use in User-Agent headers."""
        return 'chwrapper/{0}'.format(__version__)

    def handle_http_error(self, response, custom_messages={},
                          raise_for_status=True):
        if response.status_code in custom_messages.keys():
            raise requests.exceptions.HTTPError(
                custom_messages[response.status_code])
        elif raise_for_status:
            response.raise_for_status()
