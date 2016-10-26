#!/usr/bin/env python

import BaseHTTPServer
import SocketServer
import datetime
import errno
import os
import signal
import socket
import json

PLUGIN_ID="volume-count"
PLUGIN_UNIX_SOCK = "/var/run/scope/plugins/" + PLUGIN_ID + ".sock"
METRIC_NAME="http_requests_per_second"
METRIC_LABEL="HTTP req/sec"

class Handler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_GET(self):
        # The logger requires a client_address, but unix sockets don't have
        # one, so we fake it.
        self.client_address = "-"

        # Get current timestamp in RFC3339
        timestamp = datetime.datetime.utcnow()
        timestamp = timestamp.isoformat('T') + 'Z'

        # Generate our json body
        body = json.dumps({
            'Plugins': [
                {
                    'id': PLUGIN_ID,
                    'label': 'Volume Counts',
                    'description': 'Shows how many volumes each container has mounted',
                    'interfaces': ['reporter'],
                    'api_version': '1',
                }
            ],
            'Container': {
                'nodes': {
                    'abcd1234;<container>': {
                        'latest': {
                            'volume_count': {
                                'timestamp': timestamp,
                                'value': '1',
                            }
                        }
                    }
                },
                # Templates tell the UI how to render this field.
                'metadata_templates': {
                    'volume_count': {
                        # Key where this data can be found.
                        'id': "volume_count",
                        # Human-friendly field name
                        'label': "# Volumes",
                        # Look up the 'id' in the latest object.
                        'from': "latest",
                        # Priorities over 10 are hidden, lower is earlier in the list.
                        'priority': 0.1,
                    },
                },
            },
        })

        # Send the headers
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Content-length', len(body))
        self.end_headers()

        # Send the body
        self.wfile.write(body)

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

def delete_socket_file():
    if os.path.exists(PLUGIN_UNIX_SOCK):
        os.remove(PLUGIN_UNIX_SOCK)

def sig_handler(b, a):
    delete_socket_file()
    exit(0)

def main():
    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)

    # Ensure the socket directory exists
    mkdir_p(os.path.dirname(PLUGIN_UNIX_SOCK))
    # Remove existing socket in case it was left behind
    delete_socket_file()
    # Listen for connections on the unix socket
    server = SocketServer.UnixStreamServer(PLUGIN_UNIX_SOCK, Handler)
    try:
        server.serve_forever()
    except:
        delete_socket_file()
        raise

main()
