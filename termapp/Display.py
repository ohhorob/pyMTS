import signal

from blessed import Terminal

from termapp.Box import BoxStyle


class Display():
    def __init__(self, terminal):
        self._t = terminal
        self._keyhandlers = {}
        self._widgets = []
        self._digit_buffer = u''
        self._command_buffer = u''
        signal.signal(signal.SIGWINCH, self.on_resize)
        self.on_resize()
        self._redraw = False
        self._commands = {}
        self._boxes = {}

    def add_command(self, command, callback):
        self._commands[command] = callback

    def add_key(self, inputkey, callback):
        self._keyhandlers[repr(inputkey)] = callback

    def echo(self, text):
        self._t.stream.write(u'{}'.format(text))
        self._t.stream.flush()

    def on_resize(self, *args):
        # Get new geometery
        self.echo(self._t.clear)
        with self._t.location(y=4, x=-10 + (self._t.width / 2)):
            self.echo('height={t.height}, width={t.width}\r'.format(t=self._t))
        self._redraw = True

    def start(self):
        with self._t.hidden_cursor(), self._t.cbreak(), self._t.fullscreen():
            self._t.location(y=2)
            self.echo(self._t.center(self._t.bold('Replay')))
            self._redraw = True
            while True:
                if self._redraw:
                    self.status()
                    self._redraw = False
                terminal_input = self._t.inkey(timeout=2)

                if repr(terminal_input) in self._keyhandlers:
                    self._keyhandlers[repr(terminal_input)]()
                    continue

                if terminal_input == '' and terminal_input.code is None:
                    continue
                    # with _t.location(2, 35):
                    #     print('Input timeout.')
                elif terminal_input.code is not None:
                    with self._t.location(2, 30):
                        print('Name={} Code={}\n'.format(terminal_input.name, terminal_input.code))
                        if terminal_input.code == 265:  # F1
                            print('Quitting.')
                            break
                    continue

                if terminal_input == '>':
                    with self._t.location(20, 5):
                        self.echo('type command + enter; esc to cancel ')
                        cmd = self.readline(self._t)
                    self.echo(cmd)
                    if cmd in self._commands:
                        self._commands[cmd]()

                if terminal_input == 'c':
                    for bg in range(self._t.number_of_colors):
                        self.echo('\n' + self._t.on_color(bg))
                        for idx in range(self._t.number_of_colors):
                            self.echo(self._t.color(idx)('Color {0}'.format(idx)))

                if terminal_input == 's':
                    self.echo('Send')
                    # send_packet()
                    self.status()
                    continue

                char = ord(terminal_input)
                if ord('0') <= char <= ord('9'):
                    self.accumulate_digit(terminal_input)

    def status(self):
        # Render a simple status bar
        with self._t.location(0, self._t.height - 1):
            self.echo(self._t.bright_red_on_bright_yellow(
                self._t.center(
                    '{} x {}'.format(self._t.width, self._t.height), 20)
                )
            )
            self.echo(self._t.red_on_yellow(self._t.center(self._digit_buffer, 30)))
        # self.echo(self._t.move(0, 0) + u'\u256D')
        self.box(0, 0, self._t.width - 1, self._t.height - 2, style=BoxStyle['double'], colour=self._t.bright_yellow)

    def menu(self):
        # List current commands
        # draw the box
        self.box()

    def box(self, top, left, width, height, style='plain', colour=None):
        """

        :param colour:
        :param height: height width
        :param width: column count
        :param left: left column number
        :param top: top line number
        :type style: Box
        """
        if colour is not None:
            self.echo(colour)
        with self._t.location(left, top):
            self.echo(colour)
            c0 = left
            c1 = left + width - 1
            # TL -- NORTH -- TR
            self.echo(style.TL + (width - 2) * style.T + style.TR)
            for line in range(top + 1, top + height):
                self.echo(self._t.move(line, c0) + style.L + self._t.move(line, c1) + style.R)
            self.echo(self._t.move(top + height, c0) + style.BL + (width - 2) * style.B + style.BR)
            self.echo(self._t.normal)

    def readline(self, width=20):
        """A rudimentary readline implementation."""
        text = u''
        self.echo('> ')
        while True:
            inp = self._t.inkey()
            if inp.code == self._t.KEY_ENTER:
                break
            elif inp.code == self._t.KEY_ESCAPE or inp == chr(3):
                text = None
                break
            elif not inp.is_sequence and len(text) < width:
                text += inp
                self.echo(inp)
            elif inp.code in (self._t.KEY_BACKSPACE, self._t.KEY_DELETE):
                text = text[:-1]
                self.echo(u'\b \b')
        width = len(text) + 2
        self.echo(u'\b' * width)
        self.echo(u' ' * width)
        return text

    def accumulate_digit(self, digit):
        self._digit_buffer += digit
        with self._t.location(self._t.width - 20, self._t.height - 2):
            print('[ ' + self._t.bold(self._digit_buffer + '_ ]'))