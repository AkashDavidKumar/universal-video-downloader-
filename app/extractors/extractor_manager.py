import importlib
import inspect
import os
import sys
from pathlib import Path
from typing import List, Type, Optional
from loguru import logger
from .base_extractor import BaseExtractor

class ExtractorManager:
    """Manages discovery, dynamic loading, and matching of video extractor plugins."""

    def __init__(self, plugins_dir: Optional[Path] = None):
        self.extractors: List[Type[BaseExtractor]] = []
        self.plugins_dir = plugins_dir or Path(__file__).parent.parent / "plugins"
        self.builtins_dir = Path(__file__).parent
        
        # Ensure directories exist
        self.plugins_dir.mkdir(parents=True, exist_ok=True)

    def load_all(self) -> None:
        """Loads both built-in extractors and external plugins."""
        self.extractors.clear()
        
        # 1. Load built-ins (under app/extractors)
        self._load_from_directory(self.builtins_dir, package_prefix="app.extractors")
        
        # 2. Load external plugins (under app/plugins)
        self._load_from_directory(self.plugins_dir, package_prefix="app.plugins")
        
        logger.info(f"Loaded {len(self.extractors)} extractors.")

    def _load_from_directory(self, directory: Path, package_prefix: str) -> None:
        """Dynamically scans a directory for Python files and registers extractor classes."""
        logger.debug(f"Scanning directory for extractors: {directory}")
        
        # Add folder to sys.path so we can import modules
        if str(directory) not in sys.path:
            sys.path.insert(0, str(directory))

        for file in directory.glob("*.py"):
            if file.name in ("__init__.py", "base_extractor.py", "extractor_manager.py"):
                continue

            module_name = file.stem
            try:
                # Attempt to import module
                # Try import via full package path first, fall back to file stem
                try:
                    module = importlib.import_module(f"{package_prefix}.{module_name}")
                except ModuleNotFoundError:
                    module = importlib.import_module(module_name)
                
                # Scan module for subclasses of BaseExtractor
                for name, obj in inspect.getmembers(module):
                    if (
                        inspect.isclass(obj)
                        and issubclass(obj, BaseExtractor)
                        and obj is not BaseExtractor
                        and not inspect.isabstract(obj)
                    ):
                        # Avoid duplicates
                        if obj not in self.extractors:
                            self.extractors.append(obj)
                            logger.info(f"Successfully registered extractor: {obj.__name__} from {file.name}")
            except Exception as e:
                logger.error(f"Failed to load extractor module {file.name}: {e}")

    def get_extractor_for_url(self, url: str) -> BaseExtractor:
        """Finds a matching extractor instance for the given URL.
        
        Falls back to a GenericExtractor if no specific extractor matches.
        
        Raises:
            ValueError: If no suitable extractor matches and fallback is unavailable.
        """
        fallback_extractor_cls: Optional[Type[BaseExtractor]] = None

        for extractor_cls in self.extractors:
            # We want to check GenericExtractor last to let specialized extractors win
            if extractor_cls.__name__ == "GenericExtractor":
                fallback_extractor_cls = extractor_cls
                continue
                
            try:
                # Instantiate and validate
                extractor = extractor_cls()
                if extractor.validate_url(url):
                    logger.debug(f"Matched URL with specialized extractor: {extractor_cls.__name__}")
                    return extractor
            except Exception as e:
                logger.warning(f"Error validating URL with {extractor_cls.__name__}: {e}")

        # Fallback to GenericExtractor if registered
        if fallback_extractor_cls:
            logger.debug(f"Using fallback extractor: {fallback_extractor_cls.__name__}")
            return fallback_extractor_cls()

        raise ValueError(f"No extractor found that can handle URL: {url}")
