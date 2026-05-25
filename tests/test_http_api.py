import json

from mma.http_api import ApiHandler
from mma.services import MmaService


class DummyHandler(ApiHandler):
    def __init__(self):
        self.headers = {}
        self.sent = []
        self.body = b""

    def send_response(self, status):
        self.sent.append(("status", status))

    def send_header(self, name, value):
        self.sent.append((name, value))

    def end_headers(self):
        self.sent.append(("end", None))


class Writer:
    def __init__(self):
        self.data = b""

    def write(self, data):
        self.data += data


def test_http_json_response(tmp_path):
    handler = DummyHandler()
    handler.service = MmaService(tmp_path)
    handler.wfile = Writer()

    handler._json(200, {"status": "ok"})

    assert ("status", 200) in handler.sent
    assert json.loads(handler.wfile.data.decode()) == {"status": "ok"}
