import curses
from curses import textpad
import sys

def main(stdscr):
    # Initialize curses
    curses.curs_set(False) 
    stdscr.clear()  # Clear the screen

    # Calculate window dimensions
    height, width = stdscr.getmaxyx()
    col_width = width // 2

    # Create left and right windows
    right_win = curses.newwin(height-3, col_width, 0, col_width)
    right_win.scrollok(True)
    left_win = curses.newwin(height-3, col_width-1, 0, 0)
    left_win.scrollok(True)

    # Draw lines to separate the windows
    stdscr.vline(0, col_width-1, curses.ACS_VLINE, height-3)
    stdscr.hline(height-3, 0, curses.ACS_HLINE, width)
    stdscr.refresh()

    # Create prompt and input windows
    prompt_win = curses.newwin(1, 3, height-2, 0)
    prompt_win.move(0,1)
    prompt_win.addstr(">", curses.A_BOLD)
    prompt_win.refresh()
    input_win = curses.newwin(1, col_width-4, height-2, 3)

    # Main loop for input
    left_win.move(0,0)
    right_win.move(0,0)
    
    while True:
        input_win.clear()
        input_win.move(0,0)
        left_win.refresh()
        right_win.refresh()

        # get input
        box = textpad.Textbox(input_win)
        curses.curs_set(True) # Cursor while editing
        def validate_key(ch): 
            if ch == curses.ascii.DEL:      # fix backspace on MacOS
                return curses.KEY_BACKSPACE 
            return ch
        box.edit(validate_key)
        curses.curs_set(False) # No cursor while refreshing
        msg = '\n' + box.gather()

        # Echo input to the left window
        left_win.addstr(msg)
        # Convert to uppercase and display in the right window
        right_win.addstr(msg.upper())


# Run the application
if __name__ == "__main__":
    ss = [opt for opt in sys.argv if opt == '--splitscreen' or opt == '-X']
    if len(ss) > 0:
        curses.wrapper(main)
    else:
        print("NO curses")
