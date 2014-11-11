def render_grid(point_formatter, size):
    """Render a board-shaped grid as a list of strings.

    point_formatter -- function (row, col) -> string of length 2.

    Returns a list of strings.

    """
    column_header_string = " ".join("%02d" % i for i in xrange(size))
    result = []
    if size > 9:
        rowstart = "%2d "
        padding = " "
    else:
        rowstart = "%d "
        padding = ""
    for row in range(size-1, -1, -1):
        result.append(rowstart % (row) +
                      " ".join(point_formatter(row, col)
                      for col in range(size)))
    result.append(padding + "  " + column_header_string)
    return result

_point_strings = {
    None  : "  ",
    'b'   : " #",
    'w'   : " o",
    }

def render_board(board):
    """Render a gomill Board in ascii.

    Returns a string without final newline.

    """
    def format_pt(row, col):
        return _point_strings.get(board.get(row, col), " ?")
    return "\n".join(render_grid(format_pt, board.side))
