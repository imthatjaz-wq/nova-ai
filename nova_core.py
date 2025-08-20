"""
Nova Core: main orchestrator wiring (to be expanded in later segments).
For Segment 1, this file only ensures import paths and minimal bootstrap.
"""
from nova.config import Settings
from nova.logging_setup import setup_logging
from conversation.dialogue_manager import DialogueManager


def bootstrap() -> None:
    """Initialize configuration and logging; placeholder for future wiring."""
    settings = Settings()  # loads env/defaults
    logger = setup_logging(settings)
    logger.info("Nova bootstrap complete. Environment=%s", settings.env)


def run_turn(text: str) -> str:
    """Process a single input turn and return Nova's response."""
    dm = DialogueManager()
    return dm.handle(text)


if __name__ == "__main__":
    bootstrap()
