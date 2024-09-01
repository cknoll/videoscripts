import sys
import os
import glob
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QTextBrowser, QVBoxLayout, QWidget
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
import markdown
import pyaudio
import wave

from ipydex import IPS

pjoin = os.path.join

class ImageTextAudioTool(QMainWindow):
    def __init__(self, args):
        super().__init__()
        self.project_dir = args.project_dir
        self.audio_path = pjoin(self.project_dir, "audio")
        self.current_index = 0
        self.is_recording = False
        self.audio_frames = []
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
        self.setGeometry(100, 100, 800, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.image_label = QLabel(self)
        self.image_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.image_label)

        self.text_browser = QTextBrowser(self)
        layout.addWidget(self.text_browser)

        self.load_content()
        print("init done")

    def load_content(self):
        image_path = self.image_files[self.current_index]

        # Load image
        pixmap = QPixmap(image_path)
        self.image_label.setPixmap(pixmap.scaled(400, 300, Qt.KeepAspectRatio))

        # render markdown
        html_content = markdown.markdown(self.md_snippets[self.current_index])
        self.text_browser.setHtml(html_content)

    def setup_audio(self):
        return
        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(format=pyaudio.paInt16,
                                      channels=1,
                                      rate=44100,
                                      input=True,
                                      frames_per_buffer=1024)

    def keyPressEvent(self, event):
        print("key pressed", event.key())
        if event.key() == Qt.Key_A:
            self.start_recording()
        elif event.key() in (Qt.Key_Space, Qt.Key_S):
            self.stop_recording()
            self.save_audio()
            if self.current_index < len(self.image_files) - 1:
                self.current_index += 1
            self.start_recording()
        elif event.key() == Qt.Key_X:
            self.stop_recording()
            self.save_audio()

    def start_recording(self):
        print("start recording for", self.image_files[self.current_index])
        self.is_recording = True
        self.audio_frames = []

    def stop_recording(self):
        print("stop recording for", self.image_files[self.current_index])
        self.is_recording = False

    def save_audio(self):
        return
        basename = os.path.splitext(os.path.split(self.image_files[self.current_index])[1])[0]
        fpath = pjoin(self.audio_path, f"{basename}.wav")
        with wave.open(fpath, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))
            wf.setframerate(44100)
            wf.writeframes(b''.join(self.audio_frames))
        # wf.close()

    def closeEvent(self, event):
        return
        self.stream.stop_stream()
        self.stream.close()
        self.audio.terminate()


def main(args):
    app = QApplication(sys.argv)
    ex = ImageTextAudioTool(args)
    ex.show()
    sys.exit(app.exec_())
