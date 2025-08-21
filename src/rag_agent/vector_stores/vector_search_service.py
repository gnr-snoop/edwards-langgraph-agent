from abc import ABC, abstractmethod


class VectorSearch(ABC):
    
    @abstractmethod
    def __init__(self, config):
        pass

    @abstractmethod
    async def retrieve(self, question):
        pass