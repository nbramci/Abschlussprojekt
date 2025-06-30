import json
import pandas as pd
import plotly.express as px

# -------------------- Klasse zur EKG-Datenverarbeitung --------------------

# Klasse EKG-Data für Peakfinder, die uns ermöglicht peaks zu finden

class EKGdata:
    """
    Die Klasse EKGdata dient zur Verarbeitung, Analyse und Visualisierung von EKG-Messdaten.
    
    Funktionen:
    - Laden von EKG-Daten aus einem Dictionary
    - Filtern unrealistischer Werte
    - Korrektur von Zeitdaten bei Sprüngen
    - Berechnung der Dauer
    - Erkennung von Herzschlägen (Peaks)
    - Schätzung der Herzfrequenz
    - Visualisierung der EKG-Zeitreihe und der Herzfrequenzverläufe
    """

    # EKG-Test aus der Datenbank laden anhand der ID
    @staticmethod
    def load_by_id(id, db):
        """
        Lädt einen EKG-Test anhand der ID aus der Datenbank und gibt ein EKGdata-Objekt zurück.
        """
        for person in db:
            for ekg_dict in person.ekg_tests:
                if ekg_dict["id"] == id:
                    return EKGdata(ekg_dict)
        raise ValueError(f"EKG-Test mit ID {id} nicht gefunden.")

    # Konstruktor: EKG-Daten laden und vorbereiten
    def __init__(self, ekg_dict):
        """
        Initialisiert ein EKGdata-Objekt basierend auf einem übergebenen Dictionary.
        Lädt die CSV-Datei, filtert unrealistische Werte, und korrigiert bei Bedarf die Zeitreihe.
        """
        self.time_was_corrected = False

        self.id = ekg_dict["id"]
        self.date = ekg_dict["date"]
        ekg_id = ekg_dict["id"]
        self.data = f"data/ekg_data/{ekg_id}.txt"
        self.df = pd.read_csv(self.data, sep='\t', header=None, names=['Messwerte in mV','Zeit in ms',])
        self.df = self.df.dropna()
        self.df = self.df[self.df["Messwerte in mV"].between(100, 1500)]
        self.df = self.df[self.df["Messwerte in mV"] > 100]

        # Zeitreihe korrigieren, wenn sie zurückspringt
        zeit_diff = self.df["Zeit in ms"].diff()
        reset_index = zeit_diff[zeit_diff < 0].index

        if not reset_index.empty:
            start_idx = reset_index[0]
            offset = self.df.loc[start_idx - 1, "Zeit in ms"] + 1
            self.df.loc[start_idx:, "Zeit in ms"] += offset
            self.time_was_corrected = True

        # Zeitreihe bei 0 beginnen lassen (nur visuell)
        start_time = self.df["Zeit in ms"].iloc[0]
        self.df["Zeit in ms"] -= start_time

        self.duration_seconds = (self.df["Zeit in ms"].iloc[-1] - self.df["Zeit in ms"].iloc[0]) / 1000

        self.visible_range = None

    def get_duration_str(self):
        """
        Gibt die Dauer der Messung als String im Format Minuten und Sekunden zurück.
        """
        minutes = int(self.duration_seconds // 60)
        seconds = int(self.duration_seconds % 60)
        return f"{minutes} Minuten und {seconds} Sekunden"

    # Peaks (Herzschläge) im EKG-Signal finden
    def detect_peaks_globally(self):
        """
        Führt eine robuste Peak-Erkennung auf dem vollständigen EKG-Datensatz durch,
        mit Glättung und adaptiver Schwellwertsetzung, um verschiedene Signalqualitäten zu bewältigen.
        """
        from scipy.signal import find_peaks
        import numpy as np

        data_path = f"data/ekg_data/{self.id}.txt"
        full_df = pd.read_csv(data_path, sep='\t', header=None, names=['Messwerte in mV', 'Zeit in ms']).dropna()
        full_df = full_df[full_df["Messwerte in mV"].between(100, 1500)]

        # Zeitkorrektur falls notwendig
        zeit_diff = full_df["Zeit in ms"].diff()
        reset_index = zeit_diff[zeit_diff < 0].index
        if not reset_index.empty:
            start_idx = reset_index[0]
            offset = full_df.loc[start_idx - 1, "Zeit in ms"] + 1
            full_df.loc[start_idx:, "Zeit in ms"] += offset
        full_df["Zeit in ms"] -= full_df["Zeit in ms"].iloc[0]

        # Signal glätten (rolling mean)
        full_df["smoothed"] = full_df["Messwerte in mV"].rolling(window=7, center=True, min_periods=1).mean()
        signal = full_df["smoothed"].values

        # Adaptive Höhe als Prozentsatz des Maximalwerts
        adaptive_height = 0.5 * np.max(signal)

        # Samplingrate aus Zeitdifferenzen abschätzen (ms -> Hz)
        mean_diff = full_df["Zeit in ms"].diff().mean()
        sampling_rate_hz = 1000 / mean_diff  # ms -> Hz
        min_rr_interval_sec = 0.4  # z.B. 0.4s entspricht 150 bpm
        # min_distance_samples = int(min_rr_interval_sec * sampling_rate_hz)

        # Peaks finden mit adaptiver Höhe (ohne Mindestabstand)
        peaks, properties = find_peaks(signal, height=adaptive_height)
        self.all_peaks_df = full_df.iloc[peaks].copy()

    # Mittlere Herzfrequenz basierend auf den Peaks berechnen
    def estimate_hr(self):
        """
        Schätzt die mittlere Herzfrequenz basierend auf den global erkannten Peaks.
        """
        if not hasattr(self, "all_peaks_df"):
            raise ValueError("Peaks wurden noch nicht erkannt. Bitte zuerst detect_peaks_globally() aufrufen.")
        peak_times = self.all_peaks_df["Zeit in ms"].values / 1000  # in Sekunden
        rr_intervals = peak_times[1:] - peak_times[:-1]
        avg_rr = rr_intervals.mean()
        self.estimated_hr = 60 / avg_rr if avg_rr > 0 else 0
        return self.estimated_hr

    # EKG-Zeitreihe als Plot darstellen
    def plot_time_series(self):
        """
        Erstellt ein Plotly-Diagramm der EKG-Zeitreihe mit markierten Peaks.
        """
        visible_df = self.df.copy()
        fig = px.line(visible_df, x="Zeit in ms", y="Messwerte in mV", title="EKG-Zeitreihe")

        if hasattr(self, "all_peaks_df"):
            peak_df = self.all_peaks_df
            peak_df = peak_df[(peak_df["Zeit in ms"] >= visible_df["Zeit in ms"].min()) & 
                              (peak_df["Zeit in ms"] <= visible_df["Zeit in ms"].max())]
            fig.add_scatter(x=peak_df["Zeit in ms"], y=peak_df["Messwerte in mV"],
                            mode='markers', marker=dict(color='red', size=6), name="Peaks")
        self.fig = fig
        return fig
    
    # Herzfrequenz-Verlauf über die Zeit berechnen und visualisieren
    def plot_hr_over_time(self, min_time=None, max_time=None):
        """
        Berechnet die Herzfrequenz über die Zeit für den gesamten Datensatz und gibt einen Plotly-Plot zurück.
        """
        if not hasattr(self, "all_peaks_df"):
            raise ValueError("Bitte zuerst detect_peaks_globally() aufrufen.")

        peak_df = self.all_peaks_df
        peak_times = peak_df["Zeit in ms"].values / 1000  # in Sekunden
        if len(peak_times) < 2:
            raise ValueError("Nicht genügend Peaks zur Berechnung der Herzfrequenz.")

        rr_intervals = peak_times[1:] - peak_times[:-1]
        hr_values = 60 / rr_intervals
        time_points = (peak_times[1:] + peak_times[:-1]) / 2

        hr_df = pd.DataFrame({"Zeit (s)": time_points, "Herzfrequenz (bpm)": hr_values})
        fig = px.line(hr_df, x="Zeit (s)", y="Herzfrequenz (bpm)", title="Herzfrequenz über die Zeit")
        return fig

    def set_time_range(self, time_range):
        """
        Setzt einen Zeitbereich (in Millisekunden) zur Filterung der EKG-Daten.

        Parameter:
        - time_range (tuple): Ein Tupel aus (min_time, max_time) in Millisekunden.
        """
        min_time, max_time = time_range
        self.df = self.df[(self.df["Zeit in ms"] >= min_time) & (self.df["Zeit in ms"] <= max_time)]
        self.visible_range = time_range  # bleibt erhalten, da ggf. anderweitig verwendet