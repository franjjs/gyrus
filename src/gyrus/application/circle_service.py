import logging


class CircleService:
    """Centralized circle/context management for the application."""

    def __init__(self, initial_circle: str = "local"):
        self._current_circle = initial_circle
        logging.info(f"CircleService initialized with circle: {initial_circle}")

    @property
    def current_circle(self) -> str:
        """Get the currently active circle."""
        return self._current_circle

    def set_circle(self, circle_id: str) -> None:
        """Set the active circle."""
        if circle_id != self._current_circle:
            logging.info(f"🔄 Circle changed: {self._current_circle} → {circle_id}")
            self._current_circle = circle_id
        else:
            logging.debug(f"Circle already set to {circle_id}")

    def get_circle(self) -> str:
        """Get the current circle ID."""
        return self._current_circle
