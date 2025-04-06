import os
import time
import threading
import configparser
from datetime import timedelta
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import numpy as np
from musicnn.extractor import extractor
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from openpyxl import Workbook
from scipy.stats import logser

# This Ignores the CUDA Error , Could not load dynamic library 'cudart64_110.dll' due to lack of gpu
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

# ========================
# Directory Setup
# ========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SONGS_DIR = os.path.join(BASE_DIR, "songs")
RESULTS_DIR = os.path.join(BASE_DIR, "results")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
DATA_DIR = os.path.join(BASE_DIR, "data")

# Ensure directories exist, Create folders if they don't exist
for folder in [SONGS_DIR, RESULTS_DIR,LOGS_DIR, DATA_DIR]:
    os.makedirs(folder, exist_ok=True)

CONFIG_FILE = os.path.join(DATA_DIR, "tagger_config.ini")
config = configparser.ConfigParser()

# ========================
# GUI Initialization
# ========================
root = tk.Tk()
root.title("🎵 Dabbing MP3 Manager")
root.geometry("800x850")

# ========================
# Styling (Light/Dark Theme)
# ========================

style = ttk.Style()
style.theme_use('default')
style.configure("TCombobox", fieldbackground='white', background='white', foreground='black')
style.configure("TScale", troughcolor='SystemButtonFace')
style.configure("TProgressbar", background="#4CAF50", troughcolor='SystemButtonFace')

# Create tab control (Notebook)
tab_control = ttk.Notebook(root)
tab_control.pack(expand=True, fill="both", padx=10, pady=10)

# Tabs
tab_genre = ttk.Frame(tab_control)
tab_renamer = ttk.Frame(tab_control)
tab_metadata = ttk.Frame(tab_control)
tab_help = ttk.Frame(tab_control)
tab_about = ttk.Frame(tab_control)
tab_settings = ttk.Frame(tab_control)
tab_browser = ttk.Frame(tab_control)

# Add tabs to notebook
tab_control.add(tab_genre, text="🎧 Genre Tagger")
tab_control.add(tab_renamer, text="✍️ Batch Renamer")
tab_control.add(tab_metadata, text="🛠 Metadata Editor")
tab_control.add(tab_browser, text="📂 Song Browser")
tab_control.add(tab_help, text="❓ Help")
tab_control.add(tab_about, text="ℹ️ About")
tab_control.add(tab_settings, text="⚙️ Settings")

dark_mode = False
stop_flag = False

# ========================
# Shared Header (reusable)
# ========================
def build_header(tab, tab_name):
    header_frame = tk.Frame(tab)
    header_frame.pack(pady=10)

    tk.Label(header_frame, text=f"🎵 {tab_name}", font=("Helvetica", 16, "bold")).pack()
    btn_frame = tk.Frame(tab)
    btn_frame.pack(pady=(0, 10))

    tk.Button(btn_frame, text="🌓 Toggle Dark Mode", command=toggle_dark_mode).pack(side="left", padx=5)
    tk.Button(btn_frame, text="🔄 Reset to Defaults", command=reset_to_defaults).pack(side="left", padx=5)


# ========================
# Tkinter Variable Setup
# ========================
folder_var = tk.StringVar(value=SONGS_DIR)
duration_var = tk.StringVar(value="3")
overlap_var = tk.IntVar(value=50)
mode_var = tk.StringVar(value="Pick a tagging mode...")
use_custom_output = tk.BooleanVar(value=False)
custom_output_folder = tk.StringVar(value=RESULTS_DIR)
var_top_tags_only = tk.BooleanVar(value=False)

def update_gui_visibility(*args):
    """Enable or disable Excel folder options based on current mode and checkbox."""
    mode = mode_var.get()
    allow_excel = mode in ("Export to Excel only", "Tag MP3s & Export to Excel")

    # Enable/disable custom output folder checkbox and entry
    state = "normal" if allow_excel and use_custom_output.get() else "disabled"
    custom_checkbox.config(state="normal" if allow_excel else "disabled")
    custom_output_entry.config(state=state)
    browse_button.config(state=state)

    # Apply theme again so style sticks after state change
    root.after(10, apply_theme)

def on_mode_change(*args):
    """Trigger GUI update and config save when mode changes."""
    update_gui_visibility()
    save_config()

# Trace changes for saving config
def trace_all():
    folder_var.trace_add("write", lambda *args: save_config())
    mode_var.trace_add("write", on_mode_change)
    var_top_tags_only.trace_add("write", lambda *args: save_config())
    duration_var.trace_add("write", lambda *args: save_config())
    overlap_var.trace_add("write", lambda *args: save_config())
    use_custom_output.trace_add("write", lambda *args: save_config())
    custom_output_folder.trace_add("write", lambda *args: save_config())

# ========================
# Theme Application
# ========================
def apply_theme():
    bg = '#1e1e1e' if dark_mode else 'SystemButtonFace'
    fg = 'white' if dark_mode else 'black'
    entry_bg = '#2c2c2c' if dark_mode else 'white'
    output_bg = '#1e1e1e' if dark_mode else 'white'
    output_fg = 'white' if dark_mode else 'black'

    style.configure("TCombobox", fieldbackground=entry_bg, background=entry_bg, foreground=fg)
    style.configure("TScale", troughcolor=bg)
    style.configure("TProgressbar", background="#4CAF50", troughcolor=bg)
    style.map("TCombobox",
              fieldbackground=[("readonly", entry_bg)],
              background=[("readonly", entry_bg)],
              foreground=[("readonly", fg)])

    root.configure(bg=bg)
    for tab in tab_control.winfo_children():
        try:
            tab.configure(bg=bg)
        except tk.TclError:
            pass  # Skip ttk widgets that don't support 'bg'

        for widget in tab.winfo_children():
            try:
                widget.configure(bg=bg, fg=fg)
            except:
                pass
            # Recursively apply to inner frames
            for child in widget.winfo_children():
                try:
                    child.configure(bg=bg, fg=fg)
                except:
                    pass

    for button in button_frame.winfo_children():
        try:
            button.configure(bg="#4CAF50" if "Start" in button.cget("text") else "#f44336", fg="white")
        except:
            pass

# ========================
# Config Management
# ========================
def load_config():
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
        settings = config["Settings"]
        folder_var.set(settings.get("mp3_folder", SONGS_DIR))
        mode_var.set(settings.get("tagging_mode", "Pick a tagging mode..."))
        var_top_tags_only.set(settings.getboolean("top_tags_only", False))
        use_custom_output.set(settings.getboolean("use_custom_output", False))
        custom_output_folder.set(settings.get("excel_output_folder", RESULTS_DIR))
        duration_var.set(settings.get("duration", "3"))
        overlap_var.set(int(settings.get("overlap", "50")))
        global dark_mode
        dark_mode = settings.getboolean("dark_mode", False)
        apply_theme()

def save_config():
    config["Settings"] = {
        "mp3_folder": folder_var.get(),
        "tagging_mode": mode_var.get(),
        "top_tags_only": str(var_top_tags_only.get()),
        "use_custom_output": str(use_custom_output.get()),
        "excel_output_folder": custom_output_folder.get(),
        "duration": duration_var.get(),
        "overlap": str(overlap_var.get()),
        "dark_mode": str(dark_mode)
    }
    with open(CONFIG_FILE, "w") as configfile:
        config.write(configfile)

# ========================
# Settings Tab
# ========================
"""Switch between light and dark mode."""
def toggle_dark_mode():
    global dark_mode
    dark_mode = not dark_mode
    apply_theme()
    save_config()

def reset_to_defaults():
    if messagebox.askyesno("Reset Settings", "Reset all settings to default?"):
        folder_var.set(SONGS_DIR)
        duration_var.set("3")
        overlap_var.set(50)
        mode_var.set("Pick a tagging mode...")
        use_custom_output.set(False)
        custom_output_folder.set(RESULTS_DIR)
        var_top_tags_only.set(False)
        global dark_mode
        dark_mode = False
        apply_theme()
        save_config()

settings_label = tk.Label(tab_settings, text="Settings", font=("Helvetica", 16, "bold"))
settings_label.pack(pady=10)
tk.Button(tab_settings, text="🌓 Toggle Dark Mode", command=toggle_dark_mode).pack(pady=5)
tk.Button(tab_settings, text="🔄 Reset to Defaults", command=reset_to_defaults).pack(pady=5)

# Build shared header in each tab
build_header(tab_genre, "Genre Tagger")
build_header(tab_renamer, "Batch Renamer")
build_header(tab_metadata, "Metadata Editor")
build_header(tab_browser, "Song Browser")
build_header(tab_help, "Help")
build_header(tab_about, "About")
build_header(tab_settings, "Settings")

# ========================
# Song Browser Layout
# ========================
browser_folder_var = tk.StringVar()
song_list_var = tk.StringVar(value=[])
selected_song_var = tk.StringVar()
metadata_display = None

def browse_song_folder():
    folder = filedialog.askdirectory(title="Choose Folder to Browse Songs")
    if folder:
        browser_folder_var.set(folder)
        load_songs_from_folder(folder)

def load_songs_from_folder(folder):
    songs = [f for f in os.listdir(folder) if f.lower().endswith(".mp3")]
    song_listbox.delete(0, tk.END)
    for song in songs:
        song_listbox.insert(tk.END, song)
    selected_song_var.set("")
    metadata_display.config(state="normal")
    metadata_display.delete("1.0", tk.END)
    metadata_display.insert(tk.END, "Select a song to view metadata.\n")
    metadata_display.config(state="disabled")

def show_song_metadata(event=None):
    selected = song_listbox.curselection()
    if not selected:
        return
    index = selected[0]
    song_name = song_listbox.get(index)
    song_path = os.path.join(browser_folder_var.get(), song_name)

    try:
        audio = MP3(song_path, ID3=EasyID3)
        lines = [
            f"🎵 File: {song_name}",
            f"🎤 Artist: {audio.get('artist', [''])[0]}",
            f"👤 Album Artist: {audio.get('albumartist', [''])[0]}",
            f"💿 Album: {audio.get('album', [''])[0]}",
            f"📅 Year: {audio.get('date', [''])[0]}",
            f"🏢 Publisher: {audio.get('organization', [''])[0]}",
            f"© Copyright: {audio.get('copyright', [''])[0]}",
            f"🎧 Genre: {audio.get('genre', [''])[0]}",
            f"⏱ Length: {int(audio.info.length)} seconds"
        ]
    except Exception as e:
        lines = [f"❌ Error reading metadata: {e}"]

    metadata_display.config(state="normal")
    metadata_display.delete("1.0", tk.END)
    metadata_display.insert(tk.END, "\n".join(lines))
    metadata_display.config(state="disabled")

# Folder selection row
browser_top = tk.Frame(tab_browser)
browser_top.pack(padx=20, pady=(10,5), anchor="w")

tk.Button(browser_top, text="📂 Select Folder", command=browse_song_folder).grid(row=0, column=0, padx=(0, 5))
tk.Label(browser_top, textvariable=browser_folder_var, fg="blue").grid(row=0, column=1)

# Song Listbox
song_listbox = tk.Listbox(tab_browser, width=50, height=20)
song_listbox.pack(side="left", padx=(20,10), pady=(5,10), anchor="n")
song_listbox.bind("<<ListboxSelect>>", show_song_metadata)

# Metadata Viewer
metadata_frame = tk.Frame(tab_browser)
metadata_frame.pack(side="left", fill="both", expand=True, padx=(0,20), pady=(5,10), anchor="n")

metadata_display = scrolledtext.ScrolledText(metadata_frame, wrap=tk.WORD, width=45, height=20, state="disabled")
metadata_display.pack(fill="both", expand=True)

# Placeholder for Player
player_placeholder = tk.Label(metadata_frame, text="🎵 [Player Placeholder]", font=("Helvetica", 10, "italic"))
player_placeholder.pack(pady=10)


# ========================
# Metadata Editor Layout
# ========================

# ====== Metadata Logic ======

meta_folder_var = tk.StringVar()
meta_fields_vars = {
    "Contributing Artist": tk.StringVar(),
    "Album Artist": tk.StringVar(),
    "Album Title": tk.StringVar(),
    "Year": tk.StringVar(),
    "Publisher": tk.StringVar(),
    "Copyright": tk.StringVar()
}

def browse_meta_folder():
    folder = filedialog.askdirectory(title="Choose Folder to Apply Metadata")
    if folder:
        meta_folder_var.set(folder)

def apply_metadata():
    folder = meta_folder_var.get()
    if not os.path.isdir(folder):
        messagebox.showerror("Error", "Please select a valid folder.")
        return

    files = [f for f in os.listdir(folder) if f.lower().endswith(".mp3")]
    if not files:
        messagebox.showwarning("No MP3s", "No MP3 files found in this folder.")
        return

    confirm = messagebox.askyesno("Confirm", f"Apply metadata to {len(files)} MP3 files?")
    if not confirm:
        return

    updates = {field: var.get().strip() for field, var in meta_fields_vars.items() if var.get().strip()}

    for fname in files:
        try:
            path = os.path.join(folder, fname)
            audio = MP3(path, ID3=EasyID3)

            for field, value in updates.items():
                # Map user-friendly names to EasyID3 keys
                if field == "Contributing Artist":
                    audio["artist"] = value
                elif field == "Album Artist":
                    audio["albumartist"] = value
                elif field == "Album Title":
                    audio["album"] = value
                elif field == "Year":
                    audio["date"] = value
                elif field == "Publisher":
                    audio["organization"] = value
                elif field == "Copyright":
                    audio["copyright"] = value

            audio.save()
        except Exception as e:
            print(f"Error updating {fname}: {e}")

    messagebox.showinfo("Done", f"Updated metadata on {len(files)} files.")


meta_frame = tk.LabelFrame(tab_metadata, text="Bulk Metadata Fields", padx=10, pady=10)
meta_frame.pack(padx=20, pady=20, fill="x")
fields = ["Contributing Artist", "Album Artist", "Album Title", "Year", "Publisher", "Copyright"]
for i, label in enumerate(fields):
    tk.Label(meta_frame, text=label + ":").grid(row=i, column=0, sticky="w")
    tk.Entry(meta_frame, textvariable=meta_fields_vars[label], width=50).grid(row=i, column=1, pady=3)
tk.Button(meta_frame, text="📂 Select Folder", command=browse_meta_folder).grid(row=len(fields), column=0, pady=15)
tk.Button(meta_frame, text="💾 Apply Metadata", command=apply_metadata).grid(row=len(fields), column=1, pady=15)
tk.Label(meta_frame, textvariable=meta_folder_var, fg="blue").grid(row=len(fields)+1, column=0, columnspan=2, sticky="w", pady=(5,0))


# ========================
# Batch Renamer Layout
# ========================
# === Batch Renamer Logic ===
rename_folder_var = tk.StringVar()
rename_prefix_var = tk.StringVar(value="MyTrack")
rename_mode_var = tk.StringVar(value="Use prefix")
preview_output = None

def browse_rename_folder():
    folder = filedialog.askdirectory(title="Choose Folder to Rename")
    if folder:
        rename_folder_var.set(folder)

def preview_renames():
    folder = rename_folder_var.get()
    prefix = rename_prefix_var.get()
    mode = rename_mode_var.get()
    if not os.path.isdir(folder):
        messagebox.showerror("Error", "Please select a valid folder.")
        return

    files = [f for f in os.listdir(folder) if f.lower().endswith(".mp3")]
    if not files:
        messagebox.showwarning("No MP3s", "No MP3 files found in this folder.")
        return

    preview_output.config(state='normal')
    preview_output.delete(1.0, tk.END)

    for i, fname in enumerate(files, start=1):
        old_path = os.path.join(folder, fname)

        if mode == "Use prefix":
            new_name = f"{prefix}{i:02}.mp3"
        else:  # Use genre tag
            try:
                audio = MP3(old_path, ID3=EasyID3)
                genre = audio.get("genre", ["unknown"])[0].split(",")[0].strip()
                new_name = f"{genre}{i:02}.mp3"
            except:
                new_name = f"unknown{i:02}.mp3"

        preview_output.insert(tk.END, f"{fname} → {new_name}\n")

    preview_output.config(state='disabled')

def confirm_renames():
    folder = rename_folder_var.get()
    prefix = rename_prefix_var.get()
    mode = rename_mode_var.get()

    if not messagebox.askyesno("Confirm Rename", "Are you sure you want to rename the files?"):
        return

    files = [f for f in os.listdir(folder) if f.lower().endswith(".mp3")]

    for i, fname in enumerate(files, start=1):
        old_path = os.path.join(folder, fname)

        if mode == "Use prefix":
            new_name = f"{prefix}{i:02}.mp3"
        else:
            try:
                audio = MP3(old_path, ID3=EasyID3)
                genre = audio.get("genre", ["unknown"])[0].split(",")[0].strip()
                new_name = f"{genre}{i:02}.mp3"
            except:
                new_name = f"unknown{i:02}.mp3"

        new_path = os.path.join(folder, new_name)
        os.rename(old_path, new_path)

    messagebox.showinfo("Done", f"Renamed {len(files)} files.")
    preview_renames()

# ==== UI Layout for Batch Renamer ====
rename_frame = tk.LabelFrame(tab_renamer, text="Rename Options", padx=10, pady=10)
rename_frame.pack(padx=20, pady=10, fill="x")

tk.Label(rename_frame, text="Folder:").grid(row=0, column=0, sticky="w")
tk.Entry(rename_frame, textvariable=rename_folder_var, width=50).grid(row=0, column=1, padx=5)
tk.Button(rename_frame, text="📂 Browse", command=browse_rename_folder).grid(row=0, column=2, padx=5)

tk.Label(rename_frame, text="Prefix (for option 1):").grid(row=1, column=0, sticky="w", pady=(10, 0))
tk.Entry(rename_frame, textvariable=rename_prefix_var).grid(row=1, column=1, pady=(10, 0), sticky="w")

tk.Label(rename_frame, text="Rename Mode:").grid(row=2, column=0, sticky="w", pady=(10, 0))
ttk.Combobox(rename_frame, textvariable=rename_mode_var, values=["Use prefix", "Use genre tag"], state="readonly").grid(row=2, column=1, pady=(10, 0), sticky="w")

tk.Button(rename_frame, text="🧪 Preview Rename", command=preview_renames).grid(row=3, column=0, pady=15)
tk.Button(rename_frame, text="✅ Confirm Rename", command=confirm_renames).grid(row=3, column=1, pady=15)

preview_output = scrolledtext.ScrolledText(tab_renamer, wrap=tk.WORD, width=80, height=20, state='disabled')
preview_output.pack(padx=20, pady=5)


# ========================
# Genre Tagger Layout
# ========================

# Folder Selection Helpers
def choose_folder():
    folder_path = filedialog.askdirectory(initialdir=SONGS_DIR)
    if folder_path:
        folder_var.set(folder_path)

def choose_excel_folder():
    folder_path = filedialog.askdirectory(initialdir=RESULTS_DIR)
    if folder_path:
        custom_output_folder.set(folder_path)

# ========================
# Tagging Engine Logic
# ========================

def process_files(folder_path, do_genre, do_excel, gui_update_fn, update_progress_fn, top_tags_only, excel_only, input_length, custom_excel_folder=None, input_overlap=0.5):
    """
    Process MP3 files in the selected folder and tag them using musicnn.
    This function supports tagging, genre metadata writing, and Excel export.
    """
    global stop_flag
    stop_flag = False
    songs_tagged = []
    files = [f for f in os.listdir(folder_path) if f.lower().endswith(".mp3")]
    total = len(files)
    start_time = time.time()

    for i, filename in enumerate(files):
        if stop_flag:
            elapsed = time.time() - start_time
            mins, secs = divmod(int(elapsed), 60)
            current_track_label.config(text="⛔ Stopped")
            gui_update_fn(f"🚩 Stopped. Total time spent: {mins:02}:{secs:02}")
            return

        filepath = os.path.join(folder_path, filename)
        gui_update_fn(f"\n🎵 [{i+1}/{total}] Tagging: {filename}")
        current_track_label.config(text=f"Now tagging: {filename}")

        try:
            # Load audio metadata
            audio = MP3(filepath)
            input_length = float(input_length)

            # Skip files that are too short
            if audio.info.length < 3.0:
                gui_update_fn(f"⚠️ Skipping {filename} – too short ({audio.info.length:.2f}s)")
                continue
            if audio.info.length < input_length:
                gui_update_fn(f"⚠️ Skipping {filename} – shorter than input window ({audio.info.length:.2f}s)")
                continue

            try:
                gui_update_fn(f"🧪 Using input window: {input_length}s with {int(input_overlap * 100)}% overlap")
                track_start = time.time()

                # Extract tags using musicnn
                tag_scores_raw, tag_names, _ = extractor(
                    filepath,
                    model='MSD_musicnn',
                    input_length=input_length,
                    input_overlap=input_overlap,
                )

                # Set per-track progress bar
                track_progress_bar["maximum"] = tag_scores_raw.shape[0]
                track_progress_bar["value"] = 0

                # Print elapsed time
                track_elapsed = time.time() - track_start
                gui_update_fn(f"🕒 Time spent tagging this track: {track_elapsed:.2f}s")

                # Show processed duration and chunk count
                num_windows = tag_scores_raw.shape[0]
                total_processed = num_windows * input_length
                capped_total = min(audio.info.length, total_processed)
                gui_update_fn(f"📊 Processed with {num_windows} overlapping windows of {input_length:.1f}s each")
                gui_update_fn(f"📊 Total processed: ~{capped_total:.1f}s (track length: {audio.info.length:.1f}s)")

                # Average over all tag scores
                tag_scores = np.mean(tag_scores_raw, axis=0)

                # Instead of analyzing whole track instantly, simulate real-time window tagging
                track_progress_bar["maximum"] = tag_scores_raw.shape[0]
                track_progress_bar["value"] = 0

                for win_idx, window_scores in enumerate(tag_scores_raw):
                    if stop_flag:
                        break

                    # Optional: Add small delay to simulate processing time if you want
                    # Fix both progress bars 
                    time.sleep(0.01)

                    track_progress_bar["value"] = win_idx + 1
                    root.update_idletasks()

                # After loop completes, average the scores
                tag_scores = np.mean(tag_scores_raw, axis=0)

                # Safety check on result shape
                if not isinstance(tag_scores, np.ndarray) or len(tag_scores) != len(tag_names):
                    gui_update_fn(f"⚠️ Skipping {filename} due to tag length mismatch")
                    continue

            except Exception as e:
                gui_update_fn(f"❌ Error extracting tags from {filename}: {e}")
                continue

            # Sort and keep top tags
            sorted_indices = np.argsort(tag_scores)[::-1]
            tags = []
            for idx in sorted_indices[:10]:
                try:
                    score_val = float(tag_scores[idx])
                    tags.append((tag_names[idx], score_val))
                except (ValueError, TypeError):
                    gui_update_fn(f"⚠️ Skipping invalid score: {tag_names[idx]} = {tag_scores[idx]}")

            if top_tags_only:
                tags = tags[:3]

            # Format tag text and store results
            top3 = [tag for tag, _ in tags[:3]]
            tag_text = "\n".join([
                f"⭐ {tag} ({score:.2f})" if idx < 3 else f"• {tag} ({score:.2f})"
                for idx, (tag, score) in enumerate(tags)
            ])
            gui_update_fn(tag_text)
            songs_tagged.append((filename, tags))

            # Update MP3 metadata with top tags
            if do_genre and not excel_only:
                try:
                    audio = MP3(filepath, ID3=EasyID3)
                    if audio.tags is None:
                        try:
                            audio.add_tags()
                        except Exception as e:
                            gui_update_fn(f"⚠️ Could not add ID3 tags to {filename}: {e}")
                            continue

                    audio['genre'] = ', '.join(top3)
                    audio.save()
                    gui_update_fn(f"✅ Genre updated: {top3}")

                except Exception as e:
                    gui_update_fn(f"⚠️ Error writing to {filename}: {e}")

        except Exception as e:
            gui_update_fn(f"❌ Error tagging {filename}: {e}")
            continue

        # Update overall progress
        elapsed = time.time() - start_time
        avg_time = elapsed / (i + 1)
        est_remaining = avg_time * (total - i - 1)
        mins, secs = divmod(est_remaining, 60)
        update_progress_fn(i + 1, total, f"⏱️ Est. time left: {int(mins):02d}:{int(secs):02d}")

    # Export to Excel if requested
    if do_excel and songs_tagged:
        excel_path = custom_excel_folder if custom_excel_folder else folder_path
        save_excel(excel_path, songs_tagged)

    if not stop_flag:
        total = time.time() - start_time
        gui_update_fn(f"🎉 All done tagging! Total time: {str(timedelta(seconds=int(total)))}")
        current_track_label.config(text="")
        messagebox.showinfo("Done", "🎉 All done tagging!")

# ========================
# Excel Export Helper
# ========================

def save_excel(folder_path, songs_tagged):
    """Save tagging results to an Excel file."""
    output_file = os.path.join(folder_path, "suno_tags.xlsx")
    wb = Workbook()
    ws = wb.active
    ws.append(["Filename", "Tag", "Score"])
    for filename, tag_score_list in songs_tagged:
        for tag, score in tag_score_list:
            ws.append([filename, tag, round(score, 4)])
    wb.save(output_file)

# ========================
# Utility Functions
# ========================

def choose_folder():
    """Prompt the user to select an MP3 folder and store the path."""
    folder_path = filedialog.askdirectory(title="Choose MP3 Folder")
    folder_var.set(folder_path)

def update_console(text):
    """Append a line of text to the output console."""
    output_text.config(state='normal')
    output_text.insert(tk.END, f"{text}\n")
    output_text.see(tk.END)
    output_text.config(state='disabled')

def clear_console():
    """Clear the output console."""
    output_text.config(state='normal')
    output_text.delete(1.0, tk.END)
    output_text.config(state='disabled')

def update_progress(current, total, status=""):
    """Update the main progress bar and file status label."""
    progress_bar["value"] = current
    progress_label.config(text=f"{current}/{total} files tagged")
    timer_label.config(text=status)
    root.update_idletasks()

# ========================
# Tagging Controls
# ========================

def start_tagging():
    """Start the tagging process in a new thread after validating settings."""
    folder = folder_var.get()
    if not folder:
        messagebox.showerror("Error", "Please choose a folder.")
        return

    mode = mode_var.get()
    do_excel = mode in ("Export to Excel only", "Tag MP3s & Export to Excel")
    do_genre = mode in ("Tag MP3s only", "Tag MP3s & Export to Excel")
    excel_only = (mode == "Export to Excel only")

    if mode == "Pick a tagging mode...":
        messagebox.showerror("Error", "Please select a tagging mode.")
        return

    clear_console()
    progress_bar["value"] = 0
    progress_label.config(text="0/0 files tagged")
    timer_label.config(text="")

    input_length = float(duration_var.get())
    input_overlap = int(overlap_var.get()) / 100.0
    excel_path = custom_output_folder.get() if use_custom_output.get() else None

    # Launch processing in a thread
    threading.Thread(
        target=process_files,
        args=(folder, do_genre, do_excel, update_console, update_progress,
              var_top_tags_only.get(), excel_only, input_length,
              excel_path, input_overlap),
        daemon=True
    ).start()

def stop_tagging():
    """Trigger the stop flag to interrupt processing."""
    global stop_flag
    stop_flag = True

# Folder Selection
mp3_row = tk.Frame(tab_genre)
mp3_row.pack(padx=20, pady=5, anchor="w")
tk.Button(mp3_row, text="📂 Select MP3 Folder", command=choose_folder).grid(row=0, column=0, padx=(0,5))
folder_entry = tk.Entry(mp3_row, textvariable=folder_var, width=52)
folder_entry.grid(row=0, column=1)

# Duration Dropdown
tk.Label(tab_genre, text="Length of each audio chunk analyzed (in seconds):").pack(anchor="w", padx=20, pady=(10, 0))
duration_dropdown = ttk.Combobox(tab_genre, textvariable=duration_var, values=[str(i) for i in range(2, 61)], state="readonly", width=5)
duration_dropdown.pack(anchor="w", padx=20)

# Overlap Percentage
tk.Label(tab_genre, text="How much should chunks overlap (%):").pack(anchor="w", padx=20, pady=(10,0))
overlap_frame = tk.Frame(tab_genre)
overlap_frame.pack(anchor="w", padx=20)
overlap_slider = ttk.Scale(overlap_frame, from_=0, to=75, orient="horizontal",
                            command=lambda val: overlap_var.set(round(float(val)/25)*25),
                            variable=overlap_var, length=300)
overlap_slider.grid(row=0, column=0, columnspan=4)

# Overlap Tick Labels
overlap_tick_labels = []
for idx, label in enumerate(["0%", "25%", "50%", "75%"]):
    lbl = tk.Label(overlap_frame, text=label)
    lbl.grid(row=1, column=idx, padx=28)
    overlap_tick_labels.append(lbl)

# Mode Dropdown
tk.Label(tab_genre, text="What should we do with the tags?").pack(anchor="w", padx=20, pady=(10, 0))
mode_dropdown = ttk.Combobox(tab_genre, textvariable=mode_var, state="readonly", values=(
    "Pick a tagging mode...", "Export to Excel only", "Tag MP3s only", "Tag MP3s & Export to Excel"))
mode_dropdown.pack(anchor="w", padx=20)

# Custom Excel Output Folder
custom_checkbox = tk.Checkbutton(tab_genre, text="📁 Use custom Excel output folder",
                                 variable=use_custom_output)
custom_checkbox.pack(anchor="w", padx=20)

folder_frame = tk.Frame(tab_genre)
folder_frame.pack(pady=(0, 5), padx=20, anchor="w")

browse_button = tk.Button(folder_frame, text="📁 Select Excel Folder",
                          command=choose_excel_folder)
browse_button.grid(row=0, column=0, padx=(0, 5))

custom_output_entry = tk.Entry(folder_frame, textvariable=custom_output_folder, width=50)
custom_output_entry.grid(row=0, column=1)

# Top Tags Only Option
top_tags_checkbox = tk.Checkbutton(tab_genre, text="Only show top 3 tags", variable=var_top_tags_only)
top_tags_checkbox.pack(anchor="w", padx=20)

# Load config initially
trace_all()

# Defer loading config until everything is ready
root.after(50, load_config)

# Tagging Control Buttons
button_frame = tk.Frame(tab_genre)
button_frame.pack(pady=10)
tk.Button(button_frame, text="▶ Start Tagging", command=start_tagging,
          bg="#4CAF50", fg="white", padx=12, pady=5).grid(row=0, column=0, padx=10)
tk.Button(button_frame, text="⛔ Stop", command=stop_tagging,
          bg="#f44336", fg="white", padx=12, pady=5).grid(row=0, column=1, padx=10)

# Progress and Status
progress_bar = ttk.Progressbar(tab_genre, orient="horizontal", length=600, mode="determinate")
progress_bar.pack(pady=(5, 2))
progress_label = tk.Label(tab_genre, text="0/0 files tagged")
progress_label.pack()
timer_label = tk.Label(tab_genre, text="")
timer_label.pack(pady=(0, 10))

# Track Progress
current_track_label = tk.Label(tab_genre, text="")
current_track_label.pack(anchor="w", padx=20)
track_progress_label = tk.Label(tab_genre, text="Track Progress:")
track_progress_label.pack(anchor="w", padx=20)
track_progress_bar = ttk.Progressbar(tab_genre, orient="horizontal", length=600, mode="determinate")
track_progress_bar.pack(pady=(0, 10), padx=20)

# Output Console
output_text = scrolledtext.ScrolledText(tab_genre, wrap=tk.WORD, width=80, height=24, state='disabled')
output_text.pack(padx=20, pady=(0, 10))

# Startup message
output_text.config(state='normal')
output_text.insert(tk.END, "👋 Welcome to Dabbing Genre Tagger!\nReady to tag some bangers?\n\n")
output_text.config(state='disabled')

# -------------------------
# Pack and run
# -------------------------
tab_control.pack(expand=1, fill="both")

help_text = """
🎧 Genre Tagger
----------------
- Choose a folder of MP3s
- Select how long each window should be (e.g., 3s, 5s)
- Choose how much overlap you want (0–75%)
- Select what to do with the tags (Excel export, MP3 metadata, or both)
- Optionally use a custom Excel folder and only keep top 3 tags

✍️ Batch Renamer
-----------------
- Choose a folder
- Select "Use prefix" or "Use genre tag"
- Preview before renaming
- Confirm to batch rename all MP3s

🛠 Metadata Editor
-------------------
- Choose a folder
- Enter any values to apply across all MP3s
- Fields left blank are ignored
- Click "Apply Metadata" to write the info

📂 Song Browser
----------------
- Browse any folder with MP3s
- Click a file to view metadata
- Playback coming soon!

⚙️ Settings
------------
- Toggle dark mode
- Reset all settings to default

❓ Tips
-------
- You can stop tagging anytime
- Short files (less than 3 seconds) are skipped
- Output and logs go in the /results and /logs folders
"""

help_label = scrolledtext.ScrolledText(tab_help, wrap=tk.WORD, width=85, height=35)
help_label.pack(padx=20, pady=10)
help_label.insert(tk.END, help_text)
help_label.config(state="disabled")

about_text = """
🎵 About Dabbing Genre Tagger

This is a Python-powered MP3 genre tagger with bonus tools built in.

✨ Powered By:
- musicnn (AI genre recognition)
- mutagen (MP3 metadata editing)
- openpyxl (Excel file export)
- tkinter (GUI)
- numpy & scipy

🧠 AI Model:
musicnn is a deep convolutional neural network trained to detect genre from musical features using short chunks of audio.

💾 Safe and local:
- No internet access required
- Works 100% offline
- Your files are never uploaded

👨‍💻 Created by: MGT
🔢 Version: v1.0
📅 Year: 2025

💡 Fun Fact:
This tool simulates tagging audio in real-time, showing progress as if you were dabbing and listening.

"""

about_label = scrolledtext.ScrolledText(tab_about, wrap=tk.WORD, width=85, height=30)
about_label.pack(padx=20, pady=10)
about_label.insert(tk.END, about_text)
about_label.config(state="disabled")


root.protocol("WM_DELETE_WINDOW", lambda: (save_config(), root.destroy()))
root.mainloop()