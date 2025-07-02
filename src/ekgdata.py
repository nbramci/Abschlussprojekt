# Modul zur Verarbeitung, Analyse und Visualisierung von EKG-Messdaten
import json
import pandas as pd
import plotly.express as px
from scipy.signal import find_peaks
import numpy as np

class EKGdata:
    # Klasse zur Verarbeitung, Analyse und Visualisierung von EKG-Messdaten.

    @staticmethod
    def load_by_id(id, db):
        # Lädt EKG-Test anhand der ID aus der Datenbank.
        for person in db:
            for ekg_dict in person.ekg_tests:
                if ekg_dict["id"] == id:
                    return EKGdata(ekg_dict)
        raise ValueError(f"EKG-Test mit ID {id} nicht gefunden.")

    def __init__(self, ekg_dict):
        # Initialisiert mit EKG-Daten aus Dictionary und bereitet sie vor.
        self.time_was_corrected = False

        self.id = ekg_dict["id"]
        self.date = ekg_dict["date"]
        ekg_id = ekg_dict["id"]
        self.data = f"data/ekg_data/{ekg_id}.txt"
        self.df = pd.read_csv(self.data, sep='\t', header=None, names=['Messwerte in mV', 'Zeit in ms'])[::4]
        self.df = self.df.dropna()

        if self.df.empty:
            raise ValueError(f"Keine gültigen EKG-Daten in Datei {self.data}")

        # Zeitreihe korrigieren, wenn Zeitstempel zurückspringen (Reset)
        zeit_diff = self.df["Zeit in ms"].diff()
        reset_index = zeit_diff[zeit_diff < 0].index

        if not reset_index.empty:
            # Zeitstempel korrigieren, indem Offset zum weiteren Verlauf addiert wird
            start_idx = reset_index[0]
            offset = self.df["Zeit in ms"].iloc[self.df.index.get_loc(start_idx) - 1] + 1
            self.df.loc[start_idx:, "Zeit in ms"] += offset
            self.time_was_corrected = True

        # Zeitreihe visuell bei 0 beginnen lassen (normalisieren)
        if self.df.empty or self.df["Zeit in ms"].empty:
            raise ValueError(f"Keine gültigen EKG-Daten in Datei {self.data}")
        else:
            start_time = self.df["Zeit in ms"].iloc[0]
            self.df["Zeit in ms"] -= start_time

        # Abtastrate (optional, falls bekannt)
        self.sampling_rate = None

        # Gesamtdauer in Sekunden berechnen
        self.duration_seconds = (self.df["Zeit in ms"].iloc[-1] - self.df["Zeit in ms"].iloc[0]) / 1000

        self.visible_range = None  # sichtbarer Zeitbereich für Visualisierung

        self.max_valid_time = self.df["Zeit in ms"].max()

        self.rr_anomalies = pd.DataFrame()  # DataFrame für erkannte RR-Anomalien

        self.peaks = []  # Liste der Peak-Indizes
        self.peaks_detected = False  # Flag, ob Peaks gefunden wurden


    def get_duration_str(self):
        # Gibt die Messdauer als String (Minuten und Sekunden) zurück.
        minutes = int(self.duration_seconds // 60)
        seconds = int(self.duration_seconds % 60)
        return f"{minutes} Minuten und {seconds} Sekunden"

    def detect_peaks_globally(self, height=None):
        # Erkennt Peaks (Herzschläge) im gesamten EKG-Signal.
        # Vollständige EKG-Daten laden
        data_path = f"data/ekg_data/{self.id}.txt"
        full_df = pd.read_csv(data_path, sep='\t', header=None, names=['Messwerte in mV', 'Zeit in ms'])
        full_df = full_df.dropna()

        # Zeitkorrektur wie im Konstruktor (bei Sprüngen)
        zeit_diff = full_df["Zeit in ms"].diff()
        reset_index = zeit_diff[zeit_diff < 0].index
        if not reset_index.empty:
            start_idx = reset_index[0]
            previous_index = full_df.index.get_loc(start_idx) - 1
            if previous_index >= 0:
                offset = full_df["Zeit in ms"].iloc[previous_index] + 1
            else:
                offset = 0
            full_df.loc[start_idx:, "Zeit in ms"] += offset
        full_df["Zeit in ms"] -= full_df["Zeit in ms"].iloc[0]

        # Subsampling: Jeder 4. Messwert verwenden
        full_df = full_df.iloc[::4].reset_index(drop=True)

        signal = full_df["Messwerte in mV"].values

        # Schwellenwert (height) für Peaks; Standardwert 350
        if height is None:
            height = 350
        peaks, _ = find_peaks(signal, height=height)

        # Gefundene Peaks speichern
        self.all_peaks_df = full_df.iloc[peaks].copy()
        self.peaks = peaks.tolist()
        self.peaks_detected = True

    def detect_rr_anomalies(self, threshold_ms=300):
        # Erkennt RR-Anomalien (Intervalle kürzer als threshold_ms).
        if not self.peaks_detected or not hasattr(self, "all_peaks_df") or self.all_peaks_df.empty:
            raise ValueError("Bitte zuerst detect_peaks_globally() aufrufen.")
        peak_times = self.all_peaks_df["Zeit in ms"].values
        rr_intervals = peak_times[1:] - peak_times[:-1]
        anomaly_indices = [i+1 for i, rr in enumerate(rr_intervals) if rr < threshold_ms]
        max_time = self.df["Zeit in ms"].max()
        rr_df = self.all_peaks_df.iloc[anomaly_indices]
        # Nur Anomalien innerhalb des aktuellen Zeitbereichs behalten
        self.rr_anomalies = rr_df[rr_df["Zeit in ms"] <= max_time].copy()

    def estimate_hr(self):
        # Schätzt die mittlere Herzfrequenz anhand der Peaks.
        if not hasattr(self, "all_peaks_df"):
            raise ValueError("Peaks wurden noch nicht erkannt. Bitte zuerst detect_peaks_globally() aufrufen.")
        peak_times = self.all_peaks_df["Zeit in ms"].values / 1000  # Sekundenskala
        rr_intervals = peak_times[1:] - peak_times[:-1]
        avg_rr = rr_intervals.mean()
        self.estimated_hr = 60 / avg_rr if avg_rr > 0 else 0
        return self.estimated_hr

    def plot_time_series(self):
        # Erstellt ein Plot der EKG-Zeitreihe mit Peaks und RR-Anomalien.
        # Sichtbarer Bereich, standardmäßig 10 Sekunden (0 bis 10.000 ms)
        if self.visible_range is None:
            min_time = 0
            max_time = 10000
        else:
            min_time, max_time = self.visible_range

        visible_df = self.df[(self.df["Zeit in ms"] >= min_time) & (self.df["Zeit in ms"] <= max_time)].copy()

        fig = px.line(visible_df, x="Zeit in ms", y="Messwerte in mV", title="EKG-Zeitreihe")

        if hasattr(self, "all_peaks_df"):
            # Peaks im sichtbaren Bereich plotten
            peak_df = self.all_peaks_df
            peak_df = peak_df[(peak_df["Zeit in ms"] >= min_time) & 
                              (peak_df["Zeit in ms"] <= max_time)]
            fig.add_scatter(x=peak_df["Zeit in ms"], y=peak_df["Messwerte in mV"],
                            mode='markers', marker=dict(color='blue', size=6), name="Peaks")
        # RR-Anomalien als rote Markierungen mit Text annotieren
        if hasattr(self, "rr_anomalies"):
            self.visible_rr_anomalies = []
            for _, row in self.rr_anomalies.iterrows():
                anomaly_time = row["Zeit in ms"]
                if min_time <= anomaly_time <= max_time:
                    self.visible_rr_anomalies.append(row)
                    fig.add_vrect(
                        x0=anomaly_time - 50, x1=anomaly_time + 50,
                        fillcolor="red", opacity=0.4, line_width=1, line_color="darkred",
                        annotation_text="Anomalie", annotation_position="top left",
                        annotation_font_size=10, annotation_font_color="red"
                    )
            # Dummy-Trace für Legende "RR-Anomalie"
            fig.add_scatter(x=[None], y=[None], mode='markers',
                            marker=dict(color='red', size=6),
                            name='RR-Anomalie')
        self.fig = fig
        return fig
    
    def plot_hr_over_time(self, min_time=None, max_time=None):
        # Visualisiert die Herzfrequenz über die Zeit (RR-Intervalle).
        if not hasattr(self, "all_peaks_df") or self.all_peaks_df.empty:
            import plotly.graph_objects as go
            return go.Figure().update_layout(title="Keine gültigen Peaks erkannt – bitte Schwellwert anpassen.")

        peak_df = self.all_peaks_df
        peak_times = peak_df["Zeit in ms"].values / 1000  # Sekundenskala
        if len(peak_times) < 2:
            raise ValueError("Nicht genügend Peaks zur Berechnung der Herzfrequenz.")

        # RR-Intervalle und Zeitpunkte berechnen
        rr_intervals = peak_times[1:] - peak_times[:-1]
        hr_values = 60 / rr_intervals
        time_points = (peak_times[1:] + peak_times[:-1]) / 2

        # DataFrame erstellen
        hr_df = pd.DataFrame({
            "Zeit (s)": time_points,
            "Herzfrequenz (bpm)": hr_values
        })

        # Adaptive Fenstergröße: 5% der Anzahl der HR-Werte, mindestens 3
        window_size = max(3, int(len(hr_df) * 0.05))
        hr_df["Herzfrequenz (bpm)"] = hr_df["Herzfrequenz (bpm)"].rolling(window=window_size, center=True, min_periods=1).mean()

        # Falls ein Zeitbereich angegeben ist, beschneiden
        if min_time is not None and max_time is not None:
            min_s, max_s = min_time / 1000, max_time / 1000
            hr_df = hr_df[(hr_df["Zeit (s)"] >= min_s) & (hr_df["Zeit (s)"] <= max_s)]

        # Dynamische Y-Achse mit Puffer
        y_min = hr_df["Herzfrequenz (bpm)"].min() - 5
        y_max = hr_df["Herzfrequenz (bpm)"].max() + 5

        # Plot erzeugen
        fig = px.line(hr_df, x="Zeit (s)", y="Herzfrequenz (bpm)", title="Herzfrequenz über die Zeit")
        fig.update_layout(
            yaxis=dict(range=[y_min, y_max]),
            template="plotly_white"
        )
        return fig

    def set_time_range(self, time_range):
        # Setzt den Zeitbereich (in ms) für die EKG-Daten.
        min_time, max_time = time_range
        self.df = self.df[(self.df["Zeit in ms"] >= min_time) & (self.df["Zeit in ms"] <= max_time)]
        self.visible_range = time_range  # bleibt erhalten, da ggf. anderweitig verwendet

    def get_rr_anomaly_table(self):
        # Gibt eine Tabelle der RR-Anomalien (Zeitpunkte in ms) zurück.
        if not hasattr(self, "rr_anomalies") or self.rr_anomalies.empty:
            return pd.DataFrame(columns=["Zeitpunkt (ms)"])
        max_time = self.df["Zeit in ms"].max()
        valid_anomalies = self.rr_anomalies[self.rr_anomalies["Zeit in ms"] <= max_time]
        return pd.DataFrame({"Zeitpunkt (ms)": valid_anomalies["Zeit in ms"].astype(int).values})

    def get_visible_rr_anomalies(self):
        # Gibt RR-Anomalien im sichtbaren Zeitbereich zurück.
        if not hasattr(self, "rr_anomalies") or self.rr_anomalies.empty:
            return []
        max_time = self.df["Zeit in ms"].max()
        min_time, max_visible = (0, max_time) if self.visible_range is None else self.visible_range
        visible_anomalies = self.rr_anomalies[
            (self.rr_anomalies["Zeit in ms"] >= min_time) &
            (self.rr_anomalies["Zeit in ms"] <= max_visible) &
            (self.rr_anomalies["Zeit in ms"] <= max_time)
        ]
        return visible_anomalies["Zeit in ms"].astype(int).tolist()