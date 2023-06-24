"""Module for tracking and managing game state"""
import logging
from dataclasses import dataclass
from enum import Enum
from itertools import product
from typing import Optional, Union

import numpy as np
import numpy.typing as npt

from santorini_bot import GAME_LOG_DELIMITER

logger = logging.getLogger(__name__)


class Color(Enum):
    """Enum for player colors and representations"""

    BLUE: str = "b"
    WHITE: str = "w"


class TurnActions(Enum):
    """Enum for possible turn actions and text representations"""

    PLACE_WORKER: str = "place_worker"
    MOVE: str = "move"
    BUILD: str = "build"


@dataclass
class PlaceWorkerTurn:
    """Dataclass for arguments for a place worker turn"""

    color: Color
    x: int
    y: int


@dataclass
class MoveTurn:
    """Dataclass for arguments for a move turn"""

    color: Color
    start_x: int
    start_y: int
    end_x: int
    end_y: int


@dataclass
class BuildTurn:
    """Dataclass for arguments for a build turn"""

    color: Color
    worker_x: int
    worker_y: int
    build_x: int
    build_y: int


TurnArgs = Union[PlaceWorkerTurn, MoveTurn, BuildTurn]


@dataclass(unsafe_hash=True)
class Worker:
    """Dataclass for Worker attributes"""

    x: int
    y: int
    height: int
    color: Color

    def move(self, x: int, y: int, height: Optional[int] = None) -> None:
        """
        Check if it's valid to move worker to coordinates (`x`, `y`).

        :param x: ending x-coordinate of worker
        :param y: ending y-coordinate of worker
        :param height: ending height of worker. If not provided the worker height
            remains the same.
        :return:
        """
        self.x = x
        self.y = y
        if height is not None:
            self.height = height


class Board:
    """Class representing Santorini board and actions on the board state"""

    def __init__(
        self,
        length: int = 5,
        width: int = 5,
        max_height: int = 4,
        max_workers_per_player: int = 2,
    ):
        """
        Create a new Santorini game board.

        :param length: Number of squares along the length (y-axis) of the board
        :param width: Number of squares along the width (x-axis) of the board
        :param max_height: Max height of a building
        :param max_workers_per_player: Max workers per player
        """
        self.length = length
        self.width = width
        self.max_height = max_height
        self.max_workers_per_player = max_workers_per_player
        self.workers: list[Worker] = []
        self.board_blocks: npt.NDArray[np.int_] = np.zeros(
            shape=(length, width), dtype=int
        )

        neighboring_shifts = list(product([0, -1, 1], repeat=2))
        # remove non-action (0, 0)
        self._neighboring_shifts = list(
            filter(lambda x: x != (0, 0), neighboring_shifts)
        )

        # Text justification should be one higher than board max height for optional
        # one character worker representation
        self._display_board_justification = self.max_height + 1

        self._game_log_representation = GAME_LOG_DELIMITER.join(
            str(s)
            for s in [
                self.length,
                self.width,
                self.max_height,
                self.max_workers_per_player,
            ]
        )

    def display_board(self) -> str:
        """
        :return: String representing the board as a grid with labels for levels and
            workers
        """
        board_repr = np.char.add(self._workers_board(), self.board_blocks.astype(str))

        repr_str = ""
        for row in board_repr.tolist():
            # justify board tile for optional worker char
            repr_str += " ".join(
                [str(i).rjust(self._display_board_justification) for i in row]
            )
            repr_str += "\n"
        return repr_str

    @property
    def game_log_representation(self):
        """String representation of Board init parameters for game log"""
        return self._game_log_representation

    def _workers_board(self) -> npt.NDArray[np.str_]:
        board_workers = np.full(
            shape=(self.length, self.width), fill_value=" ", dtype=str
        )
        for worker in self.workers:
            board_workers[worker.y][worker.x] = worker.color.value

        return board_workers

    def place_worker(self, color: Color, x: int, y: int) -> None:
        """
        Place worker of Color `color` at coordinates (`x`, `y`).

        :param color: color of new worker
        :param x: x-coordinate of new worker
        :param y: y-coordinate of new worker
        :return: None
        """
        if not self.player_can_place_workers(color=color):
            message = (
                f'Invalid worker placement: Too many for worker color "{color}". '
                f"Max workers is {self.max_workers_per_player}"
            )
            logger.info(message)
            raise IllegalMoveError(message)

        if not self._worker_on_space(x=x, y=y):
            self.workers.append(Worker(x=x, y=y, height=0, color=color))
        else:
            message = f"Invalid worker placement: Worker already exists at ({x}, {y})"
            logger.info(message)
            raise IllegalMoveError(message)

    def _num_workers(self, color: Color) -> int:
        return sum(worker.color == color for worker in self.workers)

    def move(
        self, color: Color, start_x: int, start_y: int, end_x: int, end_y: int
    ) -> None:
        """
        Move worker from coordinates (`start_x`, `start_y`) to (`end_x`, `end_y`).

        :param color: color of worker to move
        :param start_x: starting x-coordinate of worker
        :param start_y: starting y-coordinate of worker
        :param end_x: ending x-coordinate of worker
        :param end_y: ending y-coordinate of worker
        :return: None
        """
        worker_idx = self._get_worker_index(start_x, start_y)

        if self.workers[worker_idx].color != color:
            message = (
                f"Invalid move: player {color.value} is trying to move worker at"
                f" ({start_x}, {start_y}) but that worker is color"
                f" {self.workers[worker_idx].color.value}"
            )
            logger.info(message)
            raise IllegalMoveError(message)

        if self.is_valid_move(self.workers[worker_idx], end_x, end_y):
            self.workers[worker_idx].move(
                x=end_x, y=end_y, height=self._block_height(x=end_x, y=end_y)
            )
        else:
            message = f"Invalid move: ({start_x}, {start_y}) to ({end_x}, {end_y})"
            logger.info(message)
            raise IllegalMoveError(message)

    def build(
        self, color: Color, worker_x: int, worker_y: int, build_x: int, build_y: int
    ) -> None:
        """
        Build at coordinates (`build_x`, `build_y`) with worker at
        (`worker_x`, `worker_y`).

        :param color: color of building worker
        :param worker_x: x-coordinate of worker
        :param worker_y: y-coordinate of worker
        :param build_x: x-coordinate to build at
        :param build_y: y-coordinate to build at
        :return: None
        """
        worker = self._get_worker_at(x=worker_x, y=worker_y)
        if worker.color != color:
            message = (
                f"Invalid build: player {color} is trying to build with worker at "
                f"({worker_x}, {worker_y}) but that worker is color {worker.color}"
            )
            logger.info(message)
            raise IllegalMoveError(message)
        if self.is_valid_build(worker=worker, x=build_x, y=build_y):
            self.board_blocks[build_y][build_x] += 1
        else:
            message = (
                f"Invalid build: worker at ({worker_x}, {worker_y}) building at "
                f"({build_x}, {build_y})"
            )
            logger.info(message)
            raise IllegalMoveError(message)

    def is_valid_placement(self, color: Color, x: int, y: int) -> bool:
        """
        Check if coordinates (`x`, `y`) is a valid location for placement of worker
        with color `color`.

        :param color: color of worker to check
        :param x: x-coordinate to check
        :param y: y-coordinate to check
        :return: True if worker placement is valid otherwise False
        """
        if self._is_on_board(x=x, y=y):
            _is_valid_placement = self.player_can_place_workers(
                color=color
            ) and not self._worker_on_space(x=x, y=y)
        else:
            _is_valid_placement = False
        return _is_valid_placement

    def is_valid_move(self, worker: Worker, x: int, y: int) -> bool:
        """
        Check if it's valid for worker `worker` to move to coordinates (`x`, `y`).

        :param worker: worker to move
        :param x: x-coordinate to check
        :param y: y-coordinate to check
        :return: True if move is valid otherwise False
        """
        if self._is_on_board(x=x, y=y):
            xy_block_height = self._block_height(x=x, y=y)
            _is_valid_move = (
                xy_block_height <= worker.height + 1
                and xy_block_height < self.max_height
                and not self._worker_on_space(x=x, y=y)
                and self._is_neighboring_space(worker, x=x, y=y)
            )
        else:
            _is_valid_move = False
        return _is_valid_move

    def is_valid_build(self, worker: Worker, x: int, y: int) -> bool:
        """
        Check if it's valid for worker `worker` to build at coordinates (`x`, `y`).

        :param worker: worker to build
        :param x: x-coordinate to check
        :param y: y-coordinate to check
        :return: True if build is valid otherwise False
        """
        if self._is_on_board(x=x, y=y):
            _is_valid_build = (
                self._block_height(x=x, y=y) < self.max_height
                and not self._worker_on_space(x=x, y=y)
                and self._is_neighboring_space(worker, x=x, y=y)
            )
        else:
            _is_valid_build = False
        return _is_valid_build

    def is_valid_turn(
        self, worker: Worker, move_x: int, move_y: int, build_x: int, build_y: int
    ) -> bool:
        """
        Check if it's valid for worker `worker` to move to coordinates
        (`move_x`, `move_y`) and build at coordinates (`build_x`, `build_y`).

        :param worker: worker to move and build
        :param move_x: x-coordinate to check move action
        :param move_y: y-coordinate to check move action
        :param build_x: x-coordinate to check build action
        :param build_y: y-coordinate to check build action
        :return: True if move and build are valid otherwise False
        """
        return self.is_valid_move(worker, x=move_x, y=move_y) and self.is_valid_build(
            worker, x=build_x, y=build_y
        )

    def get_valid_placements(self, color: Color) -> list[PlaceWorkerTurn]:
        """
        Get a list of valid placement actions for player of color `color`.

        :param color: player color to check
        :return: List of valid worker placement turns
        """
        placement_coordinates = list(
            product(range(self.width), range(self.length), repeat=1)
        )
        placement_coordinates = list(
            filter(
                lambda xy: self.is_valid_placement(color=color, x=xy[0], y=xy[1]),
                placement_coordinates,
            )
        )
        valid_placement = [
            PlaceWorkerTurn(color=color, x=c[0], y=c[1]) for c in placement_coordinates
        ]
        return valid_placement

    def get_valid_moves(self, worker: Worker) -> list[MoveTurn]:
        """
        Get a list of valid move actions for worker `worker`.

        :param worker: worker to check
        :return: List of valid move turns
        """
        move_coordinates = [
            (worker.x + s[0], worker.y + s[1]) for s in self._neighboring_shifts
        ]
        move_coordinates = list(
            filter(
                lambda xy: self.is_valid_move(worker=worker, x=xy[0], y=xy[1]),
                move_coordinates,
            )
        )
        valid_moves = [
            MoveTurn(
                color=worker.color,
                start_x=worker.x,
                start_y=worker.y,
                end_x=c[0],
                end_y=c[1],
            )
            for c in move_coordinates
        ]
        return valid_moves

    def get_valid_builds(self, worker: Worker) -> list[BuildTurn]:
        """
        Get a list of valid build actions for worker `worker`.

        :param worker: worker to check
        :return: List of valid build turns
        """
        build_coordinates = [
            (worker.x + s[0], worker.y + s[1]) for s in self._neighboring_shifts
        ]
        build_coordinates = list(
            filter(
                lambda xy: self.is_valid_build(worker=worker, x=xy[0], y=xy[1]),
                build_coordinates,
            )
        )
        valid_builds = [
            BuildTurn(
                color=worker.color,
                worker_x=worker.x,
                worker_y=worker.y,
                build_x=c[0],
                build_y=c[1],
            )
            for c in build_coordinates
        ]
        return valid_builds

    def _is_on_board(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.length

    def _has_block(self, x: int, y: int) -> bool:
        has_block: bool = self.board_blocks[y][x] > 0
        return has_block

    def _block_height(self, x: int, y: int) -> int:
        block_height: int = self.board_blocks[y][x]
        return block_height

    def _worker_on_space(self, x: int, y: int) -> bool:
        for worker in self.workers:
            if worker.x == x and worker.y == y:
                return True
        return False

    def _is_neighboring_space(self, worker: Worker, x: int, y: int) -> bool:
        return (x - worker.x, y - worker.y) in self._neighboring_shifts

    def get_workers_with_color(self, color: Color) -> list[Worker]:
        """
        Return a list of workers belonging to player color `color`.

        :param color: player color
        :return: List of workers
        """
        return [worker for worker in self.workers if worker.color == color]

    def _get_worker_at(self, x: int, y: int) -> Worker:
        for worker in self.workers:
            if worker.x == x and worker.y == y:
                return worker
        raise IllegalMoveError(f"No worker at ({x}, {y})")

    def _get_worker_index(self, x: int, y: int) -> int:
        for idx, worker in enumerate(self.workers):
            if worker.x == x and worker.y == y:
                return idx
        logger.info(f"Invalid move: No worker at ({x}, {x})")
        raise IllegalMoveError(f"No worker at ({x}, {y})")

    def player_can_place_workers(self, color: Color) -> bool:
        """
        :param color: player color
        :return: True if player `color` can place a worker otherwise False.
        """
        return self._num_workers(color=color) < self.max_workers_per_player

    def player_can_move(self, color: Color) -> bool:
        """
        :param color: player color
        :return: True if player `color` can move a worker otherwise False.
        """
        has_valid_moves = False
        for worker in self.get_workers_with_color(color=color):
            if len(self.get_valid_moves(worker=worker)) != 0:
                has_valid_moves = True
                break

        return has_valid_moves

    def player_can_build(self, color: Color) -> bool:
        """
        :param color: player color
        :return: True if player `color` can build with a worker.
        """
        has_valid_builds = False
        for worker in self.get_workers_with_color(color=color):
            if len(self.get_valid_builds(worker=worker)) != 0:
                has_valid_builds = True
                break

        return has_valid_builds

    def player_in_win_state(self, color: Color) -> bool:
        """
        Test if board is in a win state. Assumes player `color` is the active player.

        Win conditions:
        1. If one of your Workers moves up on top height during your turn, you
           instantly win!
        2. You must always perform a move then build on your turn. If you are unable
           to, you lose.

        :return: True if board is in a win state otherwise False
        """
        workers_at_max_height = [
            worker
            for worker in self.get_workers_with_color(color=color)
            if worker.height == (self.max_height - 1)
        ]

        if len(workers_at_max_height) > 1:
            message = (
                f"Multiple workers are in a winning state: {workers_at_max_height}"
            )
            logger.info(message)
            raise IllegalBoardStateError(message)

        return len(workers_at_max_height) == 1

    def player_in_lose_state_before_move(self, color: Color) -> bool:
        """
        Test if board is in a lose state. Assumes player `color` is the active player.

        Win conditions:
        1. If one of your Workers moves up on top height during your turn, you
           instantly win!
        2. You must always perform a move then build on your turn. If you are unable
           to, you lose.

        :return: False if worker can move otherwise True
        """
        return not self.player_can_move(color=color)

    def player_in_lose_state_after_move(self, worker_x: int, worker_y: int) -> bool:
        """
        Assumes worker at (`worker_x`, `worker_y`) moved last turn and needs to build
        next.

        Win conditions:
        1. If one of your Workers moves up on top height during your turn, you
           instantly win!
        2. You must always perform a move then build on your turn. If you are unable
           to, you lose.

        :param worker_x: x-coordinate of worker
        :param worker_y: y-coordinate of worker
        :return: False if worker can build otherwise True
        """
        worker = self._get_worker_at(x=worker_x, y=worker_y)
        return len(self.get_valid_builds(worker=worker)) == 0

    def reset(self) -> None:
        """Reset board and workers to original state."""
        self.workers = []
        self.board_blocks = np.zeros(shape=(self.length, self.width), dtype=int)


class IllegalBoardStateError(Exception):
    """Exception for when Board is in an illegal state"""


class IllegalMoveError(Exception):
    """Exception for an illegal move"""
