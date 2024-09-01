
# Background

I have N images and N wav files (of different lengths). They should be combined to one video file (mp4, webm, ...)
The length of the respective wav file determines how long each image is shown in the video.
I want to achieve this either via command line or via a python script.


# Usage

`video-script-tool <project-dir>`

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
├── all_texts.md
│
│
│   ↓ resulting files ↓
│
│
├── filelist.txt
└── combined-video.mp4
```
