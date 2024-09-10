
# Video Script Tool
## Background

I have N images and N wav files (of different lengths). They should be combined to one video file (mp4, webm, ...)
The length of the respective wav file determines how long each image is shown in the video.
I want to achieve this either via command line or via a python script.


## Installation

- Preparation on Linux:
    - `sudo apt install build-essential portaudio19-dev`
- `pip install -e .`


## Usage

### Slide Collector

- Uses a headless browser to create a screeshot (png) of every slide

- `video-script-cs --help` (shows options)
- `video-script-cs <project-dir> <presentation-url>`
- the optional option `--first-slide-number` might be useful if a presentation is divided into multiple parts:
    - example: `video-script-cs --first-slide-number 42 <project-dir> <presentation-url>`

### Text Extrator

- Extract voiceover-texts from special comments of the markdown node and
save them in `all_texts.md` (make them available for the next step).
- Note: this script uses some caching, which can be controlled by command line options

- `video-script-et --help` (shows options)
- `video-script-et <project-dir> <md-source-url>`
- useful option (example): `--suffix _a`


### GUI for Audio Recording

- Shows the slides-images in a GUI along with the voiceover-texts and offers simple possibilities
to record audio snippets for every slide-fragment (i.e. for every image)

- `video-script-rag --help` (shows options)
- `video-script-rag <project-dir>`
- useful option (example): `--suffix _a`

### Snippet Joiner

- Expects N audio files and the same number of images. Joins both kinds of input data to one video file

- `video-script-tool --help` (shows options, e.g. for audio preprocessing)
- `video-script-tool <project-dir>`

## Directory Layout

```
project_dir/
├── audio/
│   ├── noise/
│   │   └── noise.wav       (optional, currently not used)
│   ├── audio01.wav
│   └── ...
├── images/
│   ├── img01.png
│   └── ...
│
├── all_texts.md            (created by video-srcipt-et)
│
├── slides_full_source.md   (created by video-srcipt-et;
│                            caches the raw md source of the slides)
│
│   ↓ resulting files ↓
│
│
├── filelist.txt            (created by video-srcipt)
└── combined-video.mp4      (created by video-srcipt)
```
