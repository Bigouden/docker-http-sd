#!/usr/bin/env python3
#coding: utf-8

''' Docker HTTP Service Discovery '''

import os
import logging
import json
import re
import sys
from collections import defaultdict
from http.server import HTTPServer, BaseHTTPRequestHandler
import docker


# Global Variables
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()
LABEL_PREFIX = os.environ.get('LABEL_PREFIX', 'docker-http-sd')
LABEL_SUFFIX = {'port', 'network', 'targets'}
TARGETS_DELIMITER = os.environ.get('TARGETS_DELIMITER', ',')
VALID_TARGETS_DELIMITER = {',', ';', ':', '!', '?', '+', '|'}

# Logging Configuration
try:
    logging.basicConfig(stream=sys.stdout,
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        datefmt='%d/%m/%Y %H:%M:%S',
                        level=LOG_LEVEL)
except ValueError:
    logging.basicConfig(stream=sys.stdout,
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        datefmt='%d/%m/%Y %H:%M:%S',
                        level='INFO')
    logging.error("LOGLEVEL invalid !")
    sys.exit(1)

# HTTP Port Verification
try:
    HTTP_PORT = int(os.environ.get('HTTP_PORT', '9999'))
except ValueError:
    logging.error("HTTP_PORT must be int !")
    sys.exit(1)

# TARGETS Delimiter Verification
if TARGETS_DELIMITER not in VALID_TARGETS_DELIMITER:
    logging.error("INVALID TARGETS_DELIMITER: '%s' (VALID: '%s')",
                   TARGETS_DELIMITER,
                   "' or '".join(VALID_TARGETS_DELIMITER))
    sys.exit(1)


# Functions Definition
def discover():
    ''' Discover & Filter Containers Labels '''

    try:
        containers = docker.from_env().containers.list()
    except docker.errors.DockerException as exception:
        logging.error(str(exception))
        return 500, {'exception': str(exception)}

    res = []

    for container in containers:
        _ = {}
        services = defaultdict(lambda: {'targets': [],
                                        'network': str(),
                                        'port': int(),
                                        'labels': []})
        _['container'] = container.name

        for label, value in container.labels.items():
            label_split = label.split('.')
            if ((label.startswith(LABEL_PREFIX)
                 and len(label_split) == 3
                 and label.endswith(tuple(LABEL_SUFFIX))
                or (label.startswith(LABEL_PREFIX)
                 and len(label_split) == 4
                 and label_split[2] == "labels"))):
                service = label_split[1]
                if label_split[2] == "targets":
                    services[service]['targets'] = re.sub(r'\s+', '',
                                                          value).split(TARGETS_DELIMITER)
                if label_split[2] == "network":
                    services[service]['network'] = value
                if label_split[2] == "port":
                    try:
                        services[service]['port'] = int(value)
                    except ValueError:
                        logging.error('INVALID PORT %s FOR SERVICE %s ' \
                                      'ON CONTAINER %s.', value, service, container.name)
                if label_split[2] == "labels":
                    key = label_split[3]
                    services[service]['labels'].append({'label': key, 'value': value})
            else:
                logging.debug("SKIPPING LABEL: %s", label)

        _['services'] = services

        for key, value in _['services'].items():
            item = defaultdict(dict)
            item['targets'] = value['targets']
            item['labels']['__meta_port'] = str(value['port'])
            item['labels']['__meta_container'] = _['container']
            try:
                item['labels']['__meta_address'] = container.attrs['NetworkSettings'] \
                                                                  ['Networks'] \
                                                                  [value['network']] \
                                                                  ['IPAddress']
            except KeyError:
                logging.error('INVALID NETWORK %s FOR SERVICE %s ' \
                              'ON CONTAINER %s.', value['network'], key, container.name)
            item['labels']['__meta_service'] = key
            for label in value['labels']:
                item['labels'][f"__meta_{label['label']}"] = label['value']
            res.append(dict(item))
            logging.info('SERVICE DISCOVERY: %s', dict(item))

    return 200, list(res)

# Class Definition
class GetHandler(BaseHTTPRequestHandler):
    '''  GET Handler Class '''

    def _set_headers(self, code):
        ''' Manage HTTP Headers & HTTP Code '''
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()

    def do_GET(self):
        ''' Handle HTTP GET Request '''
        code, response = discover()
        self._set_headers(code)
        data = json.dumps(response)
        self.wfile.write(data.encode())

# Main Program
if __name__ == '__main__':
    logging.info("STARTING HTTP SERVER ON PORT: %s.", HTTP_PORT)
    logging.debug("LOG_LEVEL: %s", LOG_LEVEL)
    logging.debug("HTTP_PORT: %s", HTTP_PORT)
    logging.debug("LABEL_PREFIX: %s", LABEL_PREFIX)
    logging.debug("TARGETS_DELIMITER: %s", TARGETS_DELIMITER)
    httpd = HTTPServer(('0.0.0.0', HTTP_PORT), GetHandler)
    httpd.serve_forever()
