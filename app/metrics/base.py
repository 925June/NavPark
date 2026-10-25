import time
from typing import Dict
from typing import List
from typing import Optional
from collections import defaultdict
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime


@dataclass
class MetricEvent:
    """A single metric event."""
    timestamp: float
    event_type: str
    agent: Optional[str] = None
    session_id: Optional[str] = None
    duration: Optional[float] = None
    success: bool = True
    metadata: Dict = field(default_factory=dict)


class MetricsCollector:
    """Collects and aggregates metrics for monitoring."""

    def __init__(self):
        self.events: List[MetricEvent] = []
        self.counters: Dict[str, int] = defaultdict(int)
        self.timers: Dict[str, List[float]] = defaultdict(list)
        self.agent_usage: Dict[str, int] = defaultdict(int)
        self.guardrail_failures: Dict[str, int] = defaultdict(int)
        self.error_count: int = 0
        self.request_count: int = 0

    def record_event(self, event: MetricEvent):
        """Record a metric event."""
        self.events.append(event)
        
        # Update counters
        self.counters[event.event_type] += 1
        
        # Update agent usage
        if event.agent:
            self.agent_usage[event.agent] += 1
        
        # Update error count
        if not event.success:
            self.error_count += 1
        
        # Update request count
        if event.event_type == "request":
            self.request_count += 1
        
        # Update timers
        if event.duration is not None:
            self.timers[event.event_type].append(event.duration)

    def record_guardrail_failure(self, guardrail_name: str):
        """Record a guardrail failure."""
        self.guardrail_failures[guardrail_name] += 1

    def get_summary(self) -> Dict:
        """Get a summary of collected metrics."""
        total_requests = self.counters.get("request", 0)
        
        # Calculate average response times
        avg_times = {}
        for event_type, times in self.timers.items():
            if times:
                avg_times[event_type] = sum(times) / len(times)

        # Calculate guardrail pass rate
        total_guardrail_checks = self.counters.get("guardrail_check", 0)
        total_guardrail_failures = sum(self.guardrail_failures.values())
        guardrail_pass_rate = (
            (total_guardrail_checks - total_guardrail_failures) / total_guardrail_checks
            if total_guardrail_checks > 0 else 1.0
        )

        return {
            "total_requests": total_requests,
            "total_errors": self.error_count,
            "error_rate": self.error_count / total_requests if total_requests > 0 else 0.0,
            "agent_usage": dict(self.agent_usage),
            "guardrail_failures": dict(self.guardrail_failures),
            "guardrail_pass_rate": guardrail_pass_rate,
            "average_response_times": avg_times,
            "total_events": len(self.events)
        }

    def get_agent_routing_stats(self) -> Dict:
        """Get statistics about agent routing."""
        total = sum(self.agent_usage.values())
        if total == 0:
            return {}
        
        return {
            agent: {
                "count": count,
                "percentage": count / total
            }
            for agent, count in self.agent_usage.items()
        }

    def reset(self):
        """Reset all metrics."""
        self.events.clear()
        self.counters.clear()
        self.timers.clear()
        self.agent_usage.clear()
        self.guardrail_failures.clear()
        self.error_count = 0
        self.request_count = 0

    def print_summary(self):
        """Print a human-readable summary of metrics."""
        summary = self.get_summary()
        
        print("\n" + "="*60)
        print("METRICS SUMMARY")
        print("="*60)
        print(f"Total Requests: {summary['total_requests']}")
        print(f"Total Errors: {summary['total_errors']}")
        print(f"Error Rate: {summary['error_rate']:.2%}")
        print(f"Guardrail Pass Rate: {summary['guardrail_pass_rate']:.2%}")
        
        print("\nAgent Usage:")
        for agent, stats in self.get_agent_routing_stats().items():
            print(f"  {agent}: {stats['count']} ({stats['percentage']:.1%})")
        
        if summary['guardrail_failures']:
            print("\nGuardrail Failures:")
            for guardrail, count in summary['guardrail_failures'].items():
                print(f"  {guardrail}: {count}")
        
        if summary['average_response_times']:
            print("\nAverage Response Times:")
            for event_type, avg_time in summary['average_response_times'].items():
                print(f"  {event_type}: {avg_time:.3f}s")
        
        print("="*60)


# Global metrics collector instance
metrics_collector = MetricsCollector()
