from abc import ABC
from abc import abstractmethod


class BaseLLM(ABC):

    @abstractmethod
    def invoke(self, prompt: str):
        pass