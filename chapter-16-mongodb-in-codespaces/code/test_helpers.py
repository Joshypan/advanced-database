"""Offline error-semantics and process-ownership checks. No database emulation."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from pymongo.errors import OperationFailure, ServerSelectionTimeoutError
import demo
import server


class HelperTests(unittest.TestCase):
    def test_permission_check_rejects_connectivity_failures(self):
        def denied(): raise OperationFailure('not authorized',code=13)
        demo.expect_denied(denied)
        with self.assertRaises(AssertionError): demo.expect_denied(lambda: None)
        def disconnected(): raise ServerSelectionTimeoutError('offline')
        with self.assertRaises(ServerSelectionTimeoutError): demo.expect_denied(disconnected)

    def test_stale_pid_cannot_signal_this_python_process(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)
            (path/'mongod.pid').write_text(str(os.getpid()))
            with patch.object(server,'DATA',path):
                with patch.object(server.os, 'kill') as kill:
                    try:
                        server.stop()
                    except RuntimeError:
                        pass
                    kill.assert_not_called()


if __name__=='__main__': unittest.main()
