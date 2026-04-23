from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from enum import Enum


class FileStatus(Enum):
    PENDING = "pending"
    CONVERTING = "converting"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class FileItem:
    file_path: str
    status: FileStatus = FileStatus.PENDING
    output_word: Optional[str] = None
    output_markdown: Optional[str] = None
    error_message: Optional[str] = None
    
    @property
    def file_name(self) -> str:
        return Path(self.file_path).name
    
    @property
    def file_dir(self) -> str:
        return str(Path(self.file_path).parent)
    
    @property
    def file_size(self) -> int:
        try:
            return Path(self.file_path).stat().st_size
        except:
            return 0
    
    def get_output_path(self, output_dir: Optional[str] = None, extension: str = ".docx") -> str:
        if output_dir:
            base_name = Path(self.file_path).stem
            return str(Path(output_dir) / f"{base_name}{extension}")
        else:
            return str(Path(self.file_path).with_suffix(extension))
