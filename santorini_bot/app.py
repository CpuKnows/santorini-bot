"""Interface for loading, saving, and running a game"""
from os import PathLike
from typing import Optional

from santorini_bot.game import GameManager
from santorini_bot.game_log_reader import load_game_log
from santorini_bot.game_log_writer import save_game_log


class App:
    """Class for loading, saving, and running a game"""

    def __init__(
        self,
        game_manager: Optional[GameManager] = None,
    ):
        self.game_manager = game_manager or GameManager()

    def load_game(self, path: str | bytes | PathLike[str] | PathLike[bytes] | int):
        """
        Load game log from `path`.

        :param path: log file path
        :return: None
        """
        self.game_manager = load_game_log(path=path)

    def save_game(self, path: str | bytes | PathLike[str] | PathLike[bytes] | int):
        """
        Save game log to `path`.

        :param path: log file path
        :return: None
        """
        save_game_log(path=path, game_manager=self.game_manager)

    def start_game(self):
        """Start interactive game loop"""
        self.game_manager.game_loop()
