from abc import ABCMeta, abstractmethod
from cmath import rect
from dataclasses import dataclass


class Meta(metaclass=ABCMeta):
    def __init__(self):
        print("1")

    @abstractmethod
    def a(self):
        pass

    @classmethod
    def __subclasshook__(cls, subclass):
        return NotImplemented


@dataclass
class A(Meta):
    v: int

    def a(self):
        pass


a = A(1)
print(isinstance(a, Meta))
