import ssl
import socket

from contextlib import closing

import click

from cryptography import x509
from cryptography.hazmat.backends import default_backend

import icalendar

from werkzeug.exceptions import HTTPException
from werkzeug.routing import Map, Rule
from werkzeug.serving import run_simple
from werkzeug.wrappers import Response, Request

import yaml


class StaticHostDatabase(object):
    def __init__(self, hosts):
        self.hosts = hosts

    def gethosts(self, request):
        return self.hosts


class WSGIApplication(object):
    def __init__(self, host_db):
        self.host_db = host_db

        self.url_map = Map([
            Rule(r"/", endpoint=self.home)
        ])

    def __call__(self, environ, start_response):
        request = Request(environ)
        response = self.handle_request(request)
        return response(environ, start_response)

    def handle_request(self, request):
        adapter = self.url_map.bind_to_environ(request)
        try:
            endpoint, args = adapter.match()
            return endpoint(request, **args)
        except HTTPException as e:
            return e

    def home(self, request):
        cal = self.create_calendar()
        for host in self.host_db.gethosts(request):
            cert = self.get_certificate(host)
            self.add_to_calendar(cal, host, cert)

        return Response(cal.to_ical(), content_type="text/calendar")

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
            sock.connect((hostname, 443))

            return x509.load_der_x509_certificate(
                sock.getpeercert(True), backend=default_backend()
            )


@click.command()
@click.argument("config")
def main(config):
    with open(config) as f:
        config = yaml.safe_load(f.read())
    host_db = StaticHostDatabase(config["hosts"])
    run_simple("localhost", 4000, WSGIApplication(host_db))


if __name__ == "__main__":
    main()
