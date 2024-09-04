import sys
import os
import glob
import threading
import time
import contextlib

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QTextBrowser, QVBoxLayout, QPushButton, QWidget, QTextEdit, QGridLayout,
)
from PyQt5.QtGui import QPixmap, QPainter, QColor
from PyQt5.QtCore import Qt, QRect
import markdown
import pyaudio
import wave

from .util import bred, PyaudioStdoutWrapper


from ipydex import IPS

pjoin = os.path.join

# to mute logging noise for pyaudio


@contextlib.contextmanager
def suppress_output():
    with open(os.devnull, 'w') as fnull:
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

        txt_fpath = pjoin(self.project_dir, "all_texts.md")
        with open(txt_fpath, "r") as fp:
            txt_data = fp.read()
        self.md_snippets = txt_data.split("\n---\n")

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
        self.setWindowTitle('Image Text Audio Tool')
        self.setGeometry(100, 100, 1200, 1000)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QGridLayout(central_widget)

        button_area_layout = QVBoxLayout()
        button_area_widget = QWidget()
        button_area_widget.setLayout(button_area_layout)

        self.main_text_browser = QTextBrowser(self)
        self.main_text_browser.setFixedSize(1000, 300)
        layout.addWidget(self.main_text_browser, 0, 0, alignment=Qt.AlignCenter)

        self.main_text_field = QTextEdit(self)
        self.main_text_field.setFixedSize(500, 300)
        layout.addWidget(self.main_text_field, 0, 0, alignment=Qt.AlignCenter)
        self.main_text_field.hide()

        self.edit_mode_button = QPushButton("edit")
        self.edit_mode_button.clicked.connect(self.toggle_edit_mode)
        layout.addWidget(button_area_widget, 0, 1)
        button_area_layout.addWidget(self.edit_mode_button)

        self.save_button = QPushButton("save")
        button_area_layout.addWidget(self.save_button)

        self.image_label = QLabel(self)
        self.image_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.image_label, 1, 0)

        self.info_label = QLabel(' test ', self)
        self.info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.info_label, 2, 0)

        self.circle = ColorCircle('gray')
        self.circle.setFixedSize(20, 20)
        layout.addWidget(self.circle, 1, 1, alignment=Qt.AlignCenter)
        self.help_label = QLabel("W: start recording; S: Stop recording; D: go forward; A: go back", self)
        layout.addWidget(self.help_label, 3, 0)

        self.load_content()
        print("init done")

    def load_content(self):
        image_path = self.image_files[self.current_index]

        # Load image
        pixmap = QPixmap(image_path)
        self.image_label.setPixmap(pixmap.scaled(1000, 1000, Qt.KeepAspectRatio))

        self.render_md_to_html(self.md_snippets[self.current_index])
        self.info_label.setText(f"{self.current_index} {self.get_current_image_basename()}")


    def change_index_by(self, value):
        assert value in (-1, 1)

        self.current_index += value
        if self.current_index >= len(self.image_files):
            self.current_index = len(self.image_files) - 1
        if self.current_index <= 0:
            self.current_index = 0

    def render_md_to_html(self, md_src):

        # render markdown
        html_content = markdown.markdown(md_src)

        style = "font-size: x-large; text-align:center;"
        outer_html = f'<div style="{style}">{html_content}</div>'
        self.main_text_browser.setHtml(outer_html)

        self.main_text_field.setText(md_src)

    def toggle_edit_mode(self):

        # print(f"{self.edit_mode=}")
        if self.edit_mode:
            # Switch to render mode
            self.edit_mode_button.setText("edit")
            self.render_md_to_html(self.main_text_field.toPlainText())
            self.main_text_field.hide()
            self.main_text_browser.show()

        else:
            # Switch to edit mode
            self.edit_mode_button.setText("render")
            self.main_text_browser.hide()
            self.main_text_field.show()

        self.edit_mode = not self.edit_mode  # Toggle mode

    def _forward_or_backward(self, value):
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

    def keyPressEvent(self, event):
        # print("key pressed", event.key())
        if event.key() == Qt.Key_W:
            self.start_recording()
        elif event.key() in (Qt.Key_Space, Qt.Key_D):
            # move forward
            self._forward_or_backward(value=1)
        elif event.key() == Qt.Key_A:
            # backward
            self._forward_or_backward(value=-1)

        elif event.key() == Qt.Key_S:
            self.stop_recording_and_save()
        elif event.key() == Qt.Key_X:
            self.stop_recording_and_save()
            self.close()

    def recording_callback(self, in_data, frame_count, time_info, status):

        if (len(self.audio_frames) % 100) == 0:
            pass
            # print(f"callback: {len(self.audio_frames)} frames")
        self.audio_frames.append(in_data)
        return (in_data, pyaudio.paContinue)

    def start_recording(self):
        self.circle.setColor('red')
        self.audio_frames = []
        self.stream = self.audio.open(format=pyaudio.paInt16,
                                      channels=1,
                                      rate=44100,
                                      input=True,
                                      frames_per_buffer=1024,
                                      stream_callback=self.recording_callback)
        self.stream.start_stream()

    # def start_recording(self):
    #     print("start recording for", self.image_files[self.current_index])
    #     self.is_recording = True
    #     self.audio_frames = []


    def stop_recording_and_save(self):
        self.circle.setColor('gray')
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
            threading.Thread(target=self._save_audio).start()
        else:
            print("stream is None. Nothing to save")

    # def stop_recording(self):
    #     print("stop recording for", self.image_files[self.current_index])
    #     self.is_recording = False

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

        with wave.open(fpath, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))
            wf.setframerate(44100)
            wf.writeframes(b''.join(self.audio_frames))
        # wf.close()


    def closeEvent(self, event):
        """
        This is called if the window is closed via click on the x-symbol
        """
        if self.stream is not None:
            self.stream.stop_stream()
            self.stream.close()
        self.audio.terminate()


def main(args):
    app = QApplication(sys.argv)
    ex = ImageTextAudioTool(args)
    ex.show()
    sys.exit(app.exec_())
