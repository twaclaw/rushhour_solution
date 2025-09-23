# Two different approaches to solving the Rushhour puzzle 🚗

I coded these solutions purely for fun. They solve [this challenge](https://twaclaw.github.io/posts/projects/programming_challenge/).

I tackled the problem in two different ways:

- Using standard space-search strategies (BFS and $A^{*}$) in Python.
- Implementing it declaratively using [JuMP](https://jump.dev/) (an algebraic modeling language for mathematical optimization in Julia).


## Python solver

### Installation

```bash
git clone https://github.com/twaclaw/rushhour_solution.git
cd rushhour_solution
uv venv --python=python3.13
uv pip install -e .
```

### Execution

See [examples](./examples) to see how to define the input configuration.

```bash
rushhour --help

# Defaults to A* (--algorithm astar)
rushhour --conf examples/expert31.json  solve
rushhour --conf examples/expert31.json  solve --algorithm bfs

# To draw all the board positions in the solution
rushhour --conf examples/expert31.json  --draw-steps solve

# To verify a solution, provided the input file has the field "solution"
rushhour --conf examples/beginner10.json  --draw-steps verify
```

Here is an example of the output:


![example](./images/example.svg)


## JuMP solver

I implemented three slightly different models. See the [jump](./jump/README.md) folder for details.

<!-- For a detailed explanation of the approach, check [this post](https://twaclaw.github.io/posts/projects/optimizing_rushhour). -->


