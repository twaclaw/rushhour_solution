import heapq
from collections import deque
from enum import IntEnum
from typing import Literal

import torch

BOARD_SIZE = 6

"""
Conventions:
- The top left corner is (0, 0)
- The bottom right corner is (BOARD_SIZE - 1, BOARD_SIZE - 1)
- Horizontal movements towards the right are positive, and towards the left are negative.
- Vertical movements downwards are positive, and upwards are negative.
- In the board, zero (0) represents an empty cell
"""


class CarName(IntEnum):
    """
    Change the integer values to whatever fits your purpose. They must be unique.
    """

    X = 1  # red
    A = 2  # light green
    B = 3  # orange
    C = 4  # light blue
    D = 5  # pink
    E = 6  # purple
    F = 7  # dark green
    G = 8  # gray
    H = 9  # beige
    I = 10  # light yellow
    J = 11  # brown
    K = 12  # olive
    O = 13  # dark yellow
    P = 14  # light purple
    Q = 15  # blue
    R = 16  # green


class Orientation(IntEnum):
    H = 0
    V = 1


class Car:
    def __init__(
        self,
        name: CarName,
        orientation: Orientation,
        start: tuple[int, int],
        board_size: int = BOARD_SIZE,
    ):
        self.name = name
        self.orientation = orientation
        self.start = start
        self.size = self._size()
        self.board_size = board_size

    def _size(self) -> int:
        if self.name == CarName.X or self.name < CarName.O:
            return 2
        return 3

    def move_by(self, inc: int) -> "Car":
        """
        Move a car by `inc` cells.

        If inc > 0, move right (H) or down (V).
        If inc < 0, move left (H) or up (V).
        """
        if self.orientation == Orientation.H:
            return Car(self.name, self.orientation, (self.start[0], self.start[1] + inc))
        return Car(self.name, self.orientation, (self.start[0] + inc, self.start[1]))

    def in_board(self) -> bool:
        return (self.start[0] >= 0 and self.start[1] >= 0) and (self.end[0] < self.board_size and self.end[1] < self.board_size)

    @property
    def end(self) -> tuple[int, int]:
        """
        The end position of the car, i.e., the last occupied cell.
        """
        if self.orientation == Orientation.H:
            return (self.start[0], self.start[1] + self.size - 1)
        return (self.start[0] + self.size - 1, self.start[1])

    @property
    def value(self) -> torch.Tensor:
        """
        A tensor representing the car's value on the board.
        """
        return torch.tensor([[self.name]] * self.size, dtype=torch.uint8).T

    @property
    def indices(self) -> tuple[slice, int] | tuple[int, slice]:
        """
        The positions in the board occupied by the car.
        """
        if self.orientation == Orientation.H:
            return self.start[0], slice(self.start[1], self.end[1] + 1)
        return slice(self.start[0], self.end[0] + 1), self.start[1]

    @classmethod
    def from_string(cls, car_str: str) -> "Car":
        name = CarName[car_str[0]]
        orientation = Orientation.H if car_str[1] == "H" else Orientation.V
        x, y = int(car_str[2]), int(car_str[3])
        return cls(name, orientation, (x, y))

    def __str__(self):
        return f"{self.name.name}{self.orientation.name}{self.start[0]}{self.start[1]}"


class Game:
    def __init__(self, initial_state: list[str], board_size: int = BOARD_SIZE):
        """
        Representation of the Rush Hour game state (board and rules).

        Initial states follow the format: <CarName><Orientation><x><y>
        ["XH23", "AH01", "BH12", ...]
        """
        self.board = torch.zeros((board_size, board_size), dtype=torch.uint8)
        self._cars: dict[CarName, Car] = {}
        self.board_size = board_size
        for car_str in initial_state:
            car = Car.from_string(car_str)
            if car.name == CarName.X:
                if car.orientation != Orientation.H or car.start[0] != 2:
                    raise ValueError("The X car must be horizontally in row 2")
            self.add_car(car)

        if CarName.X not in self._cars:
            raise ValueError("The X car must be present in the initial state")

    def add_car(self, car: Car):
        if not self._can_place_car(car):
            raise ValueError(f"Cannot place car {car.name.name} at {car.start} with orientation {car.orientation}")
        self._cars[car.name] = car
        self._place_car(car)

    def _can_place_car(self, car: Car) -> bool:
        if not car.in_board():
            return False

        return torch.all(self.board[car.indices] == 0).item()

    def _place_car(self, car: Car):
        self.board[car.indices] = car.value

    def _can_move_car(self, car: Car, inc: int) -> bool:
        c = car.move_by(inc)
        if not c.in_board():
            return False

        return torch.all((self.board[c.indices] == 0) | (self.board[c.indices] == c.name)).item()

    def _move_car(self, car: Car, inc: int):
        c = car.move_by(inc)
        if not c.in_board():
            raise ValueError(f"Car {c.name.name} moved out of bounds to {c.start}")

        if torch.all((self.board[c.indices] == 0) | (self.board[c.indices] == c.name)).item():
            self.board[car.indices] = 0
            self.board[c.indices] = c.value
            self._cars[c.name] = c
        else:
            raise ValueError(
                f"Cannot move car {car.name.name} (by inc={inc}) (name={c.name}) ({car.indices} {c.indices}) as it overlaps with another car or is out of bounds\n{self.__str__()}. Cars: {[str(x) for x in self.cars.values()]}"
            )

    def move_sequence(self, moves: list[str]):
        """
        Sequence of moves look like this: ["X2", "A1", "B-1", "A+3"]
        The orientation is not required because it is given by the initial position.
        """
        for move in moves:
            try:
                car, inc = move[0], int(move[1:])
                car = CarName[car]
            except (KeyError, ValueError):
                raise ValueError(f"Invalid move: {move}. Expected format is '<CarName><inc>', e.g., 'X2' or 'X-1'.")

            if car in self._cars:  # ignore moves of cars not in the game
                self._move_car(self._cars[car], inc)

    def _obstacles_before_exit(self) -> int:
        """
        Count the number of obstacles (cars) in the way of the X car to exit.
        """
        xcar = self._cars.get(CarName.X)
        end = xcar.end
        return (self.board[end[0], end[1] + 1 :] != 0).sum().item()

    def is_solution(self) -> bool:
        """
        Check if the game is solved, i.e., the X car can exit the board
        """
        return self._obstacles_before_exit() == 0


    def __str__(self):
        board_str = ""
        for row in self.board:
            board_str += " ".join(self._cars[cell.item()].name.name if cell.item() != 0 else "." for cell in row) + "\n"
        return board_str.strip()

    def _count_zeros(self, tensor: torch.Tensor, position: int) -> int:
        """
        Count the number of zeros in the tensor starting from the given position.
        """
        if position >= len(tensor) or tensor[position] != 0:
            return 0

        zeros = tensor[position:] == 0
        return zeros.sum().item() if zeros.all() else zeros.float().argmin().item()

    @property
    def cars(self) -> dict[CarName, Car]:
        return self._cars

    def _get_car_moves(self, car_name: CarName) -> tuple[int, int]:
        """
        Get the possible moves for a car.
        Returns a tuple of (positve moves, negative moves).
        """
        car = self._cars[car_name]
        if car.orientation == Orientation.H:
            row = self.board[car.start[0]]
            pos_moves = self._count_zeros(row, car.end[1] + 1)
            neg_moves = self._count_zeros(row.flip(0), self.board_size - (car.start[1]))
        else:
            col = self.board[:, car.start[1]]
            pos_moves = self._count_zeros(col, car.end[0] + 1)
            neg_moves = self._count_zeros(col.flip(0), self.board_size - (car.start[0]))

        return pos_moves, neg_moves

    def _get_possible_moves(self) -> dict[CarName, torch.Tensor]:
        moves = {}
        for car_name in self._cars:
            pos_moves, neg_moves = self._get_car_moves(car_name)
            if pos_moves > 0 or neg_moves > 0:
                moves[car_name] = torch.tensor([pos_moves, neg_moves], dtype=torch.uint8)
        return moves

    @staticmethod
    def tensor_to_tuple(tensor: torch.Tensor) -> tuple:
        return tuple(tensor.flatten().tolist())

    @staticmethod
    def complement(seq: list[str]) -> list[str]:
        return [f"{x[0]}{-int(x[1:])}" if x[1] == "+" else f"{x[0]}+{abs(int(x[1:]))}" for x in seq]


    def heuristic(self):
        return int(self._obstacles_before_exit())

    def bfs(self) -> tuple[list[str] | None, int]:
        visited = set()
        queue = deque()
        queue.append((self.tensor_to_tuple(self.board), [], self._cars.copy()))
        nodes_visited = 0

        while queue:
            nodes_visited += 1
            board_tuple, moves_seq, cars = queue.popleft()
            self.board = torch.tensor(board_tuple, dtype=torch.uint8).reshape(self.board_size, self.board_size).clone()
            self._cars = cars.copy()

            if self.is_solution():
                return moves_seq, nodes_visited

            state_tuple = self.tensor_to_tuple(self.board)
            if state_tuple in visited:
                continue
            visited.add(state_tuple)
            possible_moves = self._get_possible_moves()
            for car_name in possible_moves:
                pos_moves, neg_moves = possible_moves[car_name].tolist()
                moves = [p for p in range(1, pos_moves + 1)] + [-n for n in range(1, neg_moves + 1)]
                car = self._cars[car_name]
                for inc in moves:
                    self._move_car(car, inc)
                    new_move = f"{car.name.name}+{inc}" if inc > 0 else f"{car.name.name}{inc}"
                    queue.append((self.tensor_to_tuple(self.board), moves_seq + [new_move], self._cars.copy()))
                    self._move_car(self._cars[car_name], -inc) # backtrack with updated car

        return None, nodes_visited


    def a_star(self) -> tuple[list[str] | None, int]:
        """
        A* search algorithm.
        """
        heap = []
        # g_costs stores the minimum cost (g_score) found so far to reach a state
        g_costs = {self.tensor_to_tuple(self.board): 0}
        heapq.heappush(heap, (self.heuristic(), 0, self.tensor_to_tuple(self.board), [], self._cars.copy()))
        nodes_visited = 0

        while heap:
            nodes_visited += 1
            h, cost, board_tuple, moves_seq, cars = heapq.heappop(heap)

            if cost > g_costs.get(board_tuple, float('inf')):
                continue

            self.board = torch.tensor(board_tuple, dtype=torch.uint8).reshape(self.board_size, self.board_size).clone()
            self._cars = cars.copy()

            if self.is_solution():
                return moves_seq, nodes_visited

            possible_moves = self._get_possible_moves()
            for car_name in possible_moves:
                pos_moves, neg_moves = possible_moves[car_name].tolist()
                moves = [p for p in range(1, pos_moves + 1)] + [-n for n in range(1, neg_moves + 1)]
                car = self._cars[car_name]
                for inc in moves:
                    self._move_car(car, inc)
                    new_cost = cost + 1
                    new_board_tuple = self.tensor_to_tuple(self.board)
                    if new_cost < g_costs.get(new_board_tuple, float('inf')):
                        g_costs[new_board_tuple] = new_cost
                        f_score = new_cost + self.heuristic()
                        new_move = f"{car.name.name}+{inc}" if inc > 0 else f"{car.name.name}{inc}"
                        heapq.heappush(heap, (f_score, new_cost, new_board_tuple, moves_seq + [new_move], self._cars.copy()))
                    self._move_car(self._cars[car_name], -inc)  # backtrack with updated car

        return None, nodes_visited

    def solve(self, solver: Literal["a_star", "bfs"] = "a_star") -> tuple[list[str] | None, int]:
        if solver == "a_star":
            return self.a_star()
        elif solver == "bfs":
            return self.bfs()
        else:
            raise ValueError(f"Unknown solver: {solver}")