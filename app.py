"""CLIPFARM desktop workstation, Windows."""
import hashlib
import json
import os
from pathlib import Path
import queue
import threading
from tkinter import filedialog, messagebox
from tkinterdnd2 import TkinterDnD, DND_FILES, COPY, REFUSE_DROP
import customtkinter as ctk

if os.name == 'nt':
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('Clipfarm.Desktop')

from engine import Pipeline, Cancelled, ROOT, validate_options, validate_clips, minute_clips

from ui_layout import StudioUI, BG
from brand import ASSETS
from transcripts import existing_transcript, read_transcript, remember_transcript, validate_segments
from engine import subtitle_text

ctk.set_appearance_mode('light')


class App(StudioUI, ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        super().__init__()
        self.TkdndVersion = TkinterDnD._require(self)
        self.title('Clipfarm — Studio klipów')
        # Set the same branded icon in the title bar, taskbar and Windows switcher.
        self.after(250, lambda: self.iconbitmap(str(ASSETS / 'clipfarm.ico')))
        self.geometry('1320x880')
        self.minsize(1100, 780)
        self.configure(fg_color=BG)
        self.events = queue.Queue()
        self.pipeline = None
        self.worker = None
        self.source = None
        self.metadata = None
        self.segments = []
        self.transcript_origin = ''
        self.clips = []
        self.rows = []
        self.work = None
        self.destination = ROOT / 'exports'
        self.controls = []
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)
        self.build_ui()
        self.register_source_drop(self.source_panel)
        self.after(100, self.poll)
        self.protocol('WM_DELETE_WINDOW', self.close)




    def log(self, text):
        self.events.put(('log', text))

    def poll(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == 'log':
                    self.status.configure(text=value[:110])
                    self.logs.configure(state='normal')
                    self.logs.insert('end', value + '\n')
                    self.logs.see('end')
                    self.logs.configure(state='disabled')
                elif kind == 'done':
                    self.set_busy(False)
                    value()
                elif kind == 'error':
                    self.set_busy(False)
                    self.status.configure(text='Zadanie nie powiodło się. Szczegóły w komunikacie.')
                    messagebox.showerror('CLIPFARM', value)
                elif kind == 'cancelled':
                    self.set_busy(False)
                    self.status.configure(text='Zadanie przerwane. Możesz uruchomić je ponownie.')
        except queue.Empty:
            pass
        self.after(100, self.poll)

    def set_busy(self, busy):
        for widget in self.controls:
            widget.configure(state='disabled' if busy else 'normal')
        for row in self.rows:
            for widget in row['widgets']:
                widget.configure(state='disabled' if busy else 'normal')
        self.cancel_button.configure(state='normal' if busy else 'disabled')
        if busy:
            self.progress.configure(mode='indeterminate')
            self.progress.start()
        else:
            self.progress.stop()
            self.progress.configure(mode='determinate')
            self.progress.set(0)
            self.pipeline = None
        self.refresh_actions()

    def task(self, operation, complete):
        self.pipeline = Pipeline(self.log)
        pipeline = self.pipeline
        self.set_busy(True)
        def run():
            try:
                result = operation(pipeline)
                self.events.put(('done', lambda: complete(result)))
            except Cancelled:
                self.events.put(('cancelled', None))
            except Exception as exc:
                self.log(str(exc))
                self.events.put(('error', str(exc)))
        self.worker = threading.Thread(target=run, daemon=True)
        self.worker.start()

    def choose_source(self):
        filename = filedialog.askopenfilename(title='Wybierz film', filetypes=[
            ('Filmy', '*.mp4 *.mkv *.mov *.avi *.webm *.m4v'), ('Wszystkie pliki', '*.*')])
        if filename:
            self.import_source(filename)

    def import_source(self, filename):
        if self.pipeline is not None:
            return
        try:
            self.load_source(filename)
            self.clips = []
            self.render_clips()
            self.status.configure(text='Film dodany. Kliknij „Znajdź fragmenty”, aby rozpocząć analizę.')
        except Exception as exc:
            messagebox.showerror('Nie można otworzyć filmu', str(exc))

    def register_source_drop(self, widget):
        # CTk paints labels/buttons on child windows; the whole source panel accepts drops.
        widget.drop_target_register(DND_FILES)
        widget.dnd_bind('<<DropEnter>>', self.source_drop_enter)
        widget.dnd_bind('<<DropPosition>>', self.source_drop_enter)
        widget.dnd_bind('<<DropLeave>>', self.source_drop_leave)
        widget.dnd_bind('<<Drop>>', self.source_drop)
        for child in widget.winfo_children():
            self.register_source_drop(child)

    def source_drop_enter(self, event):
        if self.pipeline is not None:
            self.source_drop_leave(event)
            return REFUSE_DROP
        self.source_panel.configure(border_width=2, border_color='#0071e3', fg_color='#eef6ff')
        return COPY

    def source_drop_leave(self, event):
        self.source_panel.configure(border_width=0, fg_color='#ffffff')
        return COPY

    def source_drop(self, event):
        self.source_drop_leave(event)
        if self.pipeline is not None:
            self.status.configure(text='Poczekaj na zakończenie zadania lub przerwij je przed zmianą filmu.')
            return REFUSE_DROP
        try:
            files = self.tk.splitlist(event.data)
            if len(files) != 1:
                raise ValueError('Przeciągnij jeden film naraz.')
            path = Path(files[0])
            if not path.is_file() or path.suffix.lower() not in {'.mp4', '.mkv', '.mov', '.avi', '.webm', '.m4v'}:
                raise ValueError('Upuść plik filmu: MP4, MKV, MOV, AVI, WEBM lub M4V.')
        except Exception as exc:
            self.status.configure(text=str(exc))
            return REFUSE_DROP
        # Return the native drop action before reading the video and creating its thumbnail.
        self.after_idle(lambda: self.import_source(path))
        return COPY

    def load_source(self, filename):
        source = Path(filename).resolve()
        metadata = Pipeline.probe(source)
        identity = hashlib.sha256(str(source).encode()).hexdigest()[:16]
        self.source, self.metadata = source, metadata
        self.work = ROOT / 'projects' / identity
        self.work.mkdir(parents=True, exist_ok=True)
        self.segments, self.transcript_origin = existing_transcript(source, self.work, metadata['duration'])
        self.source_label.configure(text=source.name[:60])
        self.update_framing_info()
        self.update_source_preview()

    def attach_transcript(self):
        if not self.source or self.pipeline is not None:
            return
        filename = filedialog.askopenfilename(title='Wczytaj transkrypcję do tego filmu',
            initialdir=str(self.source.parent), filetypes=[('Transkrypcja', '*.srt *.vtt *.json')])
        if filename:
            try:
                segments = read_transcript(filename, self.metadata['duration'])
                remember_transcript(self.source, self.work, segments)
                self.segments, self.transcript_origin = segments, Path(filename).name
                self.refresh_actions()
                self.status.configure(text='Transkrypcja wczytana. Możesz szukać klipów bez ponownego rozpoznawania mowy.')
            except Exception as exc:
                messagebox.showerror('Nie można wczytać transkrypcji', str(exc))

    def download_transcript(self):
        if not self.segments or self.pipeline is not None:
            return
        filename = filedialog.asksaveasfilename(title='Zapisz transkrypcję', initialdir=str(self.source.parent),
            initialfile=self.source.stem + '.srt', defaultextension='.srt',
            filetypes=[('Napisy SRT', '*.srt'), ('Transkrypcja JSON', '*.json')])
        if filename:
            try:
                text = (json.dumps({'version': 1, 'source': str(self.source), 'segments': self.segments},
                                   ensure_ascii=False, indent=2) if Path(filename).suffix.lower() == '.json'
                        else subtitle_text(self.segments, 0, self.metadata['duration']))
                Path(filename).write_text(text, encoding='utf-8')
                self.status.configure(text=f'Transkrypcja zapisana: {Path(filename).name}.')
            except Exception as exc:
                messagebox.showerror('Nie można zapisać transkrypcji', str(exc))

    def transcribe_only(self):
        if not self.source or self.pipeline is not None:
            return
        if not self.metadata['audio']:
            messagebox.showerror('Brak dźwięku', 'Ten film nie zawiera ścieżki audio.')
            return
        source, work = self.source, self.work
        size = {'Szybka': 'tiny', 'Zrównoważona': 'small', 'Dokładna': 'medium', 'Najdokładniejsza': 'large-v3'}[self.whisper.get()]
        def complete(rows):
            self.segments, self.transcript_origin = rows, 'Whisper lokalnie'
            self.refresh_actions()
            self.status.configure(text='Transkrypcja gotowa. Pobierz ją lub rozpocznij wybór klipów.')
        self.task(lambda p: p.transcribe(source, work, size), complete)

    def analyze(self):
        if not self.source:
            self.choose_source()
            if not self.source:
                return
        try:
            count, minimum, maximum = int(self.count.get()), float(self.minimum.get()), float(self.maximum.get())
            film_mode = self.mode.get() == 'Film · minuty'
            if not film_mode:
                validate_options(count, minimum, maximum)
            if not self.metadata['audio'] and not self.segments and (not film_mode or bool(self.burn.get())):
                raise ValueError('Ten film nie ma dźwięku. Ta wersja wybiera fragmenty na podstawie mowy.')
        except ValueError as exc:
            messagebox.showerror('Sprawdź ustawienia', str(exc))
            return
        size = {'Szybka': 'tiny', 'Zrównoważona': 'small', 'Dokładna': 'medium', 'Najdokładniejsza': 'large-v3'}[self.whisper.get()]
        brief = self.brief.get('1.0', 'end').strip()
        source, work, duration = self.source, self.work, self.metadata['duration']
        existing = list(self.segments)
        def operation(pipeline):
            if existing:
                pipeline.log('Używam gotowej transkrypcji — bez ponownego rozpoznawania mowy.')
                segments = existing
            elif film_mode and not bool(self.burn.get()):
                pipeline.log('Tryb Film · minuty: pomijam transkrypcję, bo napisy są wyłączone.')
                segments = []
            else:
                segments = pipeline.transcribe(source, work, size)
            clips = minute_clips(duration) if film_mode else pipeline.select(segments, duration, count, minimum, maximum, brief, work)
            return segments, clips
        def complete(result):
            self.segments, self.clips = result
            self.transcript_origin = self.transcript_origin or 'Whisper lokalnie'
            self.render_clips()
            self.write_project(self.work / 'project.json')
            self.status.configure(text=f'Podzielono cały film na {len(self.clips)} części.' if film_mode else f'Znaleziono {len(self.clips)} fragmentów. Sprawdź czasy i wybierz klipy do eksportu.')
        self.task(operation, complete)


    def edited_clips(self, selected_only=False):
        result = []
        for clip, row in zip(self.clips, self.rows):
            if selected_only and not row['selected'].get():
                continue
            result.append({**clip, 'start': float(row['start'].get().replace(',', '.')),
                           'end': float(row['end'].get().replace(',', '.'))})
        return validate_clips(result, self.metadata['duration'], 1, self.metadata['duration'], strict=True)

    def preview(self, index):
        try:
            clip = self.edited_clips()[index]
        except ValueError as exc:
            messagebox.showerror('Sprawdź czasy', str(exc))
            return
        folder = self.work / 'preview'
        vertical = self.format.get() == 'Pionowy 9:16'
        framing = self.framing_mode()
        light_color, speed_up, mirror = bool(self.light_color.get()), bool(self.speed_up.get()), bool(self.mirror.get())
        burn = bool(self.burn.get())
        def render(p):
            files = p.export(self.source, [clip], self.segments, folder,
                             vertical=vertical, burn=burn, framing=framing, timing_work=self.work,
                             light_color=light_color, speed_up=speed_up, mirror=mirror)
            return files, p.caption_segments
        def complete(result):
            files, self.segments = result
            os.startfile(files[0])
        self.task(render, complete)

    def export(self):
        if not self.clips:
            messagebox.showinfo('Najpierw analiza', 'Wybierz film i znajdź fragmenty do eksportu.')
            return
        try:
            clips = self.edited_clips(True)
            if not clips:
                raise ValueError('Zaznacz przynajmniej jeden klip.')
        except ValueError as exc:
            messagebox.showerror('Sprawdź klipy', str(exc))
            return
        folder = filedialog.askdirectory(title='Gdzie zapisać klipy?', initialdir=str(self.destination))
        if not folder:
            return
        self.destination = Path(folder)
        vertical, burn = self.format.get() == 'Pionowy 9:16', bool(self.burn.get())
        framing = self.framing_mode()
        light_color, speed_up, mirror = bool(self.light_color.get()), bool(self.speed_up.get()), bool(self.mirror.get())
        def complete(result):
            files, self.segments = result
            self.status.configure(text=f'Zapisano {len(files)} klipów w {self.destination}.')
            os.startfile(str(self.destination))
        def render(p):
            files = p.export(self.source, clips, self.segments, folder, vertical, burn,
                             framing=framing, timing_work=self.work, light_color=light_color,
                             speed_up=speed_up, mirror=mirror)
            return files, p.caption_segments
        self.task(render, complete)

    def write_project(self, path):
        clips = self.edited_clips() if self.rows else self.clips
        data = {'version': 2, 'source': str(self.source), 'segments': self.segments, 'clips': clips,
                'settings': {'format': self.format.get(), 'framing': self.cropping.get(), 'burn': bool(self.burn.get()),
                             'mode': self.mode.get(), 'light_color': bool(self.light_color.get()),
                             'speed_up': bool(self.speed_up.get()), 'mirror': bool(self.mirror.get())}}
        Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    def save_project(self):
        if not self.source:
            return
        filename = filedialog.asksaveasfilename(title='Zapisz projekt', defaultextension='.json',
                                               initialfile='clipfarm-project.json', filetypes=[('Projekt', '*.json')])
        if filename:
            try:
                self.write_project(filename)
                self.status.configure(text='Projekt zapisany. Możesz wrócić do niego później.')
            except Exception as exc:
                messagebox.showerror('Nie można zapisać projektu', str(exc))

    def open_project(self):
        filename = filedialog.askopenfilename(title='Otwórz projekt CLIPFARM', filetypes=[('Projekt', '*.json')])
        if filename:
            try:
                data = json.loads(Path(filename).read_text(encoding='utf-8'))
                self.load_source(data['source'])
                segments = validate_segments(data['segments'], self.metadata['duration']) if data['segments'] else self.segments
                clips = validate_clips(data['clips'], self.metadata['duration'], 1, self.metadata['duration'], strict=True)
                self.segments, self.clips = segments, clips
                self.transcript_origin = 'projekt' if segments else ''
                if segments:
                    remember_transcript(self.source, self.work, segments)
                settings = data.get('settings', {})
                if settings.get('format') in ('Pionowy 9:16', 'Oryginalny'):
                    self.format.set(settings['format'])
                if settings.get('framing') in self.cropping.cget('values'):
                    self.cropping.set(settings['framing'])
                if settings.get('mode') in self.mode.cget('values'):
                    self.mode.set(settings['mode'])
                self.burn.select() if settings.get('burn', True) else self.burn.deselect()
                self.light_color.select() if settings.get('light_color') else self.light_color.deselect()
                self.speed_up.select() if settings.get('speed_up') else self.speed_up.deselect()
                self.mirror.select() if settings.get('mirror') else self.mirror.deselect()
                self.update_framing_info()
                self.update_mode_info()
                self.render_clips()
                self.status.configure(text='Wczytano projekt. Możesz poprawić klipy i wyeksportować je ponownie.')
            except Exception as exc:
                messagebox.showerror('Nie można otworzyć projektu', str(exc))

    def open_destination(self):
        self.destination.mkdir(parents=True, exist_ok=True)
        os.startfile(str(self.destination))

    def cancel_task(self):
        if self.pipeline:
            self.pipeline.cancel.set()
            self.status.configure(text='Przerywanie… transkrypcja zatrzyma się po bieżącym fragmencie.')

    def close(self):
        if self.pipeline:
            if not messagebox.askyesno('Trwa zadanie', 'Przerwać zadanie i zamknąć CLIPFARM?'):
                return
            self.pipeline.cancel.set()
            self.withdraw()
            self.after(300, self.wait_close)
        else:
            self.destroy()

    def wait_close(self):
        if self.worker and self.worker.is_alive():
            self.after(300, self.wait_close)
        else:
            self.destroy()


if __name__ == '__main__':
    App().mainloop()
