"""Module for tracking and managing game state"""
import logging
from collections import deque
from copy import deepcopy
from dataclasses import dataclass
from typing import Iterable, Optional

from santorini_bot.board import (
    Board,
    Color,
    TurnArgs,
    TurnActions,
    BuildTurn,
    MoveTurn,
    PlaceWorkerTurn,
    IllegalMoveError,
)

logger = logging.getLogger(__name__)


@dataclass
class GameState:
    """Dataclass for holding game state"""

    active_player: Color
    board: Board
    turn_action: TurnActions
    turn: TurnArgs


class GameManager:
    """Class to manage game states"""

    def __init__(
        self,
        player_order: Iterable[Color] = (Color.BLUE, Color.WHITE),
        board: Optional[Board] = None,
    ):
        self.initial_board = board or Board()
        self.board = deepcopy(self.initial_board)

        self.initial_player_order = deque(player_order)
        self.player_order = deepcopy(self.initial_player_order)

        self._initial_turn_order = deque([TurnActions.MOVE, TurnActions.BUILD])
        self.turn_order = deepcopy(self._initial_turn_order)

        self.game_state_log: list[GameState] = []

    @property
    def active_player(self) -> Color:
        """active player is the first player in order"""
        return self.player_order[0]

    @property
    def current_turn_action(self) -> TurnActions:
        """
        Current turn action is 'place worker' if a player can place a worker on
        board otherwise the first action in the turn order
        """
        can_place_workers = any(
            self.board.player_can_place_workers(c) for c in self.player_order
        )

        return TurnActions.PLACE_WORKER if can_place_workers else self.turn_order[0]

    @property
    def previous_game_state(self) -> Optional[GameState]:
        """previous game state based on game state log"""
        return self.game_state_log[-1] if len(self.game_state_log) != 0 else None

    def game_loop(self) -> None:
        """Run game loop: turn over, turn actions"""
        player_input = ""

        while player_input != "quit":
            if self.previous_game_state is None:
                # Don't rotate active player for first move of the game
                board = deepcopy(self.initial_board)
            else:
                board = deepcopy(self.previous_game_state.board)

            logger.info(board.display_board())

            if self._in_end_game_state():
                # Game is over. Stop game loop.
                break

            logger.info(
                f"{self.active_player.value} player's turn to "
                f"{self.current_turn_action}"
            )
            player_input = input()

            if player_input == "quit":
                break

            logger.info(
                f"{self.current_turn_action.value} turn coordinates: {player_input}"
            )

            if self.current_turn_action == TurnActions.PLACE_WORKER:
                self.update_game_state(
                    turn_action=TurnActions.PLACE_WORKER,
                    turn_coordinates=list(map(int, player_input.split(" "))),
                )

            elif self.current_turn_action == TurnActions.MOVE:
                self.update_game_state(
                    turn_action=TurnActions.MOVE,
                    turn_coordinates=list(map(int, player_input.split(" "))),
                )

            elif self.current_turn_action == TurnActions.BUILD:
                self.update_game_state(
                    turn_action=TurnActions.BUILD,
                    turn_coordinates=list(map(int, player_input.split(" "))),
                )

            else:
                logger.info(f'Unknown turn action: "{self.current_turn_action}"')

    def update_game_state(
        self,
        turn_action: TurnActions,
        turn_coordinates: list[int],
        active_player: Optional[Color] = None,
    ):
        """

        :param turn_action: turn actions corresponding to turn coordinates
        :param turn_coordinates: turn coordinates corresponding to turn action
        :param active_player: Optionally specify the player making the action.
            If not specified use `active_player` attribute
        :return: None
        """
        logger.debug(
            f'game state:  active player: "{self.active_player}"  '
            f'turn_action: "{turn_action}"  turn_coordinates: "{turn_coordinates}"'
        )
        if active_player is not None and active_player != self.active_player:
            raise IllegalMoveError(
                f"Player turn is out of order. Expected {self.active_player} but got"
                f" {active_player}"
            )

        if turn_action != self.current_turn_action:
            raise IllegalMoveError(
                f"Turn action is out of order. Expected {self.current_turn_action} but"
                f" got {turn_action}"
            )

        board = deepcopy(self.board)
        in_loss_state_cant_build = False

        if turn_action == TurnActions.PLACE_WORKER:
            board.place_worker(
                color=self.active_player, x=turn_coordinates[0], y=turn_coordinates[1]
            )
            self.game_state_log.append(
                GameState(
                    active_player=self.active_player,
                    board=board,
                    turn_action=TurnActions.PLACE_WORKER,
                    turn=PlaceWorkerTurn(
                        color=self.active_player,
                        x=turn_coordinates[0],
                        y=turn_coordinates[1],
                    ),
                )
            )

        elif turn_action == TurnActions.MOVE:
            board.move(
                color=self.active_player,
                start_x=turn_coordinates[0],
                start_y=turn_coordinates[1],
                end_x=turn_coordinates[2],
                end_y=turn_coordinates[3],
            )
            self.game_state_log.append(
                GameState(
                    active_player=self.active_player,
                    board=board,
                    turn_action=TurnActions.MOVE,
                    turn=MoveTurn(
                        color=self.active_player,
                        start_x=turn_coordinates[0],
                        start_y=turn_coordinates[1],
                        end_x=turn_coordinates[2],
                        end_y=turn_coordinates[3],
                    ),
                )
            )

            # check for loss state
            in_loss_state_cant_build = board.player_in_loss_state_after_move(
                worker_x=turn_coordinates[2], worker_y=turn_coordinates[3]
            )

        elif turn_action == TurnActions.BUILD:
            self._check_moved_worker_before_build(
                build_worker_x=turn_coordinates[0], build_worker_y=turn_coordinates[1]
            )

            board.build(
                color=self.active_player,
                worker_x=turn_coordinates[0],
                worker_y=turn_coordinates[1],
                build_x=turn_coordinates[2],
                build_y=turn_coordinates[3],
            )
            self.game_state_log.append(
                GameState(
                    active_player=self.active_player,
                    board=board,
                    turn_action=TurnActions.BUILD,
                    turn=BuildTurn(
                        color=self.active_player,
                        worker_x=turn_coordinates[0],
                        worker_y=turn_coordinates[1],
                        build_x=turn_coordinates[2],
                        build_y=turn_coordinates[3],
                    ),
                )
            )

        self.board = board

        # Check for win/loss state
        in_win_state = self._check_win_state_board_win_state(logger_info_message=False)

        if not in_win_state:
            # Update new state
            if self.previous_game_state is not None and (
                self.previous_game_state.turn_action != TurnActions.MOVE
                or in_loss_state_cant_build
            ):
                # Move should be followed by build of same worker
                # If a worker can't build then they lose and are removed from the turn
                # order
                self._change_active_player()

            if not in_loss_state_cant_build:
                # Must update board before turn action because checks depend on board
                # state
                self._change_current_turn_action()

    def _check_moved_worker_before_build(
        self, build_worker_x: int, build_worker_y: int
    ):
        """
        Checks that the worker building was the worker moved last turn

        :param build_worker_x: x-coordinate of worker
        :param build_worker_y: y-coordinate of worker
        :return: None
        """
        if self.previous_game_state is None:
            raise IllegalMoveError("Cannot build as the first turn of the game.")

        if self.previous_game_state.turn_action == TurnActions.MOVE:
            previous_turn: MoveTurn = self.previous_game_state.turn  # type: ignore
        else:
            raise IllegalMoveError(
                "Must move before build, but got "
                f"{self.previous_game_state.turn_action}"
            )

        if (previous_turn.end_x, previous_turn.end_y) != (
            build_worker_x,
            build_worker_y,
        ):
            raise IllegalMoveError(
                "Must build with the last worker to move."
                f" Moved worker to ({previous_turn.end_x},"
                f" {previous_turn.end_y}) but building with worker at "
                f"({build_worker_x}, {build_worker_y})"
            )

    def _in_end_game_state(self) -> bool:
        """
        Remove players in loss state and optionally declare a winner.

        Players can be in a loss state if they don't have a valid move and build on
        their turn. A player can win by reaching the highest level on their turn or
        being the last remaining player.

        :return: True if a player is in a win state otherwise False
        """
        self._check_loss_state_player_cant_build()
        self._check_loss_state_player_cant_move()

        is_in_end_game_state = self._check_win_state_one_player_left()

        if not is_in_end_game_state:
            is_in_end_game_state = self._check_win_state_board_win_state(
                logger_info_message=True
            )

        return is_in_end_game_state

    def _check_loss_state_player_cant_build(self):
        """
        Check if a player has lost because they can't build with the worker they moved
        the last turn. If so remove that player from the player order and output that
        they have lost.

        :return: None
        """
        if (
            self.previous_game_state is not None
            and len(self.player_order) != 1
            and self.previous_game_state.turn_action == TurnActions.MOVE
        ):
            in_loss_state_cant_build = (
                self.previous_game_state.board.player_in_loss_state_after_move(
                    worker_x=self.previous_game_state.turn.end_x,
                    worker_y=self.previous_game_state.turn.end_y,
                )
            )

            if in_loss_state_cant_build:
                logger.info(
                    f"Player {self.previous_game_state.active_player} lost! No valid "
                    "builds."
                )
                self.player_order.remove(self.previous_game_state.active_player)

    def _check_loss_state_player_cant_move(self):
        """
        Check if a player has lost because they can't make a valid move with any of
        their workers. If so remove that player from the player order and output that
        they have lost.

        :return: None
        """
        if (
            self.previous_game_state is not None
            and len(self.player_order) != 1
            and self.current_turn_action == TurnActions.MOVE
        ):
            in_loss_state = (
                self.previous_game_state.board.player_in_loss_state_before_move(
                    color=self.active_player
                )
            )

            if in_loss_state:
                logger.info(f"Player {self.active_player.value} lost! No valid moves.")
                self.player_order.remove(self.active_player)

    def _check_win_state_one_player_left(self) -> bool:
        """
        :return: True if the active player is the only player left in the turn order
            otherwise False
        """
        in_win_state = False
        if len(self.player_order) == 1:
            logger.debug(f"Only one player left in player_order: {self.player_order}")
            logger.info(f"Player {self.active_player.value} won!")
            in_win_state = True
        return in_win_state

    def _check_win_state_board_win_state(
        self, logger_info_message: bool = False
    ) -> bool:
        """
        :param logger_info_message: If True log a message to INFO that the active
            player has won otherwise don't display. This is to avoid duplicate messages
            when this method is called more than once.
        :return: True if the active player is in a win state on the board otherwise
            False.
        """
        in_win_state = False

        if (
            self.previous_game_state is not None
            and self.previous_game_state.board.player_in_win_state(
                color=self.active_player
            )
        ):
            logger.debug(f"Player {self.active_player.value} in win state")
            if logger_info_message:
                logger.info(f"Player {self.active_player.value} won!")
            in_win_state = True

        return in_win_state

    def _change_active_player(self):
        """
        Update active player by rotating player order
        """
        new_active_player_color = self.player_order.popleft()
        self.player_order.append(new_active_player_color)

    def _change_current_turn_action(self):
        """
        Update current turn action and turn order if players are done placing workers
        """
        no_player_can_place_workers = all(
            not self.board.player_can_place_workers(c) for c in self.player_order
        )

        if (
            no_player_can_place_workers
            and self.previous_game_state.turn_action != TurnActions.PLACE_WORKER
        ):
            new_turn_action = self.turn_order.popleft()
            self.turn_order.append(new_turn_action)

    def reset(self) -> None:
        """Reset attributes related to game state"""
        self.board = deepcopy(self.initial_board)
        self.player_order = deepcopy(self.initial_player_order)
        self.turn_order = deepcopy(self._initial_turn_order)
        self.game_state_log = []
