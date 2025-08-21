from dataclasses import dataclass

@dataclass
class Document:
    def __init__(self, content, filename, source): 
        self.content = content
        self.filename = filename
        self.source = source