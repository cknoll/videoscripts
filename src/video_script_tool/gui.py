import sys
import os
import glob
import threading
import time
import contextlib
from collections import defaultdict
import time


from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QLabel,
    QTextBrowser,
    QVBoxLayout,
    QPushButton,
    QWidget,
    QTextEdit,
    QGridLayout,
    QAction,
    QMessageBox,
    QDialog,
    QTableWidget,
    QTableWidgetItem,
    QHBoxLayout,
)
from PyQt5.QtGui import QPixmap, QPainter, QColor, QKeySequence, QTextCursor
from PyQt5.QtCore import Qt
import markdown
import pyaudio
import wave

from .util import bred, PyaudioStdoutWrapper


from ipydex import IPS

pjoin = os.path.join

# to mute logging noise for pyaudio


@contextlib.contextmanager
def suppress_output():
    with open(os.devnull, "w") as fnull:
        with contextlib.redirect_stdout(fnull), contextlib.redirect_stderr(fnull):
            yield


class ColorCircle(QWidget):
    def __init__(self, color):
        super().__init__()
        self.color = color

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(self.color))
        painter.drawEllipse(self.rect())

    def setColor(self, color):
        self.color = color
        self.update()


class FocussingTextEdit(QTextEdit):
    def showEvent(self, event):
        super().showEvent(event)
        self.setFocus()


class ImageTextAudioTool(QMainWindow):
    def __init__(self, args):
        super().__init__()
        self.project_dir = args.project_dir
        self.audio_path = pjoin(self.project_dir, "audio")
        self.edit_mode = False
        os.makedirs(self.audio_path, exist_ok=True)
        self.current_index = 0
        self.is_recording = False
        self.audio_frames = None
        self.cursor_positions = defaultdict(lambda: 0)

        # for shortcuts and help dialog
        self.anonymous_actions = []
        self.shortcuts: list[tuple[str]] = []

        # split and join md snippets by this string
        self.md_snippet_separator = "\n---\n"

        self.src_fname = "all_texts.md"

        self.load_data()

        # setup audio (without logging noise)
        with PyaudioStdoutWrapper() as audio:
            self.audio = audio
        self.stream = None

        self.initUI()

    def load_data(self):

        pattern_img = pjoin(self.project_dir, "images", "*.png")
        self.image_files = glob.glob(pattern_img)
        self.image_files.sort()

        # load texts

        txt_fpath = pjoin(self.project_dir, self.src_fname)
        with open(txt_fpath, "r", encoding="utf8") as fp:
            txt_data = fp.read()

        self.md_snippets = txt_data.split(self.md_snippet_separator)

        assert len(self.md_snippets) > 0

        # check if there are texts for every image and vice versa
        minval = min(len(self.image_files), len(self.md_snippets))
        if len(self.md_snippets) != len(self.image_files):
            print(bred("Caution:"))
            print(f"number of text snippets: {len(self.md_snippets)}")
            print(f"number of image files:   {len(self.image_files)}\n")
            print("Skipping the leftover")

            self.md_snippets = self.md_snippets[:minval]
            self.image_files = self.image_files[:minval]

    def initUI(self):
        self.setWindowTitle("Image Text Audio Tool")
        self.setGeometry(600, 100, 1200, 1000)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QGridLayout(central_widget)

        button_area_layout = QVBoxLayout()
        button_area_widget = QWidget()
        button_area_widget.setLayout(button_area_layout)

        self.main_text_browser = QTextBrowser(self)
        self.main_text_browser.setFixedSize(1200, 200)
        layout.addWidget(self.main_text_browser, 0, 0, alignment=Qt.AlignCenter)

        self.main_text_field = FocussingTextEdit(self)
        self.main_text_field.setFixedSize(800, 200)
        layout.addWidget(self.main_text_field, 0, 0, alignment=Qt.AlignCenter)
        self.main_text_field.hide()

        # edit mode button
        self.edit_mode_button = QPushButton("Edit")
        self.edit_mode_button.clicked.connect(self.toggle_edit_mode)
        layout.addWidget(button_area_widget, 0, 1)
        button_area_layout.addWidget(self.edit_mode_button)

        # save button
        self.save_button = QPushButton("Save")
        button_area_layout.addWidget(self.save_button)
        self.save_button.clicked.connect(self.save_edited_content)

        # reload button
        self.reload_button = QPushButton("Reload")
        button_area_layout.addWidget(self.reload_button)
        self.reload_button.clicked.connect(self.reload_content)

        # help button
        self.help_button = QPushButton("Help (H))")
        self.help_button.clicked.connect(self.show_help)
        button_area_layout.addWidget(self.help_button)

        # display information about the image
        self.info_label = QLabel("", self)
        self.info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.info_label, 1, 0)

        # widget to display the image
        self.image_label = QLabel(self)
        self.image_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.image_label, 2, 0, 2, 1, alignment=Qt.AlignCenter)

        # display information about the recording state
        self.recording_symbol = ColorCircle("gray")
        self.recording_symbol.setFixedSize(20, 20)
        button_area_layout.addWidget(self.recording_symbol, alignment=Qt.AlignCenter)

        self.define_shortcuts()

        self.load_content()
        print("init done")

    def define_shortcuts(self):
        self.connect_key_sequence_to_method("H", "show this help dialog", self.show_help)
        self.connect_key_sequence_to_method("R", "start recording", self.start_recording)
        self.connect_key_sequence_to_method("Space", "stop and save recording", self.stop_recording_and_save)
        self.connect_key_sequence_to_method("PgDown", "forward", self.forward1)
        self.connect_key_sequence_to_method("PgUp", "backward", self.backward1)
        self.connect_key_sequence_to_method("Ctrl+PgDown", "forward 10 steps", self.forward10)
        self.connect_key_sequence_to_method("Ctrl+PgUp", "backward 10 steps", self.backward10)
        self.connect_key_sequence_to_method("Ctrl+E", "toggle edit mode", self.toggle_edit_mode)
        self.connect_key_sequence_to_method("Ctrl+S", "save text", self.save_edited_content)
        self.connect_key_sequence_to_method("Ctrl+Q", "quit", self.close)

    def show_help(self):

        table_data = self.shortcuts

        class HelpDialog(QDialog):
            def __init__(self):
                super().__init__()
                self.setWindowTitle("Help")
                # self.setGeometry(100, 100, 200, 600)

                # Create a QVBoxLayout
                layout = QVBoxLayout()

                self.table_widget = QTableWidget(len(table_data), 2)  # 3 rows and 2 columns
                self.table_widget.setHorizontalHeaderLabels(["Keys", "Action"])

                for row, (code, text) in enumerate(table_data):
                    self.table_widget.setItem(row, 0, QTableWidgetItem(code))
                    self.table_widget.setItem(row, 1, QTableWidgetItem(text))

                    # Set the left column (code) to be monospaced font
                    item_code = self.table_widget.item(row, 0)
                    # item_code.setFont(item_code.font().setFamily("Courier New"))

                self.table_widget.resizeColumnsToContents()
                # Add the table widget to the layout
                layout.addWidget(self.table_widget)
                ok_button = QPushButton("OK")
                ok_button.clicked.connect(self.accept)

                button_layout = QHBoxLayout()
                button_layout.addStretch()  # Add stretchable space
                button_layout.addWidget(ok_button)

                # Add the button layout to the main layout
                layout.addLayout(button_layout)

                # Set the layout for the dialog
                self.setLayout(layout)

                # Adjust the size of the dialog to fit the content
                # self.resize(self.table_widget.sizeHint())
                self.adapt_size()

            def adapt_size(self):
                # Get overall size hint
                self.size_hint = self.table_widget.sizeHint()
                # Get specific column and row sizes
                self.total_width = sum(self.table_widget.columnWidth(i) for i in range(self.table_widget.columnCount()))
                self.total_height = sum(self.table_widget.rowHeight(i) for i in range(self.table_widget.rowCount()))
                self.resize(self.total_width + 45, self.total_height + 80)

        help_dialog = HelpDialog()
        help_dialog.exec_()

    def load_content(self):
        image_path = self.image_files[self.current_index]

        # Load image
        pixmap = QPixmap(image_path)
        self.image_label.setPixmap(pixmap.scaled(1200, 1200, Qt.KeepAspectRatio))

        self.render_md_to_html(self.md_snippets[self.current_index])
        self.info_label.setText(f"{self.current_index} {self.get_current_image_basename()}")

    def change_index_by(self, value):
        assert value in (-1, -10, 1, 10)

        self.current_index += value
        if self.current_index >= len(self.image_files):
            self.current_index = len(self.image_files) - 1
        if self.current_index <= 0:
            self.current_index = 0

    def render_md_to_html(self, md_src):

        # render markdown
        html_content = markdown.markdown(md_src)

        style = "font-size: large; text-align:center;"
        outer_html = f'<div style="{style}">{html_content}</div>'
        self.main_text_browser.setHtml(outer_html)

        self.main_text_field.setText(md_src)

    def reload_content(self):
        self.main_text_field.setText(self.md_snippets[self.current_index])

    def save_edited_content(self):
        content = self.main_text_field.toPlainText()
        if content == self.md_snippets[self.current_index]:
            print("text content was not changed")
            return

        # TODO: make backup of old file?
        self.md_snippets[self.current_index] = content
        txt_fpath = pjoin(self.project_dir, self.src_fname)
        with open(txt_fpath, "w") as fp:
            fp.write(self.md_snippet_separator.join(self.md_snippets))

    def toggle_edit_mode(self):

        # print(f"{self.edit_mode=}")
        if self.edit_mode:
            # Switch to render mode
            self.edit_mode_button.setText("Edit")
            self.render_md_to_html(self.main_text_field.toPlainText())
            self.main_text_field.hide()
            self.main_text_browser.show()
            self.cursor_positions[self.current_index] = self.main_text_field.textCursor().position()
            # print(self.cursor_positions[self.current_index])

        else:
            # Switch to edit mode
            self.edit_mode_button.setText("Render")
            self.main_text_browser.hide()
            self.main_text_field.show()

            # moving the cursor position to the saved place does not yet work
            # -> not so important
            # cursor = self.main_text_field.textCursor()
            # cursor.setPosition(self.cursor_positions[self.current_index])
            # self.main_text_field.moveCursor(QTextCursor.End, QTextCursor.MoveAnchor)

            # self.main_text_field.setCursor(cursor)

        self.edit_mode = not self.edit_mode  # Toggle mode

    def assert_no_unsaved_changes(self):
        content = self.main_text_field.toPlainText()
        if content != self.md_snippets[self.current_index]:
            # error_dialog = QtWidgets.QErrorMessage()
            msg = "There are unsaved changes to the text. Save or reload."
            QMessageBox.information(None, "Information", msg)
            return False
        return True

    def _forward_or_backward(self, value):

        if not self.assert_no_unsaved_changes():
            return

        was_recording = False
        if self.stream is not None:
            self.stop_recording_and_save()
            was_recording = True
        self.change_index_by(value)
        self.load_content()

        if was_recording:
            # only start new recording if it was running before
            time.sleep(0.1)
            self.start_recording()

    def connect_key_sequence_to_method(self, ks: str, action_label: str, method: callable):

        assert isinstance(ks, str)
        self.shortcuts.append((ks, action_label))

        i = len(self.anonymous_actions)
        action = QAction(f"Action {i}", self)
        self.anonymous_actions.append(action)
        action.setShortcut(QKeySequence(ks))
        action.triggered.connect(method)
        self.addAction(action)

    def forward1(self):
        self._forward_or_backward(value=1)

    def forward10(self):
        self._forward_or_backward(value=10)

    def backward1(self):
        self._forward_or_backward(value=-1)

    def backward10(self):
        self._forward_or_backward(value=-10)

    def recording_callback(self, in_data, frame_count, time_info, status):

        if (len(self.audio_frames) % 100) == 0:
            pass
            # print(f"callback: {len(self.audio_frames)} frames")
        self.audio_frames.append(in_data)
        return (in_data, pyaudio.paContinue)

    def start_recording(self):

        if not self.assert_no_unsaved_changes():
            return

        self.recording_symbol.setColor("red")
        self.audio_frames = []
        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=44100,
            input=True,
            frames_per_buffer=1024,
            stream_callback=self.recording_callback,
        )
        self.stream.start_stream()

    def stop_recording_and_save(self):
        self.recording_symbol.setColor("gray")
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
            threading.Thread(target=self._save_audio).start()
        else:
            print("No audio stream to save")

    def get_current_image_basename(self):
        basename = os.path.splitext(os.path.split(self.image_files[self.current_index])[1])[0]
        return basename

    def _save_audio(self):
        """
        this is called by stop_recording
        """

        fpath = pjoin(self.audio_path, f"{self.get_current_image_basename()}.wav")

        if self.audio_frames is None:
            af_len = 0
        else:
            af_len = len(self.audio_frames)

        if af_len == 0:
            print(f"no audio to save (0 frames)")
            return

        print(f"saving audio:    {af_len} frames    {fpath}")

        with wave.open(fpath, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))
            wf.setframerate(44100)
            wf.writeframes(b"".join(self.audio_frames))
        # wf.close()

    def closeEvent(self, event):
        """
        This is called if the window is closed via click on the x-symbol
        """
        self.stop_recording_and_save()
        self.audio.terminate()


def main(args):
    app = QApplication(sys.argv)
    ex = ImageTextAudioTool(args)
    ex.show()
    sys.exit(app.exec_())
