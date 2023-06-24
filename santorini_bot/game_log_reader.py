"""Module for reading game state from logs"""
import logging
from os import PathLike
from typing import TextIO

from santorini_bot import GAME_LOG_DELIMITER
from santorini_bot.game import GameManager
from santorini_bot.board import Color, TurnActions, Board

logger = logging.getLogger(__name__)


def load_game_log(
    path: str | bytes | PathLike[str] | PathLike[bytes] | int,
) -> GameManager:
    """
    Load game log from `path` on disk into `game_manager`.

    :param path: log file path
    :return: game manager with loaded game state
    """
    with open(path, "r", encoding="utf-8") as file:
        # load board and first player from log
        first_line = file.readline()
        board = _load_board_from_log(log_line=first_line)

        second_line = file.readline()
        player_order = _load_player_order_from_log(log_line=second_line)

        game_manager = GameManager(player_order=player_order, board=board)

        # Load game state by executing turns
        game_manager = _load_game_state_from_log(file=file, game_manager=game_manager)

    return game_manager


def _load_board_from_log(log_line: str) -> Board:
    """
    Load board parameters from log line

    :param log_line: string line from a log file
    :return: board
    """
    logger.debug(f'_load_board_from_log log_line: "{log_line}"')
    log_line = log_line.rstrip()
    board_parameter_strs = log_line.split(GAME_LOG_DELIMITER)
    board_parameters = [int(p) for p in board_parameter_strs]

    board = Board(
        length=board_parameters[0],
        width=board_parameters[1],
        max_height=board_parameters[2],
        max_workers_per_player=board_parameters[3],
    )
    return board


def _load_player_order_from_log(log_line: str) -> list[Color]:
    """
    Load player order from a log file line.

    :param log_line: string line from a log file
    :return: player (color) turn order
    """
    logger.debug(f'_load_player_order_from_log log_line: "{log_line}"')
    log_line = log_line.rstrip()
    player_color_strs = log_line.split(GAME_LOG_DELIMITER)
    turn_order = [Color(c) for c in player_color_strs]
    return turn_order


def _load_game_state_from_log(file: TextIO, game_manager: GameManager) -> GameManager:
    """
    Load place worker, move, and build turn game states into game manager.

    :param file: File buffer to read from
    :param game_manager: game manager to update game state in
    :return: game manager with updated game state
    """
    for line in file:
        line = line.rstrip()
        logger.debug(f'_load_game_state_from_log line: "{line}"')
        split_line = line.split(GAME_LOG_DELIMITER)
        active_player = Color(split_line[0])
        turn_action = TurnActions(split_line[1])
        turn_coordinates = [int(c) for c in split_line[2:]]

        game_manager.update_game_state(
            active_player=active_player,
            turn_action=turn_action,
            turn_coordinates=turn_coordinates,
        )

    return game_manager
