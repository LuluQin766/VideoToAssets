from __future__ import annotations

from abc import ABC, abstractmethod

from video_to_assets.canonical.canonical_content import CanonicalContent
from video_to_assets.models.source_input import SourceInput


class BaseAdapter(ABC):
    @abstractmethod
    def to_canonical(self, source: SourceInput) -> CanonicalContent:
        raise NotImplementedError
