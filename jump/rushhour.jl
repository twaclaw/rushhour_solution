using JuMP
include("utils.jl")

#-----------------------------------------------------------------------------------------
# Select solver
#-----------------------------------------------------------------------------------------

optimizer = "highs"

if optimizer == "highs"
    using HiGHS
    model = Model(HiGHS.Optimizer)
    Highs_resetGlobalScheduler(1)
    set_attribute(model, MOI.NumberOfThreads(), 6) # not really used in MIP: https://ergo-code.github.io/HiGHS/dev/parallel/
elseif optimizer == "cuopt"
    using cuOpt
    model = Model(cuOpt.Optimizer)
else
    error("Unknown optimizer: $optimizer")
end


#-----------------------------------------------------------------------------------------
# Command line
#-----------------------------------------------------------------------------------------

if length(ARGS) < 2
    println("Usage: julia rushhour.jl <input_json_file> <model_option>")
    println("Example: julia rushhour.jl ../examples/beginner10.json model0")
    println("Available models: model0, model1, model2")
    exit(1)
end

input_file = ARGS[1]
model_option = ARGS[2]

if !isfile(input_file)
    println("Error: File '$input_file' not found!")
    exit(1)
end

# Validate model option
valid_models = ["model0", "model1", "model2"]
if !(model_option in valid_models)
    println("Error: Invalid model option '$model_option'")
    println("Available models: $(join(valid_models, ", "))")
    exit(1)
end

println("Loading puzzle from: $input_file")
println("Using model: $model_option")

#*****************************************************************************************
#*****************************************************************************************
# MODEL
#*****************************************************************************************
#*****************************************************************************************



#-----------------------------------------------------------------------------------------
# Load initial positions
#-----------------------------------------------------------------------------------------

initial_conf = load_game(input_file)

#-----------------------------------------------------------------------------------------
# Model parameters
#-----------------------------------------------------------------------------------------

C = [c.id for c in initial_conf]
target_car = :X

S = 6  # board size
T = 50 # Max time steps

C2 = []
for c in initial_conf
    if c.length == 2
        push!(C2, c.id)
    end
end


#-----------------------------------------------------------------------------------------
# Variables
#-----------------------------------------------------------------------------------------

# board
@variable(model, b[t in 1:T, i in 1:S, j in 1:S], Bin)

# cars
@variable(model, cars[t in 1:T, c in C, i in 1:S], Bin)

# pin: starting tile of car, more left tile or up tile
@variable(model, pin[t in 1:T, c in C, i in 1:S-1], Bin)

# models exit condition: will be set to 1 when the target car reaches the exit
@variable(model, exit[t in 1:T], Bin)

# Used to indicate which car moves at each time step
@variable(model, turn[t in 2:T, c in C], Bin)

# Used to model car movement between two consecutive time steps
@variable(model, z[t in 1:T, c in C, i in 1:S], Bin)


if model_option == "model1"
    # Used to quantify the real number of moves: each move is a different piece moving
    @variable(model, nmoves[t in 3:T, c in C], Bin)
end

if model_option == "model1" || model_option == "model0"
    @variable(model, exit_mask[t in 1:T], Bin)
    @variable(model, exit_mask_not[t in 1:T], Bin)
elseif model_option == "model2"
    # TODO: define only for cars of length 2
    mask_symbols = Symbol[:forward, :backward, :or, :and1, :and2, :mask, :conditional_mask]
    @variable(model, mask[s in mask_symbols, t in 1:T, c in C2, i in 1:S], Bin)
    # used to calculate the difference between mask[:or] and cars
    @variable(model, mask_diff[t in 1:T, c in C2, i in 1:S], Int)
end

#-----------------------------------------------------------------------------------------
# Constraints
#-----------------------------------------------------------------------------------------


# Constraint: car can only start at one pin position
for t in 1:T, c in C
    @constraint(model, sum(pin[t, c, j] for j in 1:S-1) == 1)
end


# Constraint: initial position of cars (at time t=1)
for car in initial_conf
    len = car.length
    is_vert = car.is_vertical
    x = car.initial_x
    y = car.initial_y

    if is_vert
        for j in x:(x+len-1)
            @constraint(model, cars[1, car.id, j] == 1)
        end
        @constraint(model, pin[1, car.id, x] == 1)
    else
        for i in y:(y+len-1)
            @constraint(model, cars[1, car.id, i] == 1)
        end
        @constraint(model, pin[1, car.id, y] == 1)
    end
end

# Linking of cars to board: the car variable is treated as if it were an additional dimension of the board
# First, we build a mapping of rows/columns to cars: which cars are in which rows/columns

cars_h = Dict{Int8,Vector{Symbol}}()
cars_v = Dict{Int8,Vector{Symbol}}()
for car in initial_conf
    x = car.initial_x
    y = car.initial_y
    if car.is_vertical
        if !haskey(cars_v, y)
            cars_v[y] = Symbol[]
        end
        push!(cars_v[y], car.id)
    else
        if !haskey(cars_h, x)
            cars_h[x] = Symbol[]
        end
        push!(cars_h[x], car.id)
    end
end

if model_option == "model2"
    # Constraints: defining a mask for car movements
    for t in 1:T
        for c in C2
            # Constraints: forward -> elements starting at pin and moving forward set to 1
            @constraint(model, mask[:forward, t, c, 1] == pin[t, c, 1])
            @constraint(model, mask[:forward, t, c, S] == mask[:forward, t, c, S-1])
            for i in 2:S-1
                @constraint(model, mask[:forward, t, c, i] == pin[t, c, i] + mask[:forward, t, c, i-1])
            end
            # Constraint: backward -> elements starting at pin and moving backward set to 1
            @constraint(model, mask[:backward, t, c, S-1] == pin[t, c, S-1])
            @constraint(model, mask[:backward, t, c, S] == mask[:backward, t, c, S-1])
            for i in S-2:-1:1
                @constraint(model, mask[:backward, t, c, i] == pin[t, c, i] + mask[:backward, t, c, i+1])
            end

            #Constraint: and1 OR and2
            for i in 1:S
                @constraints(model, begin
                    mask[:and1, t, c, i] <= mask[:or, t, c, i]
                    mask[:and2, t, c, i] <= mask[:or, t, c, i]
                    mask[:or, t, c, i] <= mask[:and1, t, c, i] + mask[:and2, t, c, i]
                end)
            end

            # Constraint: mask difference
            for i in 1:S
                @constraint(model, -1 <= mask_diff[t, c, i] <= 1)
            end
        end
    end

    for t in 2:T
        for c in C2
            for i in 1:S
                # Constraint: forward[t-1] AND backward[t]
                @constraints(model, begin
                    mask[:and1, t, c, i] <= mask[:forward, t-1, c, i]
                    mask[:and1, t, c, i] <= mask[:backward, t, c, i]
                    mask[:and1, t, c, i] >= mask[:forward, t-1, c, i] + mask[:backward, t, c, i] - 1
                end)

                # Constraint: forward[t] AND backward[t-1]
                @constraints(model, begin
                    mask[:and2, t, c, i] <= mask[:forward, t, c, i]
                    mask[:and2, t, c, i] <= mask[:backward, t-1, c, i]
                    mask[:and2, t, c, i] >= mask[:forward, t, c, i] + mask[:backward, t-1, c, i] - 1
                end)

                @constraint(model, mask_diff[t, c, i] == mask[:or, t, c, i] - cars[t, c, i])

                # mask[:mask] = 1 if diff > 0, 0 otherwise (since mask is binary)
                @constraint(model, mask[:mask, t, c, i] <= mask_diff[t, c, i] + 1)  # When diff=-1, mask<=0, so mask=0
                @constraint(model, mask[:mask, t, c, i] >= mask_diff[t, c, i])      # When diff=1, mask>=1, so mask=1; when diff=0, mask>=0

                # Constraint: conditional_mask = mask if turn[t,c]=1, else 0
                M = 1
                @constraint(model, mask[:conditional_mask, t, c, i] <= M * turn[t, c])
                @constraint(model, mask[:conditional_mask, t, c, i] <= mask[:mask, t, c, i])
                @constraint(model, mask[:conditional_mask, t, c, i] >= mask[:mask, t, c, i] - M * (1 - turn[t, c]))
            end
        end
    end
end

# Constraint: linking of cars to the board using the mapping defined above
for t in 1:T
    for row in 1:S
        for col in 1:S
            sum_cars = 0
            if haskey(cars_h, row)
                for c in cars_h[row]
                    sum_cars += cars[t, c, col]
                    if model_option == "model2" && c in C2
                        sum_cars += mask[:conditional_mask, t, c, col]  # only count the car if it is moving
                    end
                end
            end
            if haskey(cars_v, col)
                for c in cars_v[col]
                    sum_cars += cars[t, c, row]
                    if model_option == "model2" && c in C2
                        sum_cars += mask[:conditional_mask, t, c, row]  # only count the car if it is moving
                    end
                end
            end
            @constraint(model, b[t, row, col] == sum_cars)
        end
    end
end


# Constraint: no overlapping
for i in 1:S, j in 1:S, t in 1:T
    @constraint(model, b[t, i, j] <= 1)
end

# Constraint: the tiles making up a car must be contiguous
for t in 2:T
    for car in initial_conf
        len = car.length
        for j in 1:S
            @constraint(model, cars[t, car.id, j] ==
                                                        sum(pin[t, car.id, j-k] for k in 0:(len-1) if j - k >= 1 && j - k <= S - 1))
        end
        # Constraint: the number of tiles occupied by a car must be equal to its length and
        # remain constant over time
        @constraint(model, sum(cars[t, car.id, j] for j in 1:S) == len)
    end
end


# Constraint: maximum one car moves per time step
for t in 2:T
    if model == "model1" || model == "model0"
        @constraint(model, sum(turn[t, c] for c in C) <= exit_mask_not[t])
    else
        @constraint(model, sum(turn[t, c] for c in C) <= 1)
    end
end


# The z variable represents a logical OR between the car positions at time t and t-1
# see: https://jump.dev/JuMP.jl/stable/tutorials/linear/tips_and_tricks/#Boolean-operators
for t in 2:T
    for car in initial_conf
        is_vert = car.is_vertical
        len = car.length
        for j in 1:S
            # Constraint: the z variable is the OR between cars[t-1, car.id, j] and cars[t, car.id, j]
            @constraints(model, begin
                cars[t-1, car.id, j] <= z[t, car.id, j]
                cars[t, car.id, j] <= z[t, car.id, j]
                z[t, car.id, j] <= cars[t-1, car.id, j] + cars[t, car.id, j]
            end)
        end
        # Constraint: cars of length 2 can move at most 1 step, cars of length 3 don't have any restriction.
        # This restriction is in place to prevent "tunneling" where a car of length 2 could move through another car
        if model_option == "model0"
            @constraint(model, sum(z[t, car.id, i] for i in 1:S) <= len + turn[t, car.id])
        elseif model_option == "model2"
            @constraint(model, sum(z[t, car.id, i] for i in 1:S) <= len + turn[t, car.id]*len)
        elseif model_option == "model1"
            @constraint(model, sum(z[t, car.id, i] for i in 1:S) <= len + turn[t, car.id]*(2*len - 3))
        end
    end
end

# Constraint: the exit condition is modeled as an AND condition on car X' tiles at the exit position
for t in 1:T
    # AND constraint b[t, target_car, 5] AND b[t, target_car, 6]
    @constraints(model, begin
        exit[t] <= cars[t, target_car, 5]
        exit[t] <= cars[t, target_car, 6]
        exit[t] >= cars[t, target_car, 5] + cars[t, target_car, 6] - 1
    end)
end

# Constraint: Car X must be at the exit position at exactly one time step
@constraint(model, sum(exit[t] for t in 1:T) == 1)


if model_option == "model1" || model_option == "model0"
    @constraint(model, exit_mask[1] == 0)
    @constraint(model, exit_mask_not[1] == 1)
    for t in 2:T
        @constraint(model, exit_mask[t] == exit_mask[t-1] + exit[t-1])
        @constraint(model, exit_mask_not[t] == 1 - exit_mask[t])
    end
end

if model_option == "model1"
    # Constraint: nmoves[t,c] = turn[t,c] OR turn[t-1, c]
    for t in 3:T
        for c in C
            @constraints(model, begin
                turn[t, c] <= nmoves[t, c]
                turn[t-1, c] <= nmoves[t, c]
                nmoves[t, c] <= turn[t, c] + turn[t-1, c]
            end)
        end
    end
end

#-----------------------------------------------------------------------------------------
# Objective
#-----------------------------------------------------------------------------------------


if model_option == "model1"
    @objective(model, Min, sum(nmoves[t, c] for t in 3:T, c in C))
elseif model_option == "model2" || model_option == "model0"
    @objective(model, Min, sum(t * exit[t] for t in 1:T))
end


#-----------------------------------------------------------------------------------------
# Solving
#-----------------------------------------------------------------------------------------


optimize!(model)

print(solution_summary(model))

if termination_status(model) == MOI.OPTIMAL
    movements = get_solution_sequence(model, T, S, C)
    println("Solution movements: ", movements)
end