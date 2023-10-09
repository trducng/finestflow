import pytest

from theflow import Compose


class FlowA(Compose):
    x: int
    node_a: Compose

    def run(self):
        return self.x + self.node_a()


class FlowB(Compose):
    x: int
    node_b: Compose

    def run(self):
        return self.x + self.node_b()


class TestCircularFlow:
    def test_recursion_error_while_execute(self):
        """Add extra data to the param"""
        flow_a = FlowA(x=1)
        flow_b = FlowB(x=2, node_b=flow_a)
        flow_b.node_b.node_a = flow_b
        with pytest.raises(RecursionError):
            flow_a()

    def test_rescursion_error_while_dump(self):
        flow_a = FlowA(x=1)
        flow_b = FlowB(x=2, node_b=flow_a)
        flow_b.node_b.node_a = flow_b
        with pytest.raises(RecursionError):
            print(flow_a.dump())
