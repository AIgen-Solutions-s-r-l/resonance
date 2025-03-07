"""
System metrics collection.

This module provides functions for collecting and reporting system-level
metrics such as CPU, memory, and disk usage.
"""

import os
import platform
import time
import importlib.util
from typing import Dict, Optional

# Check if psutil is available
PSUTIL_AVAILABLE = importlib.util.find_spec("psutil") is not None

# Only import if available
if PSUTIL_AVAILABLE:
    import psutil
else:
    # Create dummy psutil functionality
    class DummyPsutil:
        @staticmethod
        def cpu_percent(*args, **kwargs):
            return 0.0
            
        @staticmethod
        def cpu_count(*args, **kwargs):
            return 1
            
        @staticmethod
        def virtual_memory():
            class DummyVirtualMemory:
                total = 0
                available = 0
                used = 0
                free = 0
                percent = 0.0
            return DummyVirtualMemory()
            
        @staticmethod
        def swap_memory():
            class DummySwapMemory:
                total = 0
                used = 0
                free = 0
                percent = 0.0
            return DummySwapMemory()
            
        @staticmethod
        def disk_usage(path):
            class DummyDiskUsage:
                total = 0
                used = 0
                free = 0
                percent = 0.0
            return DummyDiskUsage()
            
        @staticmethod
        def disk_io_counters(*args, **kwargs):
            class DummyDiskIO:
                read_count = 0
                write_count = 0
                read_bytes = 0
                write_bytes = 0
                read_time = 0
                write_time = 0
            return DummyDiskIO()
            
        @staticmethod
        def disk_partitions(*args, **kwargs):
            return []
            
        @staticmethod
        def Process(*args, **kwargs):
            class DummyProcess:
                @staticmethod
                def cpu_percent(*args, **kwargs):
                    return 0.0
                
                @staticmethod
                def memory_info():
                    class DummyMemoryInfo:
                        rss = 0
                        vms = 0
                    return DummyMemoryInfo()
                
                @staticmethod
                def memory_percent():
                    return 0.0
                
                @staticmethod
                def num_threads():
                    return 1
                
                @staticmethod
                def open_files():
                    return []
                
                @staticmethod
                def connections():
                    return []
            return DummyProcess()
            
        @staticmethod
        def net_io_counters(*args, **kwargs):
            class DummyNetIO:
                bytes_sent = 0
                bytes_recv = 0
                packets_sent = 0
                packets_recv = 0
                errin = 0
                errout = 0
                dropin = 0
                dropout = 0
            return DummyNetIO()
            
        @staticmethod
        def net_connections(*args, **kwargs):
            return []
            
        # Define exception classes
        class AccessDenied(Exception):
            pass
            
        class ZombieProcess(Exception):
            pass
    
    # Create dummy psutil
    psutil = DummyPsutil()

from app.core.config import settings
from app.log.logging import logger
from app.metrics.core import report_gauge


def collect_system_metrics() -> bool:
    """
    Collect and report system metrics.
    
    Returns:
        True if metrics were collected successfully, False otherwise
    """
    if not settings.metrics_enabled or not settings.system_metrics_enabled:
        return False
    
    if not PSUTIL_AVAILABLE:
        logger.warning(
            "psutil library not installed. System metrics collection will be limited.",
            hint="Install with 'pip install psutil'"
        )
        return False
    
    try:
        # Collect CPU metrics
        collect_cpu_metrics()
        
        # Collect memory metrics
        collect_memory_metrics()
        
        # Collect disk metrics
        collect_disk_metrics()
        
        # Collect process metrics
        collect_process_metrics()
        
        # Collect network metrics
        collect_network_metrics()
        
        return True
        
    except Exception as e:
        logger.error(
            "Error collecting system metrics",
            error=str(e)
        )
        return False


def collect_cpu_metrics() -> None:
    """Collect and report CPU metrics."""
    try:
        # CPU usage percentage (across all CPUs)
        cpu_percent = psutil.cpu_percent(interval=0.1)
        report_gauge("system.cpu.percent", cpu_percent)
        
        # Per-CPU usage
        per_cpu_percent = psutil.cpu_percent(interval=0.1, percpu=True)
        for i, cpu_usage in enumerate(per_cpu_percent):
            report_gauge("system.cpu.core.percent", cpu_usage, {"core": str(i)})
        
        # CPU count
        cpu_count = psutil.cpu_count()
        report_gauge("system.cpu.count", cpu_count)
        
        # CPU frequency
        if hasattr(psutil, "cpu_freq"):
            cpu_freq = psutil.cpu_freq()
            if cpu_freq:
                report_gauge("system.cpu.frequency.current", cpu_freq.current)
                if hasattr(cpu_freq, "min") and cpu_freq.min:
                    report_gauge("system.cpu.frequency.min", cpu_freq.min)
                if hasattr(cpu_freq, "max") and cpu_freq.max:
                    report_gauge("system.cpu.frequency.max", cpu_freq.max)
        
        # CPU load average (1, 5, 15 minutes)
        if hasattr(os, "getloadavg") and callable(os.getloadavg):
            load1, load5, load15 = os.getloadavg()
            report_gauge("system.load.1", load1)
            report_gauge("system.load.5", load5)
            report_gauge("system.load.15", load15)
        
    except Exception as e:
        logger.error(
            "Error collecting CPU metrics",
            error=str(e)
        )


def collect_memory_metrics() -> None:
    """Collect and report memory metrics."""
    try:
        # Virtual memory
        virtual_memory = psutil.virtual_memory()
        report_gauge("system.memory.total", virtual_memory.total)
        report_gauge("system.memory.available", virtual_memory.available)
        report_gauge("system.memory.used", virtual_memory.used)
        report_gauge("system.memory.free", virtual_memory.free)
        report_gauge("system.memory.percent", virtual_memory.percent)
        
        # Get detailed memory information if available
        if hasattr(virtual_memory, "active"):
            report_gauge("system.memory.active", virtual_memory.active)
        if hasattr(virtual_memory, "inactive"):
            report_gauge("system.memory.inactive", virtual_memory.inactive)
        if hasattr(virtual_memory, "buffers"):
            report_gauge("system.memory.buffers", virtual_memory.buffers)
        if hasattr(virtual_memory, "cached"):
            report_gauge("system.memory.cached", virtual_memory.cached)
        
        # Swap memory
        swap_memory = psutil.swap_memory()
        report_gauge("system.swap.total", swap_memory.total)
        report_gauge("system.swap.used", swap_memory.used)
        report_gauge("system.swap.free", swap_memory.free)
        report_gauge("system.swap.percent", swap_memory.percent)
        
    except Exception as e:
        logger.error(
            "Error collecting memory metrics",
            error=str(e)
        )


def collect_disk_metrics() -> None:
    """Collect and report disk metrics."""
    try:
        # Disk usage for root partition
        disk_usage = psutil.disk_usage("/")
        report_gauge("system.disk.total", disk_usage.total)
        report_gauge("system.disk.used", disk_usage.used)
        report_gauge("system.disk.free", disk_usage.free)
        report_gauge("system.disk.percent", disk_usage.percent)
        
        # Disk I/O counters
        disk_io = psutil.disk_io_counters()
        if disk_io:
            report_gauge("system.disk.read_count", disk_io.read_count)
            report_gauge("system.disk.write_count", disk_io.write_count)
            report_gauge("system.disk.read_bytes", disk_io.read_bytes)
            report_gauge("system.disk.write_bytes", disk_io.write_bytes)
            
            if hasattr(disk_io, "read_time"):
                report_gauge("system.disk.read_time", disk_io.read_time)
            if hasattr(disk_io, "write_time"):
                report_gauge("system.disk.write_time", disk_io.write_time)
        
        # Per-disk usage
        for partition in psutil.disk_partitions():
            if not partition.mountpoint:
                continue
                
            try:
                partition_usage = psutil.disk_usage(partition.mountpoint)
                tags = {"mountpoint": partition.mountpoint, "device": partition.device}
                
                report_gauge("system.disk.partition.total", partition_usage.total, tags)
                report_gauge("system.disk.partition.used", partition_usage.used, tags)
                report_gauge("system.disk.partition.free", partition_usage.free, tags)
                report_gauge("system.disk.partition.percent", partition_usage.percent, tags)
            except (PermissionError, OSError):
                # Skip if we don't have access
                pass
        
    except Exception as e:
        logger.error(
            "Error collecting disk metrics",
            error=str(e)
        )


def collect_process_metrics() -> None:
    """Collect and report process metrics."""
    try:
        # Current process
        process = psutil.Process()
        
        # Process CPU
        process_cpu_percent = process.cpu_percent(interval=0.1)
        report_gauge("system.process.cpu.percent", process_cpu_percent)
        
        # Process memory
        process_memory = process.memory_info()
        report_gauge("system.process.memory.rss", process_memory.rss)
        report_gauge("system.process.memory.vms", process_memory.vms)
        
        if hasattr(process_memory, "shared"):
            report_gauge("system.process.memory.shared", process_memory.shared)
        if hasattr(process_memory, "text"):
            report_gauge("system.process.memory.text", process_memory.text)
        if hasattr(process_memory, "data"):
            report_gauge("system.process.memory.data", process_memory.data)
        
        # Process memory percent
        process_memory_percent = process.memory_percent()
        report_gauge("system.process.memory.percent", process_memory_percent)
        
        # Process threads
        process_threads = process.num_threads()
        report_gauge("system.process.threads", process_threads)
        
        # Process open files
        try:
            process_open_files = len(process.open_files())
            report_gauge("system.process.open_files", process_open_files)
        except (psutil.AccessDenied, psutil.ZombieProcess):
            pass
            
        # Process connections
        try:
            process_connections = len(process.connections())
            report_gauge("system.process.connections", process_connections)
        except (psutil.AccessDenied, psutil.ZombieProcess):
            pass
        
    except Exception as e:
        logger.error(
            "Error collecting process metrics",
            error=str(e)
        )


def collect_network_metrics() -> None:
    """Collect and report network metrics."""
    try:
        # Network I/O counters
        net_io = psutil.net_io_counters()
        report_gauge("system.net.bytes_sent", net_io.bytes_sent)
        report_gauge("system.net.bytes_recv", net_io.bytes_recv)
        report_gauge("system.net.packets_sent", net_io.packets_sent)
        report_gauge("system.net.packets_recv", net_io.packets_recv)
        report_gauge("system.net.errin", net_io.errin)
        report_gauge("system.net.errout", net_io.errout)
        report_gauge("system.net.dropin", net_io.dropin)
        report_gauge("system.net.dropout", net_io.dropout)
        
        # Per-interface network I/O
        net_io_per_nic = psutil.net_io_counters(pernic=True)
        for interface, counters in net_io_per_nic.items():
            tags = {"interface": interface}
            
            report_gauge("system.net.interface.bytes_sent", counters.bytes_sent, tags)
            report_gauge("system.net.interface.bytes_recv", counters.bytes_recv, tags)
            report_gauge("system.net.interface.packets_sent", counters.packets_sent, tags)
            report_gauge("system.net.interface.packets_recv", counters.packets_recv, tags)
            report_gauge("system.net.interface.errin", counters.errin, tags)
            report_gauge("system.net.interface.errout", counters.errout, tags)
            report_gauge("system.net.interface.dropin", counters.dropin, tags)
            report_gauge("system.net.interface.dropout", counters.dropout, tags)
        
        # Network connections
        conn_counts = {
            "ESTABLISHED": 0,
            "LISTEN": 0,
            "CLOSE_WAIT": 0,
            "TIME_WAIT": 0,
            "CLOSED": 0,
            "SYN_SENT": 0,
            "SYN_RECV": 0,
            "FIN_WAIT1": 0,
            "FIN_WAIT2": 0,
            "LAST_ACK": 0,
            "CLOSING": 0,
            "NONE": 0
        }
        
        for conn in psutil.net_connections():
            status = conn.status
            conn_counts[status] = conn_counts.get(status, 0) + 1
        
        for status, count in conn_counts.items():
            report_gauge("system.net.connections", count, {"status": status})
        
    except Exception as e:
        logger.error(
            "Error collecting network metrics",
            error=str(e)
        )


def get_system_info() -> Dict[str, str]:
    """
    Get system information.
    
    Returns:
        Dictionary containing system information
    """
    try:
        info = {
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "python_version": platform.python_version(),
            "processor": platform.processor(),
            "architecture": platform.architecture()[0],
            "hostname": platform.node()
        }
        
        # Add CPU info
        cpu_info = {}
        try:
            cpu_count_physical = psutil.cpu_count(logical=False)
            cpu_count_logical = psutil.cpu_count()
            cpu_info["physical_cores"] = str(cpu_count_physical)
            cpu_info["logical_cores"] = str(cpu_count_logical)
        except Exception:
            pass
            
        for key, value in cpu_info.items():
            info[f"cpu_{key}"] = value
        
        return info
        
    except Exception as e:
        logger.error(
            "Error getting system information",
            error=str(e)
        )
        return {"error": str(e)}


def report_system_info() -> None:
    """Report system information as metrics tags."""
    if not settings.metrics_enabled or not settings.system_metrics_enabled:
        return
    
    try:
        system_info = get_system_info()
        report_gauge("system.info", 1, system_info)
        
    except Exception as e:
        logger.error(
            "Error reporting system information",
            error=str(e)
        )