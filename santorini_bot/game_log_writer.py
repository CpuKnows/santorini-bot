"""Module for writing game state to logs"""
import logging
from os import PathLike

from santorini_bot import GAME_LOG_DELIMITER
from santorini_bot.game import GameManager
from santorini_bot.board import BuildTurn, MoveTurn, PlaceWorkerTurn, TurnArgs

logger = logging.getLogger(__name__)


def save_game_log(
    path: str | bytes | PathLike[str] | PathLike[bytes] | int, game_manager: GameManager
):
    """
    Save game log from `game_manager` to `path` on disk.

    :param path: log file path
    :param game_manager: game manager with game state logs
    :return: None
    """
    with open(path, "w", encoding="utf-8") as file:
        # write board parameters
        file.write(game_manager.initial_board.game_log_representation + "\n")

        # write player order
        player_order_str = GAME_LOG_DELIMITER.join(
            c.value for c in game_manager.initial_player_order
        )
        file.write(player_order_str + "\n")

        # write turns from game state log
        for turn in game_manager.game_state_log:
            # write turn
            turn_coordinate_str = GAME_LOG_DELIMITER.join(
                _turn_args_to_log_format(turn.turn)
            )
            turn_str = GAME_LOG_DELIMITER.join(
                [
                    turn.active_player.value,
                    turn.turn_action.value,
                    turn_coordinate_str,
                ]
            )
            file.write(turn_str + "\n")


def _turn_args_to_log_format(turn_args: TurnArgs) -> list[str]:
    """
    Convert place worker, move, or build turn arguments into string representations

    :param turn_args: place worker, move, or build turn arguments
    :return: None
    """
    if isinstance(turn_args, PlaceWorkerTurn):
        log_format_args = [
            str(turn_args.x),
            str(turn_args.y),
        ]
    elif isinstance(turn_args, MoveTurn):
        log_format_args = [
            str(turn_args.start_x),
            str(turn_args.start_y),
            str(turn_args.end_x),
            str(turn_args.end_y),
        ]
    elif isinstance(turn_args, BuildTurn):
        log_format_args = [
            str(turn_args.worker_x),
            str(turn_args.worker_y),
            str(turn_args.build_x),
            str(turn_args.build_y),
        ]
    else:
        raise ValueError(
            f'Unexpected turn_args of type "{type(turn_args)}". turn_args: '
            f'"{turn_args}"'
        )

    return log_format_args
