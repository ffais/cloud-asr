import unittest
from lib import Master
from cloudasr.test_doubles import PollerSpy


class TestMaster(unittest.TestCase):

    def setUp(self):
        self.poller = PollerSpy()
        self.master = Master(self.poller, self.poller.has_next_message)

    def test_when_no_worker_is_available_master_responds_with_error(self):
        messages = [
            {"frontend": self.make_frontend_request()},
        ]
        self.run_master(messages)

        expected_message = self.make_frontend_error_response("No worker available")
        self.assertEquals([expected_message], self.poller.sent_messages["frontend"])

    def test_when_no_appropriate_worker_is_available_master_responds_with_error(self):
        messages = [
            {"worker": self.make_heartbeat_request("tcp://127.0.0.1:1", "en-US")},
            {"frontend": self.make_frontend_request("en-GB")}
        ]
        self.run_master(messages)

        expected_message = self.make_frontend_error_response("No worker available")
        self.assertEquals([expected_message], self.poller.sent_messages["frontend"])

    def test_when_worker_is_available_master_sends_his_address_to_frontend(self):
        worker_address = "tcp://127.0.0.1:1"
        messages = [
            {"worker": self.make_heartbeat_request(worker_address)},
            {"frontend": self.make_frontend_request()},
            {"worker": self.make_heartbeat_request(worker_address)},
            {"frontend": self.make_frontend_request()}
        ]
        self.run_master(messages)

        expected_message = self.make_frontend_successfull_response("tcp://127.0.0.1:1")
        self.assertEquals([expected_message, expected_message], self.poller.sent_messages["frontend"])

    def test_when_worker_sends_two_heartbeats_it_is_available_only_to_first_frontend_request(self):
        worker_address = "tcp://127.0.0.1:1"
        messages = [
            {"worker": self.make_heartbeat_request(worker_address)},
            {"worker": self.make_heartbeat_request(worker_address)},
            {"frontend": self.make_frontend_request()},
            {"frontend": self.make_frontend_request()}
        ]
        self.run_master(messages)

        expected_message1 = self.make_frontend_successfull_response("tcp://127.0.0.1:1")
        expected_message2 = self.make_frontend_error_response("No worker available")
        self.assertEquals([expected_message1, expected_message2], self.poller.sent_messages["frontend"])

    def test_when_worker_sent_heartbeat_and_went_silent_for_10secs_then_it_is_not_available_anymore(self):
        worker_address = "tcp://127.0.0.1:1"
        messages = [
            {"worker": self.make_heartbeat_request(worker_address)},
            {"frontend": self.make_frontend_request(), "time": +10}
        ]
        self.run_master(messages)

        expected_message = self.make_frontend_error_response("No worker available")
        self.assertEquals([expected_message], self.poller.sent_messages["frontend"])

    def test_when_worker_was_not_responding_and_then_it_sent_heartbeat_it_should_be_available_again(self):
        worker_address = "tcp://127.0.0.1:1"
        messages = [
            {"worker": self.make_heartbeat_request(worker_address)},
            {"worker": self.make_heartbeat_request(worker_address), "time": +100},
            {"frontend": self.make_frontend_request()}
        ]
        self.run_master(messages)

        expected_message = self.make_frontend_successfull_response("tcp://127.0.0.1:1")
        self.assertEquals([expected_message], self.poller.sent_messages["frontend"])

    def run_master(self, messages):
        self.poller.add_messages(messages)
        self.master.run()

    def make_heartbeat_request(self, worker_address, model="en-GB"):
        return {
            "address": worker_address,
            "model": model
        }

    def make_frontend_request(self, model="en-GB"):
        return {
            "model": model
        }

    def make_frontend_successfull_response(self, address):
        return {
            "status": "success",
            "address": address
        }

    def make_frontend_error_response(self, message):
        return {
            "status": "error",
            "message": message
        }
