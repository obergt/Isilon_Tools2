#!/usr/bin/python
#-------------------------------------------------------------------------------
# Name:        Isilon Tools
# Purpose:     Backup and restore NFS exports on Isilon using RESTful services.
#
# Author:      Tamir Obergot
#              Delivery specialist, EMC
#              tamir.obergot@emc.com
#
# Version:     2.0
#
# Created:     07.12.2014
#
# Licence:     Open to distribute and modify.  This example code is unsupported
#              by both EMC and the author.  IF YOU HAVE PROBLEMS WITH THIS
#              SOFTWARE, THERE IS NO ONE PROVIDING TECHNICAL SUPPORT FOR
#              RESOLVING ISSUES. USE CODE AS IS!
#
#              THIS CODE IS NOT AFFILIATED WITH EMC CORPORATION.
#-------------------------------------------------------------------------------

import json
import logging
import time
import socket
import requests


from isilon.exceptions import (ConnectionError, ObjectNotFound, APIError)


class Session(object):
    def __init__(self, clustername, username, password, services):
        self.log = logging.getLogger('logger_agent')
        self.log.addHandler(logging.NullHandler())

        self.clustername = clustername
        self.url = "https://" + self.clustername + ':8080'
        self.session_url = self.url + '/session/1/session'

        self.username = username
        self.password = password
        self.services = services

        # Create HTTPS Requests session object
        self.s = requests.Session()
        self.s.headers.update({'content-type': 'application/json'})
        self.s.verify = False

        #initialize session timeout values
        self.timeout = 0
        self.r = None

    def log_api_call(self, r, lvl):
        self.log.log(lvl, "======================================== API Call ========================================")
        self.log.log(lvl, "%s  %s , HTTP Code: %d" % (r.request.method, r.request.url, r.status_code))
        self.log.log(lvl, "Request Headers: %s" % r.request.headers)
        self.log.log(lvl, "Request Data : %s" % r.request.body)
        self.log.log(lvl, "")
        self.log.log(lvl, "Response Headers: %s " % r.headers)
        self.log.log(lvl, "Response Data: %s" % (r.text.strip()))
        self.log.log(lvl, "==========================================================================================")

    def debug_last(self):
        if self.r:
            self.log_api_call(self.r, logging.ERROR)

    def api_call(self, method, urlext, **kwargs):
        # check to see if there is a valid session
        if time.time() > self.timeout:
            self.connect()

        url = self.url + urlext

        if len(url) > 8198:
            self.log.exception("URL Length too long: %s", url)

        r = self.s.request(method, url, **kwargs)
        #check for authorization issue and retry if we just need to create a new session
        if r.status_code == 401:
            #self.bad_call(r)
            logging.info("Authentication Failure, trying to reconnect session")
            self.connect()
            r = self.s.request(method, url, **kwargs)

        if r.status_code == 404:
            self.log.log(logging.ERROR, "Object not found!")
            print r.text
            raise ObjectNotFound()
        elif r.status_code == 401:
            self.log_api_call(r, logging.ERROR)
            raise APIError("Authentication failure")
        elif r.status_code == 409 or r.status_code == 500 and urlext == "/platform/3/protocols/nfs/exports":
            self.log.log(logging.INFO, r.text)
        elif r.status_code > 409 and not r.status_code == 500 and urlext == "/platform/3/protocols/nfs/exports":
            self.log_api_call(r, logging.ERROR)
            message = "API Error: %s" % r.text
            raise APIError(message)
        elif r.status_code == 201:
            self.log_api_call(r, logging.DEBUG)
            self.log.log(logging.INFO, "Object created successfully!")
        elif r.status_code == 204:
            self.log_api_call(r, logging.DEBUG)
            self.log.log(logging.INFO, "Object deleted successfully!")

        self.log_api_call(r, logging.DEBUG)
        self.r = r
        return r


    def connect(self):
        # Get an API session cookie from Isilon
        #Cookie is automatically added to HTTP requests session
        logging.debug("--> creating session")
        sessionjson = json.dumps({'username': self.username, 'password': self.password, 'services': self.services})
        try:
            r = self.s.post(self.session_url, data=sessionjson)
            self.s.headers.update({'X-CSRF-Token': r.cookies['isicsrf'],
                                   'Referer': self.url})
        except:
            self.log.log(logging.ERROR, "Max retries exceeded with url.")
            raise Exception("Max retries exceeded with url.")
        if r.status_code != 201:
            self.log_api_call(r, logging.ERROR)
            raise ConnectionError(r.text)

        #Renew Session 60 seconds prior to our timeout
        self.timeout = time.time() + r.json()['timeout_absolute'] - 60
        logging.debug("New Session created! Current clock %d, timeout %d" % (time.time(), self.timeout))
        return True