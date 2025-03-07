#!/usr/bin/env python
"""
Simple StatsD Server for development and testing.

This script implements a basic StatsD server that listens for metrics
from the application and prints them to the console or saves to a file.
It's intended for development and testing purposes only.
"""

import socket
import time
import json
import argparse
import signal
import sys
import os
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple, Union, Any


class SimpleStatsDServer:
    """A simple StatsD server for development and testing."""
    
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8125,
        output_file: Optional[str] = None,
        pretty_print: bool = True,
        verbose: bool = False
    ):
        """
        Initialize the StatsD server.
        
        Args:
            host: The host to listen on
            port: The port to listen on
            output_file: Optional file to save metrics to
            pretty_print: Whether to pretty-print the output
            verbose: Whether to print verbose output
        """
        self.host = host
        self.port = port
        self.output_file = output_file
        self.pretty_print = pretty_print
        self.verbose = verbose
        
        # Metric storage
        self.counters: Dict[str, int] = {}
        self.gauges: Dict[str, float] = {}
        self.timers: Dict[str, List[float]] = {}
        self.histograms: Dict[str, List[float]] = {}
        
        # Last seen tags for each metric
        self.metric_tags: Dict[str, Dict[str, str]] = {}
        
        # Metrics received since last flush
        self.metrics_received = 0
        
        # Socket
        self.sock: Optional[socket.socket] = None
        
        # Running flag
        self.running = False
    
    def start(self) -> None:
        """Start the StatsD server."""
        # Create UDP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.host, self.port))
        
        # Set running flag
        self.running = True
        
        # Print startup message
        print(f"StatsD server listening on {self.host}:{self.port}")
        print("Press Ctrl+C to stop")
        
        # Get buffer size
        buffer_size = 8192  # 8KB buffer
        
        # Initialize output file if specified
        if self.output_file:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(self.output_file)), exist_ok=True)
            
            # Write header to file
            with open(self.output_file, "w") as f:
                f.write("# StatsD Metrics Log\n")
                f.write(f"# Started at: {datetime.now().isoformat()}\n")
                f.write("# Format: [timestamp] [metric_type] [metric_name] [value] [tags]\n\n")
        
        # Main loop
        try:
            last_flush_time = time.time()
            
            while self.running:
                # Check if we need to flush metrics
                now = time.time()
                if now - last_flush_time >= 10:  # Flush every 10 seconds
                    self.flush_metrics()
                    last_flush_time = now
                
                # Set socket timeout to allow checking for Ctrl+C
                self.sock.settimeout(1.0)
                
                try:
                    # Receive data
                    data, addr = self.sock.recvfrom(buffer_size)
                    
                    # Process data
                    self.process_packet(data, addr)
                    
                except socket.timeout:
                    # No data received, just continue
                    pass
                    
        except KeyboardInterrupt:
            print("\nShutting down...")
        
        finally:
            # Flush metrics one last time
            self.flush_metrics()
            
            # Close socket
            if self.sock:
                self.sock.close()
                self.sock = None
            
            # Print summary
            print(f"Processed {self.metrics_received} metrics")
    
    def process_packet(self, data: bytes, addr: Tuple[str, int]) -> None:
        """
        Process a StatsD packet.
        
        Args:
            data: The packet data
            addr: The sender address
        """
        # Decode data
        try:
            lines = data.decode("utf-8").splitlines()
            
            for line in lines:
                # Skip empty lines
                if not line:
                    continue
                
                # Parse metric
                self.parse_metric(line)
            
        except Exception as e:
            print(f"Error processing packet: {e}")
    
    def parse_metric(self, line: str) -> None:
        """
        Parse a StatsD metric line.
        
        Args:
            line: The metric line
        """
        # Split line into parts
        parts = line.split(":")
        
        if len(parts) < 2:
            if self.verbose:
                print(f"Invalid metric format: {line}")
            return
        
        # Extract name and rest
        name = parts[0]
        rest = parts[1]
        
        # Split rest into value and metadata
        value_parts = rest.split("|")
        
        if len(value_parts) < 2:
            if self.verbose:
                print(f"Invalid metric value format: {rest}")
            return
        
        # Extract value and type
        try:
            value_str = value_parts[0]
            value = float(value_str)
            metric_type = value_parts[1]
        except ValueError:
            if self.verbose:
                print(f"Invalid metric value: {value_parts[0]}")
            return
        
        # Extract sample rate and tags
        sample_rate = 1.0
        tags = {}
        
        for part in value_parts[2:]:
            if part.startswith("@"):
                # Sample rate
                try:
                    sample_rate = float(part[1:])
                except ValueError:
                    pass
            
            elif part.startswith("#"):
                # Tags
                tag_parts = part[1:].split(",")
                
                for tag_part in tag_parts:
                    tag_kv = tag_part.split(":")
                    
                    if len(tag_kv) == 2:
                        tags[tag_kv[0]] = tag_kv[1]
        
        # Store tags for this metric
        self.metric_tags[name] = tags
        
        # Process metric based on type
        if metric_type == "c":
            # Counter
            adjusted_value = value / sample_rate
            self.counters[name] = self.counters.get(name, 0) + adjusted_value
            
            if self.verbose:
                self._print_metric("counter", name, adjusted_value, tags)
            
        elif metric_type == "g":
            # Gauge
            self.gauges[name] = value
            
            if self.verbose:
                self._print_metric("gauge", name, value, tags)
            
        elif metric_type == "ms":
            # Timer
            if name not in self.timers:
                self.timers[name] = []
            
            self.timers[name].append(value)
            
            if self.verbose:
                self._print_metric("timer", name, value, tags)
            
        elif metric_type == "h":
            # Histogram
            if name not in self.histograms:
                self.histograms[name] = []
            
            self.histograms[name].append(value)
            
            if self.verbose:
                self._print_metric("histogram", name, value, tags)
            
        else:
            # Unknown type
            if self.verbose:
                print(f"Unknown metric type: {metric_type}")
            return
        
        # Increment metrics received counter
        self.metrics_received += 1
        
        # Log to file if specified
        if self.output_file:
            with open(self.output_file, "a") as f:
                timestamp = datetime.now().isoformat()
                tags_str = json.dumps(tags) if tags else "{}"
                f.write(f"[{timestamp}] [{metric_type}] [{name}] [{value}] [{tags_str}]\n")
    
    def flush_metrics(self) -> None:
        """Flush metrics to output."""
        # Skip if no metrics
        if self.metrics_received == 0:
            return
        
        # Print metrics
        self._print_metrics()
        
        # Reset counters (but keep gauges)
        self.counters = {}
        self.timers = {}
        self.histograms = {}
        
        # Reset metrics received counter
        self.metrics_received = 0
    
    def _print_metrics(self) -> None:
        """Print metrics to console."""
        # Get current time
        now = datetime.now().isoformat()
        
        # Print header
        print(f"\n--- Metrics flush at {now} ---")
        
        # Print counters
        if self.counters:
            print("\nCounters:")
            for name, value in sorted(self.counters.items()):
                tags = self.metric_tags.get(name, {})
                self._print_metric("counter", name, value, tags)
        
        # Print gauges
        if self.gauges:
            print("\nGauges:")
            for name, value in sorted(self.gauges.items()):
                tags = self.metric_tags.get(name, {})
                self._print_metric("gauge", name, value, tags)
        
        # Print timers
        if self.timers:
            print("\nTimers:")
            for name, values in sorted(self.timers.items()):
                if not values:
                    continue
                
                tags = self.metric_tags.get(name, {})
                avg = sum(values) / len(values)
                min_val = min(values)
                max_val = max(values)
                
                if self.pretty_print:
                    print(f"  {name} (count={len(values)}, min={min_val:.2f}ms, avg={avg:.2f}ms, max={max_val:.2f}ms) {tags}")
                else:
                    print(f"  {name} = {values} {tags}")
        
        # Print histograms
        if self.histograms:
            print("\nHistograms:")
            for name, values in sorted(self.histograms.items()):
                if not values:
                    continue
                
                tags = self.metric_tags.get(name, {})
                avg = sum(values) / len(values)
                min_val = min(values)
                max_val = max(values)
                
                if self.pretty_print:
                    print(f"  {name} (count={len(values)}, min={min_val:.2f}, avg={avg:.2f}, max={max_val:.2f}) {tags}")
                else:
                    print(f"  {name} = {values} {tags}")
        
        # Print footer
        print(f"\n--- End metrics ({self.metrics_received} received) ---\n")
    
    def _print_metric(
        self,
        metric_type: str,
        name: str,
        value: Union[int, float, List[float]],
        tags: Dict[str, str]
    ) -> None:
        """
        Print a single metric.
        
        Args:
            metric_type: The metric type
            name: The metric name
            value: The metric value
            tags: The metric tags
        """
        if self.pretty_print:
            # Format value based on type
            if isinstance(value, (int, float)):
                if metric_type == "timer":
                    value_str = f"{value:.2f}ms"
                else:
                    value_str = f"{value:.2f}" if isinstance(value, float) else str(value)
            else:
                value_str = str(value)
            
            # Format tags
            if tags:
                tags_str = ", ".join(f"{k}={v}" for k, v in tags.items())
                tags_str = f" [{tags_str}]"
            else:
                tags_str = ""
            
            print(f"  {name} = {value_str}{tags_str}")
        else:
            print(f"  {metric_type} {name} = {value} {tags}")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Simple StatsD server for development and testing")
    
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to listen on (default: 127.0.0.1)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8125,
        help="Port to listen on (default: 8125)"
    )
    
    parser.add_argument(
        "--output-file",
        type=str,
        help="File to save metrics to (optional)"
    )
    
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Display raw metric values instead of pretty-printing"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print verbose output"
    )
    
    return parser.parse_args()


def main() -> None:
    """Main function."""
    # Parse arguments
    args = parse_args()
    
    # Create server
    server = SimpleStatsDServer(
        host=args.host,
        port=args.port,
        output_file=args.output_file,
        pretty_print=not args.raw,
        verbose=args.verbose
    )
    
    # Start server
    server.start()


if __name__ == "__main__":
    main()