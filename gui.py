import sys
from PyQt5.QtWidgets import QApplication, QInputDialog, QMainWindow
from collections import deque
from datetime import datetime, timedelta


def _make_hbox(*widgets):
    """Returns an QHBoxLayout with the given widgets."""
    hbox = QHBoxLayout()
    for widget in widgets:
        hbox.addWidget(widget)
    return hbox

def _show_error_message(parent, error_message):
    """Displays a QErrorMessage with the given error message."""
    error_message = QErrorMessage(parent)
    error_message.ShowMessage(error_message)


class ConnectDialog(QtGui.QWidget):
    """The server connection dialog upon startup."""

    def __init__(self):
        super(ConnectDialog, self).__init__()

        self._output_filename = None
        self._show_ui()

    def _show_file_dialog(self):
        self._output_filename = QFileDialog.getOpenFileName(self, 'Choose output file')

    def _show_ui(self):
        vbox = QtGui.QVBoxLayout()

        # Add the server text field.
        server_label = QLabel('Server')
        self._server_edit = QLineEdit()
        vbox.addLayout(_make_hbox(server_label, self._server_edit))

        # Add the polling rate text field.
        poll_label = QLabel('Seconds/poll')
        self._poll_slider = QSlider()
        self._poll_slider.setRange(5, 60)
        self._poll_slider.setTickInterval(1)
        vbox.addLayout(_make_hbox(poll_label, self._poll_slider))

        # Add the output file chooser.
        output_label = QLabel('Ouptut')
        self._output_edit = QLineEdit()
        vbox.addLayout(_make_hbox(output_label, self._output_edit))

        vbox.addStretch(1)

        # Add the Connect and Quit buttons.
        self._connect_button = QtGui.QPushButton("Connect")
        self._quit_button = QtGui.QPushButton("Quit")
        hbox = QHBoxLayout()
        hbox.addStretch(1)
        hbox.addWidget(self._connect_button)
        hbox.addWidget(self._quit_button)
        vbox.addLayout(hbox)

        # Configure this window.
        self.setLayout(vbox)
        self.setGeometry(300, 300, 300, 150)
        self.setWindowTitle('Connect to Server')
        self.show()

    def _validate():
        # Validate the server address.
        server_parts = server_label.text().strip().split(':')
        if len(parts) != 2:
            _show_error_message(self, "Server must have form [address]:[port]")
            return
        server_address, server_port = server_parts

        poll_length = self._poll_slider.value()

        # Validate the output filename.
        if self._output_filename == None:
            _show_error_message(self, "Must choose an output file")
            return
        elif os.path.isdir(self._output_filename):
            _show_error_message(self, "Cannot choose a directory")
            return

        # TODO: Move on.


class PlayerRow:
    def _empty_label(self):
        return QLabel("-")

    def __init__(self, player_name):
        self._player_name = player_name
        self._use_checkbox = QCheckBox(self._player_name)

        # Labels for the statistics.
        self._total_label = self._empty_label()
        self._avg_label = self._empty_label()
        self._stddev_label = self._empty_label()
        self._new_label = self._empty_label()

        # Labels for the player ranks.
        self._new_rank_label = self._empty_label()
        self._stddev_rank_label = self._empty_label()
        self._combined_rank_label = self._empty_label()

    def update_stats(self, stats):
        """Updates the statistics for this player."""
        self._total_label.setText(stats.total())
        self._avg_label.setText(stats.avg())
        self._stddev_label.setText(stats.std_dev())
        self._new_label.setText(stats.new())

    def _get_rank_text(self, rank):
        # Create text.
        if rank == 1:
            text = "1<sup>st</sup>"
        elif rank == 2:
            text = "2<sup>nd</sup>"
        elif rank == 3:
            text = "3<sup>rd</sup>"
        else:
            text = "%s<sup>th</sup>" % rank
        # Color text.
        if rank == 1:
            text = "<font color=\"green\">%s</font>" % text

        return text

    def update_poll(self, new_rank, stddev_rank, combined_rank):
        """Updates the ranks for this player."""
        self._new_rank_label.setText(self._get_rank_text(new_rank))
        self._stddev_rank_label.setText(self._get_rank_text(stddev_rank))
        self._combined_rank_label.setText(self._get_rank_text(combined_rank))

    def add_to_row(self, row, grid):
        """Adds this player to the given grid at the given row."""
        for column, widget in enumerate((
                self._use_checkbox,
                self._total_label,
                self._avg_label,
                self._stddev_label,
                self._new_label,
                self._new_rank_label,
                self._stddev_rank_label,
                self._combined_rank_label)):
            grid.addWidget(widget, row, column)


ObservedPlayer = namedtuple('ObservedPlayer', ['name', 'deque_time'])

class ServerMonitor(QMainWindow):
    # Enum value for updating the Monitor instance.
    _UPDATE_MONITOR = 'update_monitor'
    # Enum value for updating the file containing the best player to spectate.
    _UPDATE_SPEC = 'update_spec'

    def __init__(self, server_address):
        super(ServerMonitor, self).__init__()

        self._server_address = server_address
        self._show_ui()

        self._obs_player_queue = deque()
        self._next_update_monitor_time = None
        self._next_update_spec_time = None
        self._next_update_timer = None

    def _get_next_action(self):
        """Returns the next action that the update thread should perform."""
        if self._next_update_monitor_time and self._next_update_spec_time:
            # Return the time that is closer in the future.
            if self._next_update_monitor_time < self._next_update_spec_time:
                return ServerMonitor._UPDATE_MONITOR
            else:
                return ServerMonitor._UPDATE_SPEC
        elif self._next_update_monitor_time:
            return ServerMonitor._UPDATE_MONITOR
        elif self._next_update_spec_time:
            return ServerMonitor._UPDATE_SPEC
        else:
            return None

    def _get_seconds_until_next_action(self, action, now=None):
        """Returns the time in seconds until running the given action.

        This method returns None if there is no action."""
        if not action:
            return None

        if now is None:
            now = datetime.utcnow()
        if action == ServerMonitor._UPDATE_MONITOR:
            # Return the time until we should update the monitor.
            return (self._next_update_monitor_time - now).total_seconds()
        elif action == ServerMonitor._UPDATE_SPEC:
            # Return the time until we should update the best spectator.
            return (self._next_update_spec_time - now).total_seconds()
        else:
            raise ValueError('Invalid action: %s' % action)

    def _schedule_next_update_timer(self, seconds_until):
        self._next_update_timer = Timer(seconds_until, self._update)

    def _update_spec_file(self):
        """Writes the best player to spectate to the file."""
        if not self._obs_player_queue:
            return

        # Write the player name to the file.
        obs_player = self._obs_player_queue.popleft()
        with open(self._output_filename, 'w') as f:
            f.write('spec_player "%s"' % player_name)
        # Update the next time at which this method should be run.
        if self._obs_player_queue:
            self._next_update_spec_time = self._obs_player_queue[0].deque_time
        else:
            self._next_update_spec_time = None

    def _update(self):
        """The method that the update thread executes."""
        while True:
            next_action = self._get_next_action()
            if not next_action:
                # No next action to execute, so exit.
                break
            seconds_until_next_action = self._get_time_until_next_action()
            if seconds_until_next_action > 0:
                # Run this action at the given time in the future.
                self._schedule_next_update_timer(seconds_until_next_action)
                break

            # Run the next action now.
            if next_action == ServerMontior._UPDATE_MONITOR:
                # TODO
                pass
            elif next_action == ServerMonitor._UPDATE_SPEC:
                self._update_spec_file()

    def _show_ui(self):
        self._weight_slider = QSlider()
        self._weight_slider.setRange(0, 100)
        self._weight_slider.setTickInterval(25)

    def _populate_grid(self):
        self._grid = QGridLayout()
        self.setLayout(grid)


def main():
    app = QApplication(sys.argv)
    server_address, success = QInputDialog.getText(
            None, 'Connect to server', 'Enter server address:')
    if success:
        print 'server_address=%s' % server_address

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()

