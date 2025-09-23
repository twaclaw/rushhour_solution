using JSON
using DataFrames, CSV
using JuMP

struct Car
    id::Symbol
    length::Int
    is_vertical::Bool
    initial_x::Int
    initial_y::Int
end

const lengths = Dict(
    :X => 2,  # red
    :A => 2,  # light green
    :B => 2,  # orange
    :C => 2,  # light blue
    :D => 2,  # pink
    :E => 2,  # purple
    :F => 2,  # dark green
    :G => 2,  # gray
    :H => 2,  # beige
    :I => 2, # light yellow
    :J => 2, # brown
    :K => 2, # olive
    :O => 3, # dark yellow
    :P => 3, # light purple
    :Q => 3, # blue
    :R => 3, # green
)

function load_game(filepath::String)
    json_string = read(filepath, String)
    initial_state_strings = JSON.parse(json_string)["initial_state"]
    cars_data = Car[]

    for car_str in initial_state_strings
        if length(car_str) != 4
            @warn "Skipping invalid car string: $car_str"
            continue
        end

        symbol_char = car_str[1]
        orientation_char = car_str[2]
        x_char = car_str[3]
        y_char = car_str[4]

        id = Symbol(symbol_char)
        is_vertical = (orientation_char == 'V')

        # why does Julia have 1-based indexing 🤷‍♂️
        initial_x = parse(Int, x_char) + 1
        initial_y = parse(Int, y_char) + 1

        #     # Look up the length from the dictionary
        if !haskey(lengths, id)
            @error "Length for piece '$id' not found in PIECE_LENGTHS dictionary."
            continue
        end
        len = lengths[id]

        push!(cars_data, Car(id, len, is_vertical, initial_x, initial_y))
    end

    return cars_data
end


function get_solution_sequence(model, T, SIZE, C)
    """
    Return the sequence of movements as an array of strings, e.g. ["X+1", "A-1", ...]
    """
    movements = String[]
    car_positions = Dict{Symbol, Int}()

    pin_values = value.(model[:pin])
    turn_values = value.(model[:turn])
    exit_values = value.(model[:exit])

    # Initialize positions at t=1
    for c in C
        for i in 1:SIZE-1
            if pin_values[1, c, i] ≈ 1.0
                car_positions[c] = i
                break
            end
        end
    end

    for t in 2:T
        moving_car = nothing
        for c in C
            if turn_values[t, c] ≈ 1.0
                moving_car = c
                break
            end
        end

        if moving_car !== nothing
            current_position = nothing
            for i in 1:SIZE-1
                if pin_values[t, moving_car, i] ≈ 1.0
                    current_position = i
                    break
                end
            end

            if current_position !== nothing && haskey(car_positions, moving_car)
                previous_position = car_positions[moving_car]
                difference = current_position - previous_position

                if difference != 0
                    sign = difference >= 0 ? "+" : ""
                    movement_str = string(moving_car) * sign * string(difference)
                    push!(movements, movement_str)
                end

                car_positions[moving_car] = current_position
            end
        end

        # Stop if the target car has exited
        if exit_values[t] ≈ 1.0
            println("\nPuzzle solved at time step $t - stopping movement generation")
            break
        end
    end

    return movements
end

function save_results(model, T, SIZE, C)
    # for debugging
    open("results.txt", "w") do io
        for v in all_variables(model)
            println(io, string(name(v), " = ", value(v)))
        end
    end

    b_values = value.(model[:b])
    df = DataFrame(t = Int[], i = Int[], j = Int[], value = Float64[])
    for t in 1:T
        for i in 1:SIZE
            for j in 1:SIZE
                push!(df, (t, i, j, b_values[t, i, j]), promote=true)
            end
        end
    end
    CSV.write("b_variable.csv", df)

    pin_values = value.(model[:pin])
    df = DataFrame(t = Int[], c = Int[], i = Int[], value = Float64[])
    for t in 1:T
        for c in C
            for i in 1:SIZE-1
                push!(df, (t, c, i, pin_values[t, c, i]), promote=true)
            end
        end
    end
    CSV.write("pin_variable.csv", df)

    turn_values = value.(model[:turn])
    df = DataFrame(t = Int[], c = Int[], value = Float64[])
    for t in 2:T
        for c in C
            push!(df, (t, c, turn_values[t, c]), promote=true)
        end
    end
    CSV.write("turn_variable.csv", df)

    z_values = value.(model[:z])
    df = DataFrame(t = Int[], c = Int[], i = Int[], value = Float64[])
    for t in 2:T
        for c in C
            for i in 1:SIZE
                push!(df, (t, c, i, z_values[t, c, i]), promote=true)
            end
        end
    end
    CSV.write("z_variable.csv", df)

    exit_values = value.(model[:exit])
    df = DataFrame(t = Int[], value = Float64[])
    for t in 1:T
        push!(df, (t, exit_values[t]))
    end
    CSV.write("exit_variable.csv", df)
end