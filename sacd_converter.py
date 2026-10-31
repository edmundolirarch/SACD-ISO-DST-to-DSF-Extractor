import os
import sys
import subprocess
import threading
import shutil
import tempfile
import urllib.request
import urllib.parse
import json
from pathlib import Path
from tkinter import messagebox
import tkinter as tk

import customtkinter as ctk
from mutagen.dsf import DSF
from mutagen.id3 import ID3, TIT2, TPE1, TALB, APIC, TRCK

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class MusicBrainzSearchWindow(ctk.CTkToplevel):
    def __init__(self, parent, artist, album, callback):
        super().__init__(parent)
        self.title("Búsqueda en MusicBrainz")
        self.geometry("600x400")
        self.callback = callback
        
        # UI Elements
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        self.lbl_status = ctk.CTkLabel(self, text="Buscando...")
        self.lbl_status.grid(row=0, column=0, pady=10)
        
        self.listbox = tk.Listbox(self, font=("System", 11))
        self.listbox.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        
        self.btn_select = ctk.CTkButton(self, text="Seleccionar Versión", command=self._on_select, state="disabled")
        self.btn_select.grid(row=2, column=0, pady=10)
        
        self.results = []
        
        # Run search in thread
        threading.Thread(target=self._search, args=(artist, album), daemon=True).start()
        
    def _search(self, artist, album):
        try:
            # Query MusicBrainz API
            query = f'artist:"{artist}" AND release:"{album}"'
            url = f"https://musicbrainz.org/ws/2/release/?query={urllib.parse.quote(query)}&fmt=json"
            
            req = urllib.request.Request(url, headers={'User-Agent': 'SACDExtractorApp/1.0 ( local@example.com )'})
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                
            releases = data.get('releases', [])
            if not releases:
                self.after(0, lambda: self.lbl_status.configure(text="No se encontraron resultados."))
                return
                
            self.results = releases
            self.after(0, self._populate_list)
        except Exception as e:
            self.after(0, lambda: self.lbl_status.configure(text=f"Error: {str(e)}"))

    def _populate_list(self):
        self.lbl_status.configure(text="Seleccione la versión correcta del álbum:")
        for r in self.results:
            title = r.get('title', 'Unknown')
            date = r.get('date', 'Unknown Date')
            country = r.get('country', 'Unknown Country')
            track_count = r.get('track-count', '?')
            display_text = f"{title} ({date}) - {country} - {track_count} pistas"
            self.listbox.insert(tk.END, display_text)
        self.btn_select.configure(state="normal")

    def _on_select(self):
        selection = self.listbox.curselection()
        if not selection: return
        
        idx = selection[0]
        release_id = self.results[idx]['id']
        
        self.btn_select.configure(state="disabled")
        self.lbl_status.configure(text="Obteniendo lista de pistas...")
        
        threading.Thread(target=self._get_tracks, args=(release_id,), daemon=True).start()
        
    def _get_tracks(self, release_id):
        try:
            url = f"https://musicbrainz.org/ws/2/release/{release_id}?inc=recordings&fmt=json"
            req = urllib.request.Request(url, headers={'User-Agent': 'SACDExtractorApp/1.0 ( local@example.com )'})
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                
            tracks = []
            # Navigate MusicBrainz JSON structure for tracks
            for media in data.get('media', []):
                for track in media.get('tracks', []):
                    num = track.get('position', len(tracks)+1)
                    title = track.get('title', 'Unknown Track')
                    tracks.append({"num": int(num), "title": title})
                    
            self.after(0, lambda: self.callback(tracks))
            self.after(0, self.destroy)
        except Exception as e:
            self.after(0, lambda: self.lbl_status.configure(text=f"Error obteniendo pistas: {str(e)}"))


class SACDConverterApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("SACD ISO to DSF Stereo Extractor")
        self.geometry("900x800")
        self.minsize(800, 700)
        
        self.iso_path = tk.StringVar()
        self.dest_path = tk.StringVar()
        self.cover_path = tk.StringVar()
        self.album_name = tk.StringVar(value="Álbum Desconocido")
        self.artist_name = tk.StringVar(value="Artista Desconocido")
        self.tracks_data = [] 
        self.is_processing = False
        
        self.creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        self._build_ui()
        
    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        
        # RUTAS
        frame_paths = ctk.CTkFrame(self)
        frame_paths.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        frame_paths.grid_columnconfigure(1, weight=1)
        
        ctk.CTkButton(frame_paths, text="Seleccionar Archivo ISO / DST", command=self._select_iso, width=200).grid(row=0, column=0, padx=10, pady=10)
        ctk.CTkLabel(frame_paths, textvariable=self.iso_path, anchor="w").grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        
        ctk.CTkButton(frame_paths, text="Seleccionar Carpeta Destino", command=self._select_dest, width=200).grid(row=1, column=0, padx=10, pady=10)
        ctk.CTkLabel(frame_paths, textvariable=self.dest_path, anchor="w").grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        # METADATOS GENERALES Y BUSQUEDA
        frame_meta = ctk.CTkFrame(self)
        frame_meta.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        frame_meta.grid_columnconfigure(1, weight=1)
        frame_meta.grid_columnconfigure(3, weight=1)
        
        ctk.CTkLabel(frame_meta, text="Álbum:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        ctk.CTkEntry(frame_meta, textvariable=self.album_name).grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        
        ctk.CTkLabel(frame_meta, text="Artista Principal:").grid(row=0, column=2, padx=10, pady=10, sticky="w")
        ctk.CTkEntry(frame_meta, textvariable=self.artist_name).grid(row=0, column=3, padx=10, pady=10, sticky="ew")
        
        ctk.CTkButton(frame_meta, text="Buscar Nombres Online", command=self._search_online, width=180, fg_color="#2b8a3e", hover_color="#2b8a3e").grid(row=0, column=4, padx=10, pady=10)
        
        ctk.CTkButton(frame_meta, text="Cargar Portada (Local)", command=self._select_cover, width=180).grid(row=1, column=4, padx=10, pady=10)
        ctk.CTkLabel(frame_meta, textvariable=self.cover_path, anchor="e").grid(row=1, column=1, columnspan=3, padx=10, pady=10, sticky="ew")

        # TABLA DE PISTAS
        self.frame_tracks = ctk.CTkScrollableFrame(self, label_text="Pistas Detectadas (Edite Artista y Título si es necesario)")
        self.frame_tracks.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        self.frame_tracks.grid_columnconfigure(1, weight=1)
        self.frame_tracks.grid_columnconfigure(2, weight=1)
        
        # CONTROLES MANUALES
        frame_controls = ctk.CTkFrame(self, fg_color="transparent")
        frame_controls.grid(row=3, column=0, padx=20, pady=(0, 5), sticky="e")
        
        ctk.CTkButton(frame_controls, text="+ Añadir Pista", command=self._add_single_track, width=120).pack(side="left", padx=5)
        ctk.CTkButton(frame_controls, text="- Quitar Pista", command=self._remove_single_track, width=120).pack(side="left", padx=5)

        # PROGRESO Y EJECUCIÓN
        frame_exec = ctk.CTkFrame(self)
        frame_exec.grid(row=4, column=0, padx=20, pady=(10, 20), sticky="ew")
        frame_exec.grid_columnconfigure(0, weight=1)
        
        self.btn_start = ctk.CTkButton(frame_exec, text="INICIAR CONVERSIÓN", command=self._start_process, height=40, font=("System", 16, "bold"))
        self.btn_start.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="ew")
        
        self.lbl_status_album = ctk.CTkLabel(frame_exec, text="Álbum: Esperando...")
        self.lbl_status_album.grid(row=1, column=0, padx=20, pady=0, sticky="w")
        self.progress_album = ctk.CTkProgressBar(frame_exec)
        self.progress_album.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.progress_album.set(0)
        
        self.lbl_status_track = ctk.CTkLabel(frame_exec, text="Pista actual: Esperando...")
        self.lbl_status_track.grid(row=3, column=0, padx=20, pady=0, sticky="w")
        self.progress_track = ctk.CTkProgressBar(frame_exec)
        self.progress_track.grid(row=4, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.progress_track.set(0)

    def _get_sacd_extract_path(self):
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, 'sacd_extract.exe')
        return 'sacd_extract.exe' 

    def _select_iso(self):
        filetypes = (("SACD ISO files", "*.iso"), ("All files", "*.*"))
        path = tk.filedialog.askopenfilename(title="Seleccionar SACD ISO", filetypes=filetypes)
        if path:
            self.iso_path.set(path)
            self._scan_iso()

    def _select_dest(self):
        path = tk.filedialog.askdirectory(title="Seleccionar Carpeta de Destino")
        if path:
            self.dest_path.set(path)

    def _select_cover(self):
        filetypes = (("Imágenes", "*.jpg *.jpeg *.png"), ("All files", "*.*"))
        path = tk.filedialog.askopenfilename(title="Seleccionar Portada", filetypes=filetypes)
        if path:
            self.cover_path.set(path)

    def _clear_tracks_ui(self):
        for widget in self.frame_tracks.winfo_children():
            widget.destroy()
        self.tracks_data.clear()

    def _scan_iso(self):
        if not self.iso_path.get(): return
        
        self._clear_tracks_ui()
        self.lbl_status_album.configure(text="Escaneando ISO...")
        
        exe_path = self._get_sacd_extract_path()
        if not os.path.exists(exe_path):
            messagebox.showerror("Error", f"No se encontró {exe_path}. Asegúrese de que el binario esté junto al script.")
            return

        def run_scan():
            try:
                cmd = [exe_path, "-i", self.iso_path.get()]
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=self.creationflags)
                stdout, stderr = process.communicate()
                
                tracks_found = []
                album_title = "Álbum Desconocido"
                artist_name = "Artista Desconocido"
                
                lines = stdout.split('\n')
                current_track_num = 0
                for line in lines:
                    line = line.strip()
                    if "Title:" in line and current_track_num == 0:
                        album_title = line.split("Title:", 1)[1].strip()
                    elif "Artist:" in line and current_track_num == 0:
                        artist_name = line.split("Artist:", 1)[1].strip()
                    elif "Track:" in line:
                        current_track_num += 1
                        tracks_found.append({"num": current_track_num, "title": f"Pista {current_track_num:02d}", "artist": artist_name})
                
                if not tracks_found:
                    for i in range(1, 16): 
                        tracks_found.append({"num": i, "title": f"Pista {i:02d}", "artist": artist_name})

                self.after(0, self._populate_tracks_ui, tracks_found, album_title, artist_name)
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error de escaneo", str(e)))
            finally:
                self.after(0, lambda: self.lbl_status_album.configure(text="Álbum: Esperando..."))

        threading.Thread(target=run_scan, daemon=True).start()

    def _populate_tracks_ui(self, tracks, album_title, artist_title):
        self.album_name.set(album_title)
        self.artist_name.set(artist_title)
        
        ctk.CTkLabel(self.frame_tracks, text="#", font=("System", 12, "bold")).grid(row=0, column=0, padx=5, pady=5)
        ctk.CTkLabel(self.frame_tracks, text="Título de la Canción", font=("System", 12, "bold")).grid(row=0, column=1, padx=5, pady=5, sticky="w")
        ctk.CTkLabel(self.frame_tracks, text="Artista", font=("System", 12, "bold")).grid(row=0, column=2, padx=5, pady=5, sticky="w")

        for i, track in enumerate(tracks):
            self._create_track_row(track['num'], track['title'], track['artist'])

    def _create_track_row(self, num, title, artist):
        row = len(self.tracks_data) + 1
        
        lbl_num = ctk.CTkLabel(self.frame_tracks, text=f"{num:02d}")
        lbl_num.grid(row=row, column=0, padx=5, pady=2)
        
        var_title = tk.StringVar(value=title)
        ent_title = ctk.CTkEntry(self.frame_tracks, textvariable=var_title)
        ent_title.grid(row=row, column=1, padx=5, pady=2, sticky="ew")
        
        var_artist = tk.StringVar(value=artist)
        ent_artist = ctk.CTkEntry(self.frame_tracks, textvariable=var_artist)
        ent_artist.grid(row=row, column=2, padx=5, pady=2, sticky="ew")
        
        self.tracks_data.append({
            "num": num,
            "lbl": lbl_num,
            "ent_title": ent_title,
            "ent_artist": ent_artist,
            "var_title": var_title,
            "var_artist": var_artist
        })

    def _add_single_track(self):
        new_num = len(self.tracks_data) + 1
        title = f"Pista {new_num:02d}"
        artist = self.artist_name.get()
        if self.tracks_data:
            artist = self.tracks_data[-1]["var_artist"].get()
        self._create_track_row(new_num, title, artist)

    def _remove_single_track(self):
        if not self.tracks_data: return
        track = self.tracks_data.pop()
        track["lbl"].destroy()
        track["ent_title"].destroy()
        track["ent_artist"].destroy()

    def _search_online(self):
        artist = self.artist_name.get().strip()
        album = self.album_name.get().strip()
        
        if not artist or not album:
            messagebox.showwarning("Faltan datos", "Debe ingresar al menos el Nombre del Álbum y el Artista Principal para buscar.")
            return
            
        MusicBrainzSearchWindow(self, artist, album, self._on_online_results)

    def _on_online_results(self, tracks):
        # Update UI with online results
        self._clear_tracks_ui()
        artist_name = self.artist_name.get().strip()
        album_name = self.album_name.get().strip()
        
        formatted_tracks = []
        for t in tracks:
            formatted_tracks.append({"num": t["num"], "title": t["title"], "artist": artist_name})
            
        self._populate_tracks_ui(formatted_tracks, album_name, artist_name)
        messagebox.showinfo("Búsqueda Exitosa", f"Se han cargado {len(tracks)} pistas desde MusicBrainz.")

    def _check_conflicts(self):
        dest_dir = self.dest_path.get()
        if not dest_dir:
            return False
            
        for track in self.tracks_data:
            num = track["num"]
            title = track["var_title"].get().strip()
            
            safe_title = "".join(c for c in title if c not in r'\/*?:"<>|')
            
            # Formato CORTO solicitado: "01 - Título.dsf"
            filename = f"{num:02d} - {safe_title}.dsf"
            filepath = os.path.join(dest_dir, filename)
            
            if os.path.exists(filepath):
                return filepath
        return None

    def _start_process(self):
        if self.is_processing: return
        if not self.iso_path.get() or not self.dest_path.get():
            messagebox.showwarning("Faltan rutas", "Seleccione el archivo ISO y la carpeta de destino.")
            return
            
        conflict = self._check_conflicts()
        if conflict:
            messagebox.showerror("Conflicto Detectado", f"El archivo ya existe:\n{conflict}\n\nProceso cancelado. Por favor, cambie la carpeta de destino o los nombres.")
            return

        self.is_processing = True
        self.btn_start.configure(state="disabled")
        self.progress_album.set(0)
        self.progress_track.set(0)
        
        threading.Thread(target=self._process_extraction, daemon=True).start()

    def _process_extraction(self):
        exe_path = self._get_sacd_extract_path()
        iso_file = self.iso_path.get()
        final_dest = self.dest_path.get()
        album = self.album_name.get().strip()
        cover_img = self.cover_path.get()
        
        total_tracks = len(self.tracks_data)
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                for idx, track in enumerate(self.tracks_data):
                    track_num = track["num"]
                    title = track["var_title"].get().strip()
                    artist = track["var_artist"].get().strip()
                    
                    safe_title = "".join(c for c in title if c not in r'\/*?:"<>|')
                    
                    # Formato CORTO: 01 - Título.dsf
                    final_filename = f"{track_num:02d} - {safe_title}.dsf"
                    final_filepath = os.path.join(final_dest, final_filename)
                    
                    self.after(0, lambda i=idx, t=total_tracks: self.lbl_status_album.configure(text=f"Álbum: Procesando pista {i+1} de {t} ({int((i/t)*100)}%)"))
                    self.after(0, lambda i=idx, t=total_tracks: self.progress_album.set(i/t))
                    self.after(0, lambda p=title: self.lbl_status_track.configure(text=f"Extrayendo y convirtiendo: {p}..."))
                    
                    if idx == 0:
                        self.after(0, lambda: self.lbl_status_track.configure(text="Iniciando extracción del disco completo al buffer temporal..."))
                        cmd = [exe_path, "-s", "-c", "-i", iso_file]
                        process = subprocess.Popen(cmd, cwd=temp_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, creationflags=self.creationflags)
                        
                        for line in iter(process.stdout.readline, ''):
                            line = line.strip()
                            if "%" in line:
                                try:
                                    parts = line.split("%")
                                    num_str = parts[0].split()[-1]
                                    num_str = "".join(c for c in num_str if c.isdigit())
                                    if num_str:
                                        pct = int(num_str) / 100.0
                                        self.after(0, lambda p=pct: self.progress_track.set(p))
                                except:
                                    pass
                        process.wait()
                    
                    extracted_files = list(Path(temp_dir).rglob("*.dsf"))
                    target_file = None
                    for f in extracted_files:
                        if f.name.startswith(f"{track_num:02d}"):
                            target_file = f
                            break
                    
                    if target_file:
                        self.after(0, lambda p=title: self.lbl_status_track.configure(text=f"Inyectando metadatos: {p}..."))
                        shutil.move(str(target_file), final_filepath)
                        
                        try:
                            audio = DSF(final_filepath)
                            if audio.tags is None:
                                audio.add_tags()
                            
                            audio.tags.add(TIT2(encoding=3, text=[title]))
                            audio.tags.add(TPE1(encoding=3, text=[artist]))
                            audio.tags.add(TALB(encoding=3, text=[album]))
                            
                            # INYECCIÓN DEL NÚMERO DE PISTA
                            audio.tags.add(TRCK(encoding=3, text=[str(track_num)]))
                            
                            if cover_img and os.path.exists(cover_img):
                                with open(cover_img, 'rb') as c:
                                    img_data = c.read()
                                mime = 'image/jpeg' if cover_img.lower().endswith('.jpg') or cover_img.lower().endswith('.jpeg') else 'image/png'
                                audio.tags.add(
                                    APIC(
                                        encoding=3,
                                        mime=mime,
                                        type=3, 
                                        desc='Cover',
                                        data=img_data
                                    )
                                )
                            audio.save()
                        except Exception as e:
                            print(f"Error etiquetando {final_filepath}: {e}")
                            
            self.after(0, lambda: self.progress_album.set(1.0))
            self.after(0, lambda: self.progress_track.set(1.0))
            self.after(0, lambda: self.lbl_status_album.configure(text="Álbum: Completado (100%)"))
            self.after(0, lambda: self.lbl_status_track.configure(text="Operación finalizada."))
            
            if cover_img and os.path.exists(cover_img):
                 ext = os.path.splitext(cover_img)[1]
                 shutil.copy(cover_img, os.path.join(final_dest, f"cover{ext}"))
            
            self.after(0, self._on_complete)

        except Exception as e:
            self.after(0, lambda e=e: messagebox.showerror("Error crítico", str(e)))
        finally:
            self.is_processing = False
            self.after(0, lambda: self.btn_start.configure(state="normal"))

    def _on_complete(self):
        messagebox.showinfo("Conversión Completada", "Todos los archivos han sido extraídos y etiquetados exitosamente.\n\nSe abrirá la carpeta de destino.")
        dest = self.dest_path.get()
        if os.path.exists(dest):
            os.startfile(dest)

if __name__ == "__main__":
    app = SACDConverterApp()
    app.mainloop()
