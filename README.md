# 🎵 Dabbing Genre Tagger

**Dabbing Genre Tagger** is an AI-powered desktop app that scans your MP3 files and tags their genres using [musicnn](https://github.com/jordipons/musicnn). Tag results are saved directly to MP3 metadata and/or exported to Excel, all through a user-friendly graphical interface.

## 🔥 Features

🎧 **Genre Tagging Tab**
- Detect genres using AI (musicnn model)
- Customize audio chunk duration and overlap
- Tag MP3s with top 3 genres
- Export all tags to Excel
- Optional custom output folder
- Choose between: Tag MP3s, Export to Excel, or Both

🧹 **Batch Renamer Tab**
- Rename MP3 files with a custom prefix
- Rename based on top genre tag
- Preview and confirm before renaming

📝 **Metadata Editor Tab** (coming soon)
- Edit artist, album, year, and more metadata fields

📁 **Song Browser Tab**
- View and preview MP3s in a selected folder
- Inspect metadata (and eventually play audio)

⚙️ **Settings Tab**
- Toggle dark mode 🌙
- Save and load persistent user settings
- Reset to default config

🆘 **Help + About Tabs**
- Learn how to use the app
- View credits, tech used, and a few fun facts 🎶

✅ **General Perks**
- Dark mode styling across all widgets
- Progress bars, timers, and tagging logs
- Full GUI — no coding required!
- Built with ❤️ for the Friday Dabs crew

---

## 🛠️ Requirements

- Python **3.10**
- See `requirements.txt` for package versions

### Install dependencies:
bash
pip install -r requirements.txt

---

## 🚀 Usage

python app.py


## Credits

Built with love by **MedGrowerTom** 🌿💨  
Inspired by the Friday Dabs crew and the power of sonic tagging.

🧠 Powered By:
- Built using [musicnn](https://github.com/jordipons/musicnn) by Jordi Pons
- MP3 metadata editing via [mutagen](https://mutagen.readthedocs.io/)
- Excel support via [openpyxl](https://openpyxl.readthedocs.io/)
- GUI made with 🍃 Tkinter + ttk
- [TensorFlow](https://www.tensorflow.org/)
- [NumPy](https://numpy.org/)


## To Do

- Fix per-track progress bar (based on number of tagging windows)
- Add dark mode styling to About tab
- Style scrollbar for dark theme
- Add visual waveform preview with overlap indication
- Complete Metadata Editor functionality
- Add MP3 preview player in Song Browser
