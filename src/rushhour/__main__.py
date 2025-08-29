import argparse
import json

from .game import Game


def main():
    parser = argparse.ArgumentParser(description="Run a Rush Hour game.")
    parser.add_argument("--conf", type=str, help="File with game initial configuration and solution (optional)", required=True)
    args = parser.parse_args()

    with open(args.conf, "r") as f:
        config = json.load(f)

    g = Game(config["initial_state"])

    print("Initial board:\n")
    print(g)
    # print(g.get_possible_moves())

    solution = g.solve()

    print(f"Solution found by DFS:\n {solution}\n")
    print(g)


if __name__ == "__main__":
    main()
