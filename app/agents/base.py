from abc import ABC
from abc import abstractmethod

from app.state import WorkflowState


class BaseAgent(ABC):

    def __init__(self, llm):

        self.llm = llm

    @abstractmethod
    def execute(
        self,
        state: WorkflowState
    ) -> WorkflowState:
        pass