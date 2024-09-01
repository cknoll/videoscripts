import sys
import os
import glob
import threading
import time

from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QTextBrowser, QVBoxLayout, QPushButton, QWidget
from PyQt5.QtGui import QPixmap, QPainter, QColor
from PyQt5.QtCore import Qt, QRect
import markdown
import pyaudio
import wave


from ipydex import IPS

pjoin = os.path.join

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
        os.makedirs(self.audio_path, exist_ok=True)
        self.current_index = 0
        self.is_recording = False
        self.audio_frames = None
        self.load_data()
        self.setup_audio()
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
        assert len(self.md_snippets) == len(self.image_files)

    def initUI(self):
        self.setWindowTitle('Image Text Audio Tool')
        self.setGeometry(100, 100, 1200, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.text_browser = QTextBrowser(self)
        layout.addWidget(self.text_browser)

        self.image_label = QLabel(self)
        self.image_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.image_label)

        self.info_label = QLabel(' test ', self)
        self.info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.info_label)

        self.circle = ColorCircle('gray')
        self.circle.setFixedSize(20, 20)
        layout.addWidget(self.circle, alignment=Qt.AlignCenter)
        self.help_label = QLabel("W: start recording; S: Stop recording; D: go forward; A: go back", self)
        layout.addWidget(self.help_label)

        self.load_content()
        print("init done")

    def load_content(self):
        image_path = self.image_files[self.current_index]

        # Load image
        pixmap = QPixmap(image_path)
        self.image_label.setPixmap(pixmap.scaled(800, 600, Qt.KeepAspectRatio))

        # render markdown
        html_content = markdown.markdown(self.md_snippets[self.current_index])
        self.text_browser.setHtml(html_content)

    def setup_audio(self):
        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(format=pyaudio.paInt16,
                                      channels=1,
                                      rate=44100,
                                      input=True,
                                      frames_per_buffer=1024)

    def change_index_by(self, value):
        assert value in (-1, 1)

        self.current_index += value
        if self.current_index >= len(self.image_files):
            self.current_index = len(self.image_files) - 1
        if self.current_index <= 0:
            self.current_index = 0

        self.info_label.setText(f"{self.current_index} {self.get_current_image_basename()}")

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
        print("key pressed", event.key())
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
              print(f"callback: {len(self.audio_frames)} frames")
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
        print(f"saving audio:    {len(self.audio_frames)} frames    {fpath}")

        with wave.open(fpath, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))
            wf.setframerate(44100)
            wf.writeframes(b''.join(self.audio_frames))
        # wf.close()


    def closeEvent(self, event):
        print("closeEvent")
        return
        self.stream.stop_stream()
        self.stream.close()
        self.audio.terminate()


def main(args):
    app = QApplication(sys.argv)
    ex = ImageTextAudioTool(args)
    ex.show()
    sys.exit(app.exec_())
