def manhattan_distance(xy_tuple_a, xy_tuple_b):
    return abs(xy_tuple_a[0] - xy_tuple_b[0]) + abs(xy_tuple_a[1] - xy_tuple_b[1])

def chebyshev_distance(xy_tuple_a, xy_tuple_b):
    return max(abs(xy_tuple_a[0] - xy_tuple_b[0]), abs(xy_tuple_a[1] - xy_tuple_b[1]))

