"""
Tests for the metrics system.

This module contains unit tests for the metrics collection and reporting.
"""

import time
import unittest
from unittest.mock import patch, MagicMock, call

from fastapi.testclient import TestClient
from fastapi import FastAPI, Response

from app.core.config import settings
from app.metrics import (
    init_app,
    report_gauge,
    increment_counter,
    report_timing,
    report_histogram,
    timing
)
from app.metrics.tasks import task_timer, async_task_timer
from app.metrics.algorithm import track_match_operation


class TestMetrics(unittest.TestCase):
    """Test suite for metrics functionality."""

    def setUp(self):
        """Set up test environment."""
        # Enable metrics for testing
        settings.metrics_enabled = True
        settings.metrics_backend = "logging"  # Use logging backend for tests
        
        # Create test FastAPI app
        self.app = FastAPI()
        init_app(self.app)
        
        # Create test client
        self.client = TestClient(self.app)
        
        # Add test endpoint
        @self.app.get("/test")
        def test_endpoint():
            increment_counter("test.endpoint.called")
            report_gauge("test.gauge", 42)
            return {"message": "test"}
        
        @self.app.get("/slow")
        def slow_endpoint():
            time.sleep(0.1)  # Simulate slow operation
            return {"message": "slow"}

    def tearDown(self):
        """Clean up after tests."""
        settings.metrics_enabled = True

    @patch("app.metrics.core._log_metric")
    def test_report_gauge(self, mock_log_metric):
        """Test reporting gauge metric."""
        # Report gauge
        report_gauge("test.gauge", 42, {"tag1": "value1"})
        
        # Check if metric was logged
        mock_log_metric.assert_called_once_with(
            "gauge", "test.gauge", 42, {"tag1": "value1"}
        )

    @patch("app.metrics.core._log_metric")
    def test_increment_counter(self, mock_log_metric):
        """Test incrementing counter metric."""
        # Increment counter
        increment_counter("test.counter", {"tag1": "value1"}, 2)
        
        # Check if metric was logged
        mock_log_metric.assert_called_once_with(
            "counter", "test.counter", 2, {"tag1": "value1"}
        )

    @patch("app.metrics.core._log_metric")
    def test_report_timing(self, mock_log_metric):
        """Test reporting timing metric."""
        # Report timing
        report_timing("test.timing", 0.123, {"tag1": "value1"})
        
        # Check if metric was logged
        mock_log_metric.assert_called_once_with(
            "timing", "test.timing", 0.123, {"tag1": "value1"}
        )

    @patch("app.metrics.core._log_metric")
    def test_report_histogram(self, mock_log_metric):
        """Test reporting histogram metric."""
        # Report histogram
        report_histogram("test.histogram", 42.0, {"tag1": "value1"})
        
        # Check if metric was logged
        mock_log_metric.assert_called_once_with(
            "histogram", "test.histogram", 42.0, {"tag1": "value1"}
        )

    @patch("app.metrics.core.report_timing")
    def test_timing_context_manager(self, mock_report_timing):
        """Test timing context manager."""
        # Use timing context manager
        with timing("test.operation", {"tag1": "value1"}):
            time.sleep(0.01)  # Small operation
        
        # Check if timing was reported
        self.assertEqual(mock_report_timing.call_count, 1)
        
        # Verify call arguments
        args, kwargs = mock_report_timing.call_args
        self.assertEqual(args[0], "test.operation")
        self.assertEqual(args[2], {"tag1": "value1"})
        
        # Duration should be positive
        self.assertGreater(args[1], 0)

    @patch("app.metrics.core.increment_counter")
    @patch("app.metrics.core.report_timing")
    def test_task_timer_decorator(self, mock_report_timing, mock_increment_counter):
        """Test task timer decorator."""
        # Define test task
        @task_timer("test.task")
        def test_task(x, y):
            time.sleep(0.01)  # Small operation
            return x + y
        
        # Execute test task
        result = test_task(2, 3)
        
        # Check result
        self.assertEqual(result, 5)
        
        # Check if metrics were reported
        mock_increment_counter.assert_called_once()
        mock_report_timing.assert_called_once()
        
        # Verify counter call
        counter_args, counter_kwargs = mock_increment_counter.call_args
        self.assertEqual(counter_args[0], "task.count")
        self.assertEqual(counter_args[1], {"task": "test.task", "status": "success"})
        
        # Verify timing call
        timing_args, timing_kwargs = mock_report_timing.call_args
        self.assertEqual(timing_args[0], "task.duration")
        self.assertEqual(timing_args[2], {"task": "test.task", "status": "success"})
        
        # Duration should be positive
        self.assertGreater(timing_args[1], 0)

    @patch("app.metrics.core.increment_counter")
    @patch("app.metrics.core.report_timing")
    def test_error_in_task_timer(self, mock_report_timing, mock_increment_counter):
        """Test error handling in task timer decorator."""
        # Define test task with error
        @task_timer("test.error_task")
        def error_task():
            time.sleep(0.01)  # Small operation
            raise ValueError("Test error")
        
        # Execute test task (should raise error)
        with self.assertRaises(ValueError):
            error_task()
        
        # Check if metrics were reported with error status
        mock_increment_counter.assert_called_once()
        mock_report_timing.assert_called_once()
        
        # Verify counter call with error tags
        counter_args, counter_kwargs = mock_increment_counter.call_args
        self.assertEqual(counter_args[0], "task.count")
        self.assertEqual(
            counter_args[1], 
            {"task": "test.error_task", "status": "error", "error_type": "ValueError"}
        )
        
        # Verify timing call with error tags
        timing_args, timing_kwargs = mock_report_timing.call_args
        self.assertEqual(timing_args[0], "task.duration")
        self.assertEqual(
            timing_args[2], 
            {"task": "test.error_task", "status": "error", "error_type": "ValueError"}
        )
        
        # Duration should be positive
        self.assertGreater(timing_args[1], 0)

    @patch("app.metrics.core.increment_counter")
    @patch("app.metrics.core.report_timing")
    def test_algorithm_decorator(self, mock_report_timing, mock_increment_counter):
        """Test algorithm match operation decorator."""
        # Define test match operation
        @track_match_operation("test.match")
        def match_operation(candidates):
            time.sleep(0.01)  # Small operation
            return {"matches": [{"id": 1, "score": 0.95}, {"id": 2, "score": 0.85}]}
        
        # Execute match operation
        result = match_operation([1, 2, 3])
        
        # Check result
        self.assertEqual(len(result["matches"]), 2)
        
        # Check if metrics were reported
        self.assertGreaterEqual(mock_increment_counter.call_count, 1)
        self.assertGreaterEqual(mock_report_timing.call_count, 1)
        
        # Verify at least one counter call for the operation
        counter_called_with_operation = False
        for call_args in mock_increment_counter.call_args_list:
            args, kwargs = call_args
            if args[0] == "algorithm.match.operation.count" and \
               args[1].get("operation") == "test.match":
                counter_called_with_operation = True
                break
        
        self.assertTrue(counter_called_with_operation)
        
        # Verify at least one timing call for the operation
        timing_called_with_operation = False
        for call_args in mock_report_timing.call_args_list:
            args, kwargs = call_args
            if args[0] == "algorithm.match.operation.duration" and \
               args[2].get("operation") == "test.match":
                timing_called_with_operation = True
                break
        
        self.assertTrue(timing_called_with_operation)

    @patch("app.metrics.core.increment_counter")
    def test_http_middleware(self, mock_increment_counter):
        """Test HTTP metrics middleware."""
        # Make test request
        response = self.client.get("/test")
        
        # Check if response is ok
        self.assertEqual(response.status_code, 200)
        
        # Check if HTTP metrics were reported
        http_request_counted = False
        for call_args in mock_increment_counter.call_args_list:
            args, kwargs = call_args
            if args[0] == "http.request.count":
                http_request_counted = True
                # Check tags
                self.assertEqual(args[1]["method"], "GET")
                self.assertEqual(args[1]["path"], "/test")
                self.assertEqual(args[1]["status"], "200")
                self.assertEqual(args[1]["status_class"], "2xx")
                break
        
        self.assertTrue(http_request_counted)


if __name__ == "__main__":
    unittest.main()