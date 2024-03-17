import curses
from curses import textpad
import sys

# special case to trim '>' from the output
def remove_prompts_from_tail(lines):
    for i in reversed(range(len(lines))):
        str = lines[i].strip()
        if str == '':
            continue
        elif str == '>':
            lines[i] = ''
            return

class SplitScreen:
    def __init__(self, stdscr):
        # Initialize curses
        curses.curs_set(False) 
        self.stdscr = stdscr
        stdscr.clear()  # Clear the screen

        # Calculate window dimensions
        self.height, self.width = stdscr.getmaxyx()
        self.col_width = self.width // 2

        # Create left and right windows
        self.right_win = curses.newwin(self.height-3, self.col_width, 0, self.col_width)
        self.right_win.scrollok(True)
        self.right_win.move(0,0)

        self.left_win = curses.newwin(self.height-3, self.col_width-1, 0, 0)
        self.left_win.scrollok(True)
        self.left_win.move(0,0)

        # Draw lines to separate the windows
        stdscr.vline(0, self.col_width-1, curses.ACS_VLINE, self.height-3)
        stdscr.hline(self.height-3, 0, curses.ACS_HLINE, self.width)
        stdscr.refresh()

        # Create prompt and input windows
        self.prompt_win = curses.newwin(1, 3, self.height-2, 0)
        self.prompt_win.move(0,1)
        self.prompt_win.addstr(">", curses.A_BOLD)
        self.prompt_win.refresh()
        self.input_win = curses.newwin(1, self.col_width-4, self.height-2, 3)

        # create arrays for scrolling
        self.left_lines = []
        self.right_lines = []
        self.scroll_pos = 0   # scroll_pos number of lines we've scrolled back

    def get_command(self):
        self.input_win.clear()
        self.input_win.move(0,0)

        box = textpad.Textbox(self.input_win)
        curses.curs_set(True) # Cursor while editing
        def validate_key(ch): 
            if ch == curses.ascii.DEL:      # fix backspace on MacOS
                return curses.KEY_BACKSPACE
            elif ch == curses.KEY_UP:
                self.scroll_up()
            elif ch == curses.KEY_DOWN:
                self.scroll_down()
            return ch
        box.edit(validate_key)
        curses.curs_set(False) # No cursor while refreshing
        return box.gather()

    def refresh_window(self, win, lines):
        height, _ = win.getmaxyx()
        if len(lines) > height:
            prefix = len(lines) - height
            start = max(0, min(prefix-self.scroll_pos, prefix))
            end = start + height
            lines = lines[start:end]
        win.erase()
        for i in range(0, len(lines)):
            win.addstr(i, 0, lines[i])
        win.refresh()

    def trim_space_from_tails(self):
        if len(self.left_lines) >= 2 and len(self.right_lines) >= 2:
            if '' == self.left_lines[-1].strip() and \
               '' == self.left_lines[-2].strip() and \
               '' == self.right_lines[-1].strip() and \
               '' == self.right_lines[-2].strip():
                self.left_lines.pop()
                self.right_lines.pop()

    def output_text(self, left_msg, right_msg):
        left_rets = left_msg.count('\n')
        right_rets = right_msg.count('\n')
        added_rets = abs(left_rets - right_rets)*'\n'
        if left_rets < right_rets:
            left_msg = left_msg + added_rets
        else:
            right_msg = right_msg + added_rets

        # massive special case to avoid proliferation of > prompts
        if left_rets <= 1 and right_rets <= 1 and \
           left_msg.startswith("> ") and right_msg.startswith("> "):
            remove_prompts_from_tail(self.left_lines)
            remove_prompts_from_tail(self.right_lines)
            self.trim_space_from_tails()
        self.left_lines = self.left_lines + left_msg.split('\n')
        self.right_lines = self.right_lines + right_msg.split('\n')

        self.refresh_window(self.left_win, self.left_lines)
        self.refresh_window(self.right_win, self.right_lines)

    def scroll_up(self):
        if self.scroll_pos >= len(self.left_lines)-1:
            return
        self.scroll_pos = min(len(self.left_lines)-1, self.scroll_pos+1)
        self.refresh_window(self.left_win, self.left_lines)
        self.refresh_window(self.right_win, self.right_lines)

    def scroll_down(self):
        if self.scroll_pos <= 0:
            return
        self.scroll_pos = max(0, self.scroll_pos-1)
        self.refresh_window(self.left_win, self.left_lines)
        self.refresh_window(self.right_win, self.right_lines)

##
## TEST
##
def main(stdscr):
    ss = SplitScreen(stdscr)
    while True:
        msg = ss.get_command()
        ss.output_text(msg, msg)

# Run the application
if __name__ == "__main__":
    ss = [opt for opt in sys.argv if opt == '--splitscreen' or opt == '-X']
    if len(ss) > 0:
        curses.wrapper(main)
    else:
        print("NO curses")
