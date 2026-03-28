"""Functions for extracting an event name from a transition's name and label."""

import dataclasses
from typing import Callable, Final

type Extractor = Callable[[str, str | None], str]


@dataclasses.dataclass(frozen=True, repr=False)
class ExtractorFactory:
    extractor: Extractor

    def __call__(self, name: str, label: str | None) -> str:
        return self.extractor(name, label)


AlwaysName: Final[Extractor] = ExtractorFactory(lambda name, _: name)
LabelIfPresentElseName: Final[Extractor] = ExtractorFactory(lambda name, label: label or name)
