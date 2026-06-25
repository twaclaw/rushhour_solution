use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use std::collections::{HashMap, HashSet, VecDeque};

const N_CARS: usize = 16;
const BOARD_SIZE: usize = 6;
const X_ID: usize = 0; // car_id('X')
const X_ROW: usize = 2; // the X car is constrained to row 2

#[derive(Clone, Copy, PartialEq, Eq, Hash)]
enum Orientation {
    H,
    V,
}

/// Car Names in Python (in input strings)
fn car_id(letter: char) -> Option<usize> {
    Some(match letter {
        'X' => 0,
        'A' => 1,
        'B' => 2,
        'C' => 3,
        'D' => 4,
        'E' => 5,
        'F' => 6,
        'G' => 7,
        'H' => 8,
        'I' => 9,
        'J' => 10,
        'K' => 11,
        'O' => 12,
        'P' => 13,
        'Q' => 14,
        'R' => 15,
        _ => return None,
    })
}

/// Inverse of `car_id`: car id back to its input letter.
fn car_letter(id: usize) -> char {
    const LETTERS: [char; N_CARS] = [
        'X', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'O', 'P', 'Q', 'R',
    ];
    LETTERS[id]
}

/// A single car move: car `id` shifted by `inc` cells (sign = direction).
#[derive(Clone, Copy)]
struct Move {
    id: usize,
    inc: i32,
}

impl Move {
    /// Same labels as on the Python side (e.g, 'O+1', 'X-2', etc.)
    fn label(&self) -> String {
        let letter = car_letter(self.id);
        if self.inc > 0 {
            format!("{letter}+{}", self.inc)
        } else {
            format!("{letter}{}", self.inc)
        }
    }
}

fn car_size(id: usize) -> usize {
    if id < 12 { // car 'O'
        2
    } else {
        3
    }
}

/// Bitmask of the cells a car covers, or an error if it falls off the board.
fn car_mask(
    orientation: Orientation,
    row: usize,
    col: usize,
    size: usize,
) -> Result<u64, String> {
    let fits = match orientation {
        Orientation::H => col + size <= BOARD_SIZE,
        Orientation::V => row + size <= BOARD_SIZE,
    };
    if row >= BOARD_SIZE || col >= BOARD_SIZE || !fits {
        return Err(format!(
            "car at ({row}, {col}) does not fit on a {BOARD_SIZE}x{BOARD_SIZE} board"
        ));
    }

    let mut mask = 0u64;
    for k in 0..size {
        let (r, c) = match orientation {
            Orientation::H => (row, col + k),
            Orientation::V => (row + k, col),
        };
        mask |= 1u64 << (r * BOARD_SIZE + c); //row major
    }
    Ok(mask)
}

#[derive(Clone, Copy, PartialEq, Eq, Hash)]
struct Game {
    board: u64, // occupancy bitboard, row-major
    /// Per-car mask indexed by car id; `0` means the car is absent.
    cars: [u64; N_CARS],
    orientations: [Orientation; N_CARS],
}

impl Game {
    /// Build a board from car_strs like `["XH23", "AH01", ...]`, verifying
    /// that every car fits on the board and no two cars overlap.
    fn new(initial_state: Vec<String>) -> Result<Self, String> {
        let mut game = Game {
            board: 0,
            cars: [0; N_CARS],
            orientations: [Orientation::H; N_CARS]
        };

        for car_str in initial_state {
            let chars: Vec<char> = car_str.chars().collect();
            if chars.len() != 4 {
                return Err(format!(
                    "invalid car car_str {car_str:?} (expected 4 chars)"
                ));
            }

            let id = car_id(chars[0])
                .ok_or_else(|| format!("unknown car name {:?} in {car_str:?}", chars[0]))?;

            let orientation = match chars[1] {
                'H' => Orientation::H,
                'V' => Orientation::V,
                other => return Err(format!("invalid orientation {other:?} in {car_str:?}")),
            };

            let row = chars[2]
                .to_digit(10)
                .ok_or_else(|| format!("invalid row in {car_str:?}"))? as usize;

            let col = chars[3]
                .to_digit(10)
                .ok_or_else(|| format!("invalid col in {car_str:?}"))? as usize;

            if game.cars[id] != 0 {
                return Err(format!("car {:?} placed more than once", chars[0]));
            }

            let mask = car_mask(orientation, row, col, car_size(id))
                .map_err(|e| format!("{e} (car {car_str:?})"))?;

            if id == X_ID && row != X_ROW {
                return Err(format!("car X must be in row 2"));
            }

            // Verify the target cells are not already occupied.
            if game.board & mask != 0 {
                return Err(format!("car {car_str:?} overlaps an already placed car"));
            }

            game.board |= mask;
            game.cars[id] = mask;
            game.orientations[id] = orientation
        }

        Ok(game)
    }

    /// Number of cars between the X car and the exit
    fn obstacles_before_exit(&self) -> u32 {
        let x = self.cars[X_ID];
        let x_end = 63 - x.leading_zeros() as usize; // X's rightmost cell (highest set bit)
        let row_end = X_ROW * BOARD_SIZE + (BOARD_SIZE - 1); // last cell of X's row
        let len = row_end - x_end; // cells to the right of X, up to the exit
        let after = ((1u64 << len) - 1) << (x_end + 1); // mask of just those cells
        (after & self.board).count_ones()
    }

    // A new game with car id moved
    fn moved(&self, id: usize, old: u64, new: u64) -> Game {
        let mut g = *self;
        g.cars[id] = new;
        g.board = (self.board & !old) | new; // clear old cells, set new ones
        g
    }

    /// Every state reachable by sliding a single car one or more cells
    /// Move contains also the sequence labels (for creating the solution sequence)
    fn possible_moves(&self) -> Vec<(Move, Game)> {
        let mut moves = Vec::new();

        for id in 0..N_CARS {
            let m = self.cars[id];
            if m == 0 {
                continue; // car absent
            }
            let others = self.board & !m; // occupancy with this car removed
            let orientation = self.orientations[id];

            // Amount to shift the cars one position (horizontally or vertically -> row-major)
            let shift = match orientation {
                Orientation::H => 1,
                Orientation::V => BOARD_SIZE,
            };

            // positive:
            // -> True  -> right or down
            // -> False -> left or u p 
            for positive in [true, false] {
                let mut cur = m;
                let mut steps = 0i32; // cells moved so far in this direction
                loop {
                    // Stop if the leading cell of the car is already on the edge,
                    let head = 63 - cur.leading_zeros() as usize; // bottom / right cell
                    let tail = cur.trailing_zeros() as usize; // top / left cell
                    let on_edge = match (orientation, positive) {
                        (Orientation::H, true) => head % BOARD_SIZE == BOARD_SIZE - 1,
                        (Orientation::H, false) => tail % BOARD_SIZE == 0,
                        (Orientation::V, true) => head / BOARD_SIZE == BOARD_SIZE - 1,
                        (Orientation::V, false) => tail / BOARD_SIZE == 0,
                    };
                    if on_edge {
                        break;
                    }

                    let next = if positive { cur << shift } else { cur >> shift };
                    if next & others != 0 {
                        break; // blocked by another car
                    }

                    steps += 1;
                    let inc = if positive { steps } else { -steps };
                    moves.push((Move { id, inc }, self.moved(id, m, next)));
                    cur = next;
                }
            }
        }

        moves
    }

    fn bfs(&self) -> (Option<Vec<String>>, usize) {
        let mut visited: HashSet<Game> = HashSet::new();
        let mut queue: VecDeque<Game> = VecDeque::new();
        // 
        let mut solution_seq: HashMap<Game, (Game, Move)> = HashMap::new();

        queue.push_back(*self);
        visited.insert(*self);

        while let Some(state) = queue.pop_front() {
            if state.obstacles_before_exit() == 0 {
                return (Some(self.reconstruct(&solution_seq, state)), visited.len());
            }

            for (mv, next) in state.possible_moves() {
                if visited.insert(next) {
                    solution_seq.insert(next, (state, mv));
                    queue.push_back(next);
                }
            }
        }

        (None, visited.len())
    }

    /// reconstruct solution sequence from goal
    fn reconstruct(&self, solution_seq: &HashMap<Game, (Game, Move)>, goal: Game) -> Vec<String> {
        let mut moves = Vec::new();
        let mut cur = goal;
        // The start state has no predecessor, so the loop stops there.
        while let Some(&(prev, mv)) = solution_seq.get(&cur) {
            moves.push(mv.label());
            cur = prev;
        }
        moves.reverse();
        moves
    }

}

/// Solve a Rush Hour puzzle.
#[pyfunction]
#[pyo3(signature = (initial_state, solver="bfs"))]
fn solve(
    initial_state: Vec<String>,
    solver: &str,
) -> PyResult<(Option<Vec<String>>, usize)> {
    let game = Game::new(initial_state).map_err(PyValueError::new_err)?;
    match solver {
        "bfs" => Ok(game.bfs()),
        _ => Err(PyValueError::new_err(format!(
            "Algorithm {solver} not implemented!"
        ))),
    }
}

#[pymodule]
fn rust_hour(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(solve, m)?)?;
    Ok(())
}
