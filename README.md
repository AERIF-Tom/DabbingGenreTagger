# 🎵 Dabbing Genre Tagger

An AI-powered GUI tool that scans your MP3 files and tags their genre using [musicnn](https://github.com/jordipons/musicnn), saving tags to MP3 metadata and/or an Excel file.

## Features
- Detect genres using AI (musicnn model)
- Tag MP3s with top 3 genres
- Export full tagging results to Excel
- Customize tagging window and overlap
- Dark mode 🌙
- Save + load user settings
- Stop tagging anytime
- Save tagging logs
- Full GUI — no coding needed!

## Requirements
- Python 3.10
- See `requirements.txt` for all needed packages + versions

## Usage
bash
python main.py

## Credits

Built with love by **MedGrowerTom** 🌿💨  
Inspired by the Friday Dabs crew and the power of sonic tagging.

Uses:
- Built using [musicnn](https://github.com/jordipons/musicnn) by Jordi Pons
- MP3 metadata editing via [mutagen](https://mutagen.readthedocs.io/)
- Excel support via [openpyxl](https://openpyxl.readthedocs.io/)
- GUI made with 🍃 Tkinter + ttk
- [TensorFlow](https://www.tensorflow.org/)
- [NumPy](https://numpy.org/)


## To Do
- fix track progress bar, so it sees how many windows there are for the track bases on track length and audio chunk length, and uses that to know where its 100% is
- add dark theme to the about section
- add dark theme to the scroll bar
* add a visual for the audio and the overlapping
