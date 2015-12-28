import ssl
import socket
import sys

from contextlib import closing

import click

from cryptography import x509
from cryptography.hazmat.backends import default_backend

import icalendar

from werkzeug.serving import run_simple
from werkzeug.wrappers import Response, Request

import yaml


class WSGIApplication(object):
    def __init__(self, hostnames):
        self.hostnames = hostnames

    def create_calendar(self):
        cal = icalendar.Calendar()
        cal["summary"] = "When do the certs expire?"
        cal["prodid"] = "-//Certficate Expiration//.../"
        cal["version"] = "1.0"
        return cal

    def add_to_calendar(self, cal, host, cert):
        event = icalendar.Event()
        event["uid"] = "{}:{}".format(host, cert.serial)
        event.add("dtstart", cert.not_valid_after.date())
        event.add("description", "{} certificate expiration".format(host))
        event.add("summary", "The certificate for {}:443 expires".format(host))
        cal.add_component(event)

    def get_certificate(self, hostname):
        ssl_context = ssl.create_default_context()
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            sock = ssl_context.wrap_socket(sock, server_hostname=hostname)
            print hostname
            sock.connect((hostname, 443))

            return x509.load_der_x509_certificate(
                sock.getpeercert(True), backend=default_backend()
            )

    def __call__(self, environ, start_response):
        request = Request(environ)
        response = self.handle_request(request)
        return response(environ, start_response)

    def handle_request(self, request):
        cal = self.create_calendar()
        for host in self.hostnames:
            cert = self.get_certificate(host)
            self.add_to_calendar(cal, host, cert)

        return Response(cal.to_ical(), content_type="text/calendar")


@click.command()
@click.argument("config")
def main(config):
    with open(config) as f:
        config = yaml.safe_load(f.read())
    run_simple("localhost", 4000, WSGIApplication(config["hosts"]))


if __name__ == "__main__":
    main()
