import pytest
from app.scheduler.event_queue import EventQueue, Event


class TestEventQueue:
    def test_push_and_pop_order(self):
        eq = EventQueue()

        eq.push(Event(time=10.0, event_type="A", target_agent_id="s1"))
        eq.push(Event(time=5.0, event_type="B", target_agent_id="s1"))
        eq.push(Event(time=15.0, event_type="C", target_agent_id="s1"))

        first = eq.pop()
        assert first.time == 5.0
        assert first.event_type == "B"

        second = eq.pop()
        assert second.time == 10.0
        assert second.event_type == "A"

        third = eq.pop()
        assert third.time == 15.0
        assert third.event_type == "C"

    def test_empty_queue(self):
        eq = EventQueue()
        assert eq.pop() is None
        assert eq.peek() is None
        assert eq.is_empty() is True

    def test_size(self):
        eq = EventQueue()
        assert eq.size() == 0

        eq.push(Event(time=1.0, event_type="A", target_agent_id="s1"))
        assert eq.size() == 1

        eq.push(Event(time=2.0, event_type="B", target_agent_id="s1"))
        assert eq.size() == 2

        eq.pop()
        assert eq.size() == 1

    def test_peek(self):
        eq = EventQueue()
        assert eq.peek() is None

        eq.push(Event(time=10.0, event_type="A", target_agent_id="s1"))
        eq.push(Event(time=5.0, event_type="B", target_agent_id="s1"))

        peeked = eq.peek()
        assert peeked.time == 5.0
        assert eq.size() == 2

    def test_to_list_and_from_list(self):
        eq = EventQueue()
        events = [
            Event(time=10.0, event_type="A", target_agent_id="s1", payload={"key": "value"}),
            Event(time=5.0, event_type="B", target_agent_id="s2"),
            Event(time=15.0, event_type="C", target_agent_id="s1"),
        ]
        for e in events:
            eq.push(e)

        data = eq.to_list()
        assert len(data) == 3

        eq2 = EventQueue.from_list(data)
        assert eq2.size() == 3

        popped = []
        while not eq2.is_empty():
            popped.append(eq2.pop())

        assert len(popped) == 3
        assert popped[0].time == 5.0
        assert popped[1].time == 10.0
        assert popped[2].time == 15.0
