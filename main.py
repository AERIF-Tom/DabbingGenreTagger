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

# ========================
# Configuration Management
# ========================

CONFIG_FILE = "tagger_config.ini"
config = configparser.ConfigParser()

def load_config():
    """Load settings from config file and apply them to the GUI."""
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
        settings = config["Settings"]
        folder_var.set(settings.get("mp3_folder", ""))
        mode_var.set(settings.get("tagging_mode", "Pick a tagging mode..."))
        var_top_tags_only.set(settings.getboolean("top_tags_only", False))
        use_custom_output.set(settings.getboolean("use_custom_output", False))
        custom_output_folder.set(settings.get("excel_output_folder", ""))
        duration_var.set(settings.get("duration", "3"))
        overlap_var.set(int(settings.get("overlap", "50")))
        global dark_mode
        dark_mode = settings.getboolean("dark_mode", False)
        apply_theme()

def save_config():
    """Save current GUI settings to config file."""
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

def reset_to_defaults():
    """Reset all settings to default values."""
    if messagebox.askyesno("Reset Settings", "Are you sure you want to reset all settings to default?"):
        folder_var.set("")
        mode_var.set("Pick a tagging mode...")
        var_top_tags_only.set(False)
        use_custom_output.set(False)
        custom_output_folder.set("")
        duration_var.set("3")
        overlap_var.set(50)
        global dark_mode
        dark_mode = False
        apply_theme()
        save_config()

def save_log_to_file():
    log_content = output_text.get("1.0", tk.END)
    file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt")])
    if file_path:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(log_content)

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

# ========================
# Global Variables
# ========================

dark_mode = False
stop_flag = False

# ========================
# GUI Initialization
# ========================

root = tk.Tk()
root.title("🎵 Dabbing Genre Tagger")
root.geometry("700x820")
root.resizable(False, False)

# ========================
# Help/About Menu
# ========================

def show_about():
    """Display a detailed Help/About dialog explaining how to use the tool."""
    about_text = (
        "Dabbing Genre Tagger\n\n"
        "This tool scans MP3 files and uses AI to tag their genre using the musicnn model.\n\n"
        "➡ Select MP3 Folder: Choose the folder containing your MP3s.\n"
        "➡ Length of each audio chunk: How many seconds of audio to analyze per chunk.\n"
        "➡ Overlap: How much to overlap audio chunks (in %).\n"
        "➡ What should we do with the tags?:\n"
        "   - Export to Excel only: Save tags to spreadsheet.\n"
        "   - Tag MP3s only: Update the genre metadata in the MP3s.\n"
        "   - Tag MP3s & Export to Excel: Do both!\n"
        "➡ Use custom Excel output folder: Save the Excel file somewhere specific.\n"
        "➡ Only show top 3 tags: Limits tagging to 3 genres per song.\n\n"
        "Start Tagging will analyze each track using musicnn.\n"
        "Tags will be displayed in the output box below, and optionally saved to Excel or embedded in the MP3.\n\n"
        "You can stop the process anytime using the Stop button.\n\n"
        "Dark mode is available if you're tagging while dabbing in the dark. 🌙💨\n"
    )
    messagebox.showinfo("About Dabbing Genre Tagger", about_text)

# Add a simple menu bar with an About option
menu_bar = tk.Menu(root)
help_menu = tk.Menu(menu_bar, tearoff=0)
help_menu.add_command(label="About", command=show_about)
menu_bar.add_cascade(label="Help", menu=help_menu)
root.config(menu=menu_bar)
help_menu.add_separator()
help_menu.add_command(label="Save Log", command=save_log_to_file)

# ========================
# Styling (Light/Dark Theme)
# ========================

style = ttk.Style()
style.theme_use('default')
style.configure("TCombobox", fieldbackground='white', background='white', foreground='black')
style.configure("TScale", troughcolor='SystemButtonFace')
style.configure("TProgressbar", background="#4CAF50", troughcolor='SystemButtonFace')

# ========================
# Tkinter Variable Setup
# ========================

folder_var = tk.StringVar()
mode_var = tk.StringVar(value="Pick a tagging mode...")
var_top_tags_only = tk.BooleanVar()
duration_var = tk.StringVar(value="3")
overlap_var = tk.IntVar(value=50)
use_custom_output = tk.BooleanVar()
custom_output_folder = tk.StringVar()

# Trace saves on updates
folder_var.trace_add("write", lambda *args: save_config())
mode_var.trace_add("write", on_mode_change)
var_top_tags_only.trace_add("write", lambda *args: save_config())
duration_var.trace_add("write", lambda *args: save_config())
overlap_var.trace_add("write", lambda *args: save_config())
use_custom_output.trace_add("write", lambda *args: save_config())
custom_output_folder.trace_add("write", lambda *args: save_config())

# Overlap tick mark labels for visual alignment
overlap_tick_labels = []

# ========================
# Apply Theme Function
# ========================

def apply_theme():
    """Apply dark or light theme styles to all widgets."""
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

    for lbl in overlap_tick_labels:
        lbl.configure(bg=bg, fg=fg)

    root.configure(bg=bg)
    for widget in root.winfo_children():
        try:
            widget.configure(bg=bg, fg=fg)
        except:
            pass
    for frame in [mp3_row, overlap_frame, folder_frame, button_frame]:
        frame.configure(bg=bg)
        for w in frame.winfo_children():
            try:
                w.configure(bg=bg, fg=fg)
            except:
                pass

    output_text.config(bg=output_bg, fg=output_fg, insertbackground=output_fg)
    custom_output_entry.config(bg=entry_bg if custom_output_entry['state'] == 'normal' else '#1e1e1e', fg=fg, insertbackground=fg)
    folder_entry.config(bg=entry_bg, fg=fg, insertbackground=fg)
    custom_checkbox.config(bg=bg, fg=fg, selectcolor=bg)
    top_tags_checkbox.config(bg=bg, fg=fg, selectcolor=bg)

# ========================
# Theme Toggle
# ========================

def toggle_dark_mode():
    """Switch between light and dark mode."""
    global dark_mode
    dark_mode = not dark_mode
    apply_theme()
    save_config()

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

# ========================
# Main GUI Layout
# ========================

# Title and global buttons
tk.Label(root, text="🎵 Dabbing Genre Tagger", font=("Helvetica", 16, "bold")).pack(pady=10)
tk.Button(root, text="🌓 Toggle Dark Mode", command=toggle_dark_mode).pack(pady=(0, 10))
tk.Button(root, text="🔄 Reset to Defaults", command=reset_to_defaults).pack(pady=(0, 10))

# MP3 Folder Selection
mp3_row = tk.Frame(root)
mp3_row.pack(padx=20, pady=5, anchor="w")
tk.Button(mp3_row, text="📂 Select MP3 Folder", command=choose_folder).grid(row=0, column=0, padx=(0,5))
folder_entry = tk.Entry(mp3_row, textvariable=folder_var, width=52)
folder_entry.grid(row=0, column=1)

# Input Window Duration
tk.Label(root, text="Length of each audio chunk analyzed (in seconds):").pack(anchor="w", padx=20, pady=(10, 0))
duration_dropdown = ttk.Combobox(root, textvariable=duration_var, values=[str(i) for i in range(2, 61)], state="readonly", width=5)
duration_dropdown.pack(anchor="w", padx=20)

# Overlap Percentage
tk.Label(root, text="How much should chunks overlap (%):").pack(anchor="w", padx=20, pady=(10,0))
overlap_frame = tk.Frame(root)
overlap_frame.pack(anchor="w", padx=20)
overlap_slider = ttk.Scale(overlap_frame, from_=0, to=75, orient="horizontal",
                            command=lambda val: overlap_var.set(round(float(val)/25)*25),
                            variable=overlap_var, length=300)
overlap_slider.grid(row=0, column=0, columnspan=4)

# Slider tick labels
for idx, label in enumerate(["0%", "25%", "50%", "75%"]):
    lbl = tk.Label(overlap_frame, text=label)
    lbl.grid(row=1, column=idx, padx=28)
    overlap_tick_labels.append(lbl)

# Mode Dropdown
tk.Label(root, text="What should we do with the tags?").pack(anchor="w", padx=20, pady=(10, 0))
mode_dropdown = ttk.Combobox(root, textvariable=mode_var, state="readonly", values=(
    "Pick a tagging mode...", "Export to Excel only", "Tag MP3s only", "Tag MP3s & Export to Excel"))
mode_dropdown.pack(anchor="w", padx=20)

# Custom Excel Output Folder
custom_checkbox = tk.Checkbutton(root, text="📁 Use custom Excel output folder",
                                 variable=use_custom_output, command=update_gui_visibility)
custom_checkbox.pack(anchor="w", padx=20)

folder_frame = tk.Frame(root)
folder_frame.pack(pady=(0, 5), padx=20, anchor="w")

browse_button = tk.Button(folder_frame, text="📁 Select Excel Folder",
                          command=lambda: custom_output_folder.set(
                              filedialog.askdirectory(title="Choose Excel Output Folder")))
browse_button.grid(row=0, column=0, padx=(0, 5))

custom_output_entry = tk.Entry(folder_frame, textvariable=custom_output_folder, width=50)
custom_output_entry.grid(row=0, column=1)

# Top Tags Only Option
top_tags_checkbox = tk.Checkbutton(root, text="Only show top 3 tags", variable=var_top_tags_only)
top_tags_checkbox.pack(anchor="w", padx=20)

# Tagging Control Buttons
button_frame = tk.Frame(root)
button_frame.pack(pady=10)
tk.Button(button_frame, text="▶ Start Tagging", command=start_tagging,
          bg="#4CAF50", fg="white", padx=12, pady=5).grid(row=0, column=0, padx=10)
tk.Button(button_frame, text="⛔ Stop", command=stop_tagging,
          bg="#f44336", fg="white", padx=12, pady=5).grid(row=0, column=1, padx=10)

# Progress and Status Indicators
progress_bar = ttk.Progressbar(root, orient="horizontal", length=600, mode="determinate")
progress_bar.pack(pady=(5, 2))
progress_label = tk.Label(root, text="0/0 files tagged")
progress_label.pack()
timer_label = tk.Label(root, text="")
timer_label.pack(pady=(0, 10))

# Per-track Progress Bar
current_track_label = tk.Label(root, text="")
current_track_label.pack(anchor="w", padx=20)
track_progress_label = tk.Label(root, text="Track Progress:")
track_progress_label.pack(anchor="w", padx=20)
track_progress_bar = ttk.Progressbar(root, orient="horizontal", length=600, mode="determinate")
track_progress_bar.pack(pady=(0, 10), padx=20)

# Output Console
output_text = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=80, height=24, state='disabled')
output_text.pack(padx=20, pady=(0, 10))

# Apply Theme, Load Settings, and Run
apply_theme()
load_config()

# Startup message
output_text.config(state='normal')
output_text.insert(tk.END, "👋 Welcome to Dabbing Genre Tagger!\nReady to tag some bangers?\n\n")
output_text.config(state='disabled')

root.protocol("WM_DELETE_WINDOW", lambda: (save_config(), root.destroy()))
root.mainloop()
