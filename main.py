"""
Hauptmodul der Streamlit-Anwendung zur Anzeige und Analyse von EKG-Daten.

Diese App ermöglicht die Auswahl von Versuchspersonen, zeigt deren Basisinformationen
sowie EKG-Daten und berechnet wichtige Kennwerte wie Herzfrequenz.
"""

import bcrypt
import streamlit as st
import pandas as pd
from PIL import Image
from plotly import express as px
import numpy as np
import datetime

from src.read_person_data import load_user_objects
from src.ekgdata import EKGdata

from tinydb import TinyDB, Query

# Session-Variablen initialisieren, falls noch nicht vorhanden
if "is_logged_in" not in st.session_state:
    st.session_state["is_logged_in"] = False
    st.session_state["current_user_name"] = ""
    st.session_state["current_user"] = None
    st.session_state["login_failed"] = False
    st.session_state["role"] = ""

if "is_logged_in" in st.session_state and st.session_state["is_logged_in"]:
    st.set_page_config(page_title="EKG-Analyse", layout="wide")
else:
    st.set_page_config(page_title="EKG-Analyse", layout="centered")

if not st.session_state["is_logged_in"]:
    st.title("Login")

def reset_session():
    st.session_state["is_logged_in"] = False
    st.session_state["current_user_name"] = ""
    st.session_state["current_user"] = None
    st.session_state["login_failed"] = False
    st.session_state["role"] = ""

if not st.session_state["is_logged_in"]:
    with st.form("login_form"):
        st.subheader("Bitte einloggen")
        username = st.text_input("Benutzername", "")
        password = st.text_input("Passwort", type="password")
        submitted = st.form_submit_button("Login")

        if submitted:
            db = TinyDB("data/tinydb_person_db.json")
            users = db.table("_default").all()

            matched_user = None
            for user in users:
                stored_pw = user.get("password", "")
                if (user.get("username", "").strip().lower() == username.strip().lower() and
                    (bcrypt.checkpw(password.encode(), stored_pw.encode()) if stored_pw.startswith("$2b$") else stored_pw == password)):
                    matched_user = user
                    break

            if matched_user:
                st.session_state["login_failed"] = False
                st.session_state["is_logged_in"] = True
                st.session_state["current_user_name"] = matched_user["username"]
                all_users = load_user_objects()
                current_user = next((p for p in all_users if p.username == matched_user["username"]), None)
                st.session_state["current_user"] = current_user
                st.session_state["role"] = matched_user.get("role", "user")

                # Bei Admins direkt eigenes Profil anzeigen
                if matched_user.get("role") == "admin":
                    st.session_state["admin_mode"] = "Benutzer suchen"
                    st.session_state["admin_selected_user"] = f"{current_user.firstname} {current_user.lastname}"

                st.success("Login erfolgreich!")
                st.rerun()
            else:
                st.session_state["login_failed"] = True

if st.session_state.get("login_failed"):
    st.error("Ungültiger Benutzername oder Passwort.")

if st.session_state["is_logged_in"]:
    person = None
    st.header("EKG-APP")
    if st.session_state["role"] == "admin":
        if st.button("Logout", key="admin_logout"):
            reset_session()
            st.rerun()

        st.write("### Admin-Modus")
        admin_option = st.radio(
            "Aktion auswählen",
            ["Benutzer suchen", "Neue Person anlegen"],
            index=0 if st.session_state.get("admin_mode") == "Benutzer suchen" else 1
        )

        if admin_option == "Benutzer suchen":
            all_users = load_user_objects()
            suchname = st.text_input("Benutzer suchen (Vor- oder Nachname)")
            matching_users = [
                p for p in all_users if suchname.lower() in p.firstname.lower() or suchname.lower() in p.lastname.lower()
            ]
            if matching_users:
                select_options = [f"{p.firstname} {p.lastname}" for p in matching_users]
                selected = st.selectbox("Nutzer auswählen", select_options, key="admin_selected_user")
                person = next(p for p in matching_users if f"{p.firstname} {p.lastname}" == selected)

                tabs = st.tabs(["👤 Übersicht & Analyse", "⚙️ Bearbeiten / Löschen"])

                with tabs[0]:
                    col1, col2 = st.columns([1, 2])

                    ekg = None
                    hr_fig = None

                    with col1:
                        st.markdown("### 🧍 Versuchsperson")
                        st.image(person.picture_path, caption=person.get_full_name(), width=250)
                        st.markdown(f"**Name:** {person.get_full_name()}")
                        st.markdown(f"**ID:** `{person.id}`")
                        st.markdown(f"**Geburtsjahr:** {person.date_of_birth}")
                        st.markdown(f"**Maximale Herzfrequenz (geschätzt):** {person.calc_max_heart_rate()} bpm")

                        # PDF Export Option für Admins (direkt nach Personendaten)
                        ekg_tests = person.ekg_tests
                        if ekg_tests:
                            try:
                                import fpdf
                                fpdf_available = True
                            except ImportError:
                                fpdf_available = False
                            if not fpdf_available:
                                st.info("Das Paket 'fpdf' ist nicht installiert. Installiere es mit `pip install fpdf`, um die Analyse als PDF zu exportieren.")
                            else:
                                pass
                        ekg_options = {f"Test {i+1} am {t['date']}": t["id"] for i, t in enumerate(ekg_tests)}
                        # Fallback: selectbox muss existieren, sonst Standardwert nehmen
                        selected_label = st.session_state.get("ekg_select_admin")
                        if ekg_options:
                            if not selected_label or selected_label not in ekg_options:
                                selected_label = list(ekg_options.keys())[0]
                        else:
                            selected_label = None
                        if selected_label:
                            selected_id = ekg_options[selected_label]
                            selected_test = next(test for test in ekg_tests if test["id"] == selected_id)
                            user_data = [person]
                            ekg = EKGdata.load_by_id(selected_id, user_data)
                            # Wichtig: detect_peaks_globally() muss vor detect_rr_anomalies() aufgerufen werden!
                            ekg.detect_peaks_globally()
                            if ekg.peaks:
                                try:
                                    ekg.detect_rr_anomalies()
                                except ValueError:
                                    st.info("⚠️ Für diese Einstellungen konnten keine verwertbaren EKG-Daten erkannt werden. Bitte den Wert für die Peak-Erkennung anpassen.")
                            else:
                                st.info("ℹ️ Keine Peaks erkannt – Anomalie-Erkennung wird übersprungen.")
                            min_ms = int(ekg.df["Zeit in ms"].min())
                            max_ms = int(ekg.df["Zeit in ms"].max())
                            slider_key = "slider_admin"
                            # CSV-Export des gewählten EKG-Zeitbereichs (direkt nach Auswahl des Zeitbereichs)
                            if ekg.df is not None and not ekg.df.empty:
                                # set_time_range falls Slider gesetzt, sonst unverändert
                                if slider_key in st.session_state:
                                    time_range = st.session_state[slider_key]
                                    ekg.set_time_range(time_range)
                                csv = ekg.df.to_csv(index=False).encode("utf-8")
                                st.download_button(
                                    label="📥 CSV des gewählten Zeitbereichs herunterladen",
                                    data=csv,
                                    file_name=f"{person.username}_{selected_test['date'].replace('.', '-')}_auswahl.csv",
                                    mime="text/csv",
                                    key="csv_admin_download_left"
                                )
                            if st.button("📝 Analyse-Zusammenfassung als PDF erstellen", key="pdf_admin_button"):
                                from fpdf import FPDF
                                import os

                                # Plotly-Figur des EKGs als PNG erzeugen
                                import plotly.io as pio
                                fig = ekg.plot_time_series()
                                png_bytes = fig.to_image(format="png")
                                export_dir = "exports"
                                os.makedirs(export_dir, exist_ok=True)
                                png_path = os.path.join(export_dir, f"{person.username}_ekg_snapshot.png")
                                with open(png_path, "wb") as f:
                                    f.write(png_bytes)

                                class PDF(FPDF):
                                    def header(self):
                                        self.set_font("Arial", "B", 12)
                                        self.cell(0, 10, "EKG-Analyse-Zusammenfassung", ln=True, align="C")
                                        self.ln(10)

                                pdf = PDF()
                                pdf.add_page()

                                # Profilbild links oben
                                try:
                                    pdf.image(person.picture_path, x=10, y=15, w=30)
                                except:
                                    pass

                                # Zeilenumbruch nach Bild, damit kein Text auf dem Bild steht
                                pdf.ln(35)

                                # Alle Personendaten unter dem Bild, kompakt ohne große Abstände
                                pdf.set_font("Arial", "B", 14)
                                pdf.cell(0, 10, f"Name: {person.get_full_name()}", ln=True)
                                pdf.set_font("Arial", "", 12)
                                pdf.cell(0, 10, f"ID: {person.id}", ln=True)
                                pdf.cell(0, 10, f"Geburtsjahr: {person.date_of_birth}", ln=True)
                                pdf.cell(0, 8, f"Testdatum: {selected_test['date']}", ln=1)
                                pdf.cell(0, 8, f"Maximale Herzfrequenz (geschätzt): {person.calc_max_heart_rate()} bpm", ln=1)
                                estimated_hr_val = round(ekg.estimate_hr()) if hasattr(ekg, "estimate_hr") else "-"
                                pdf.cell(0, 8, f"Geschätzte Herzfrequenz: {estimated_hr_val} bpm", ln=1)
                                pdf.cell(0, 8, f"Gesamtdauer der Messung: {ekg.get_duration_str()}", ln=1)

                                try:
                                    start_ms = ekg.df["Zeit in ms"].min()
                                    end_ms = ekg.df["Zeit in ms"].max()
                                    range_duration_sec = (end_ms - start_ms) / 1000
                                    r_min = int(range_duration_sec // 60)
                                    r_sec = int(range_duration_sec % 60)
                                    range_str = f"{r_min} Minuten und {r_sec} Sekunden"
                                    pdf.cell(0, 8, f"Dauer des gewählten Zeitbereichs: {range_str}", ln=1)
                                except:
                                    pdf.cell(0, 8, f"Dauer des gewählten Zeitbereichs: nicht verfügbar", ln=1)

                                pdf.cell(0, 8, "EKG-Zeitreihe auf der nächsten Seite", ln=1)

                                num_peaks = len(ekg.peaks) if hasattr(ekg, "peaks") else "-"
                                pdf.cell(0, 8, f"Anzahl erkannter Peaks (Herzschläge): {num_peaks}", ln=1)

                                pdf.ln(5)

                                visible_anomalies = ekg.get_visible_rr_anomalies()
                                pdf.set_font("Arial", "B", 12)
                                pdf.cell(0, 8, f"Anomalien: {len(visible_anomalies)} erkannt (im ausgewählten Bereich)", ln=1)
                                pdf.set_font("Arial", "", 10)

                                if visible_anomalies:
                                    col_width = 60
                                    items_per_row = 3
                                    for i, a in enumerate(visible_anomalies):
                                        art = "Ausreißer hoch" if a > 2000 else "Ausreißer tief" if a < 400 else "Ausreißer"
                                        text = f"{i+1}. {a} ms ({art})"
                                        pdf.cell(col_width, 8, text, ln=False)
                                        if (i + 1) % items_per_row == 0:
                                            pdf.ln(8)
                                    if len(visible_anomalies) % items_per_row != 0:
                                        pdf.ln(8)
                                else:
                                    pdf.cell(0, 8, "Keine Anomalien im gewählten Bereich", ln=1)

                                pdf.add_page()

                                page_width = pdf.w - 2 * pdf.l_margin
                                try:
                                    pdf.image(png_path, x=pdf.l_margin, y=pdf.get_y(), w=page_width)
                                    pdf.ln(90)
                                except:
                                    pass

                                pdf_path = os.path.join(export_dir, f"{person.username}_analyse.pdf")
                                pdf.output(pdf_path)

                                with open(pdf_path, "rb") as f:
                                    st.download_button("📄 PDF herunterladen", data=f, file_name=f"{person.username}_analyse.pdf", mime="application/pdf")
                        else:
                            st.info("❕ Keine EKG-Daten für diese Person vorhanden.")

                    with col2:
                        st.markdown("### ⚙️ Analyseoptionen")
                        ekg_tests = person.ekg_tests
                        if ekg_tests:
                            ekg_options = {f"Test {i+1} am {t['date']}": t["id"] for i, t in enumerate(ekg_tests)}
                            if ekg_options:
                                selected_label = st.selectbox("Wählen Sie einen EKG-Test", list(ekg_options.keys()), key="ekg_select_admin")
                            else:
                                selected_label = None
                            if selected_label:
                                selected_id = ekg_options[selected_label]
                                selected_test = next(test for test in ekg_tests if test["id"] == selected_id)
                                user_data = [person]
                                ekg = EKGdata.load_by_id(selected_id, user_data)
                                # Peak- und Anomalie-Erkennung wird nun im Visualisierungs-Abschnitt durchgeführt

                                min_ms = int(ekg.df["Zeit in ms"].min())
                                max_ms = int(ekg.df["Zeit in ms"].max())
                                default_end = min(min_ms + 10000, max_ms)

                                # CSV-Export des gewählten EKG-Zeitbereichs (direkt nach Auswahl des Zeitbereichs)
                                # (Export-Button nur in linker Spalte unter Personendaten)



                                st.write("#### Analyse gesamter Messdaten")
                                st.write("Länge der Zeitreihe:", ekg.get_duration_str())
                                if ekg.time_was_corrected:
                                    st.warning("Hinweis: In der ausgewählten EKG-Datei wurden fehlerhafte Zeitstempel erkannt. Diese wurden automatisch korrigiert. Die Ergebnisse können dennoch Ungenauigkeiten enthalten.")
                                # Peak-Schwelle wird im Visualisierungs-Abschnitt angepasst
                            else:
                                st.info("❕ Keine EKG-Daten für diese Person vorhanden.")
                        else:
                            st.info("Keine EKG-Daten für diese Person verfügbar.")

                        if ekg_tests and selected_label:
                            st.markdown("### 📉 Visualisierung")
                            st.write("#### Zeitbereich für Analyse auswählen")
                            time_range = st.slider("Analyse-Zeitraum (ms)",
                                min_value=min_ms,
                                max_value=max_ms,
                                value=(min_ms, default_end),
                                step=100,
                                key="slider_admin")

                            ekg.set_time_range(time_range)
                            st.write("#### Peak-Erkennung anpassen")
                            with st.container():
                                col1_peak, col2_peak = st.columns([1, 4])
                                with col1_peak:
                                    height_input = st.number_input(
                                        "Peak-Schwelle",
                                        min_value=0.0,
                                        max_value=2000.0,
                                        value=350.0,
                                        step=1.0,
                                        format="%.1f",
                                        key=f"height_input_{st.session_state['role']}_{selected_id}",
                                        help="Schwellwert für Ausschläge in der Peak-Erkennung (Standard: 350). Dieser Wert kann an 'raw' oder skalierte EKG-Dateien angepasst werden."
                                    )
                            # Wichtig: detect_peaks_globally() muss vor detect_rr_anomalies() aufgerufen werden!
                            ekg.detect_peaks_globally(height=height_input)
                            if not ekg.peaks:
                                st.warning("⚠️ Es wurden keine Peaks erkannt. Bitte einen niedrigeren Wert für die Höhe eingeben.")
                            if ekg.peaks:
                                try:
                                    ekg.detect_rr_anomalies()
                                except ValueError:
                                    st.info("⚠️ Für diese Einstellungen konnten keine verwertbaren EKG-Daten erkannt werden. Bitte den Wert für die Peak-Erkennung anpassen.")
                            else:
                                st.info("Keine Peaks erkannt – Anomalie-Erkennung wird übersprungen.")
                            # Herzfrequenz erst nach Peak-Erkennung schätzen!
                            estimated_hr = ekg.estimate_hr()
                            ekg.plot_time_series()
                            hr_fig = ekg.plot_hr_over_time()
                        # Graphen werden jetzt unterhalb der Columns angezeigt, daher hier nur vorbereiten
                    # --- Graphen unterhalb der Columns in voller Breite darstellen (analog User) ---
                    if ekg is not None:
                        st.plotly_chart(ekg.fig, use_container_width=True, height=400, key="plot_admin_fig")
                        if hr_fig is not None:
                            st.plotly_chart(hr_fig, use_container_width=True, height=400, key="plot_admin_hr")



                with tabs[1]:
                    st.write("#### Bearbeiten oder Löschen")
                    col_left, col_right = st.columns([1, 2])

                    with col_left:
                        st.image(person.picture_path, caption=person.get_full_name(), width=200)

                    with col_right:
                        with st.expander("✏️ Person bearbeiten"):
                            st.image(person.picture_path, caption="Aktuelles Profilbild", width=150)
                            edit_firstname = st.text_input("Vorname", value=person.firstname)
                            edit_lastname = st.text_input("Nachname", value=person.lastname)
                            edit_birth_year = st.number_input("Geburtsjahr", min_value=1920, max_value=datetime.date.today().year, value=int(person.date_of_birth))
                            edit_username = st.text_input("Benutzername", value=person.username)
                            edit_password = st.text_input("Passwort", value=person.password)
                            edit_role = st.selectbox("Rolle", ["user", "admin"], index=["user", "admin"].index(person.role))
                            edit_picture = st.file_uploader("Neues Profilbild hochladen", type=["jpg", "jpeg", "png"])

                            if st.button("Änderungen speichern"):
                                if not all([edit_firstname.strip(), edit_lastname.strip(), edit_username.strip(), edit_password.strip()]):
                                    st.error("❌ Bitte füllen Sie alle Felder aus.")
                                else:
                                    db = TinyDB("data/tinydb_person_db.json")
                                    query = Query()
                                    all_users = db.all()
                                    if any(u.get("username", "").lower() == edit_username.strip().lower() and u.get("username") != person.username for u in all_users):
                                        st.error("❌ Dieser Benutzername ist bereits vergeben.")
                                    else:
                                        picture_path = person.picture_path
                                        if edit_picture:
                                            import os
                                            os.makedirs("data/profile_pictures", exist_ok=True)
                                            picture_path = f"data/profile_pictures/{person.id}.jpg"
                                            with open(picture_path, "wb") as f:
                                                f.write(edit_picture.read())
                                        db.update({
                                            "firstname": edit_firstname,
                                            "lastname": edit_lastname,
                                            "date_of_birth": str(edit_birth_year),
                                            "username": edit_username,
                                            "password": bcrypt.hashpw(edit_password.encode(), bcrypt.gensalt()).decode(),
                                            "role": edit_role,
                                            "picture_path": picture_path
                                        }, query.username == person.username)
                                        st.success("✅ Personendaten aktualisiert.")
                                        st.rerun()

                        with st.expander("🗑️ Person löschen"):
                            if st.button("Diese Person löschen"):
                                db = TinyDB("data/tinydb_person_db.json")
                                query = Query()
                                db.remove(query.username == person.username)
                                st.success("✅ Person wurde gelöscht.")
                                st.rerun()

                        with st.expander("📤 EKG-Daten hochladen"):
                            ekg_file = st.file_uploader("EKG-Datei im .txt-Format", type=["txt"], key="ekg_upload")
                            ekg_date = st.date_input("Datum des EKG-Tests", value=datetime.date.today())

                            if st.button("EKG hochladen"):
                                if ekg_file:
                                    import uuid, os
                                    os.makedirs("data/ekg_data", exist_ok=True)
                                    ekg_id = str(uuid.uuid4())
                                    filename = f"{ekg_id}.txt"
                                    file_path = os.path.join("data/ekg_data", filename)

                                    with open(file_path, "wb") as f:
                                        f.write(ekg_file.read())

                                    db = TinyDB("data/tinydb_person_db.json")
                                    query = Query()
                                    db_user = db.get(query.username == person.username)
                                    existing_tests = db_user.get("ekg_tests", [])
                                    existing_tests.append({
                                        "id": ekg_id,
                                        "date": ekg_date.strftime("%d.%m.%Y")
                                    })
                                    db.update({"ekg_tests": existing_tests}, query.username == person.username)

                                    st.success("✅ EKG-Datei erfolgreich hochgeladen.")
                                else:
                                    st.error("❌ Bitte wählen Sie eine gültige Datei aus.")

                        with st.expander("🗑️ EKG-Test löschen"):
                            if person.ekg_tests:
                                ekg_options_delete = {f"Test {i+1} am {t['date']}": t["id"] for i, t in enumerate(person.ekg_tests)}
                                selected_label_delete = st.selectbox("Wähle EKG-Test zum Löschen", list(ekg_options_delete.keys()), key="delete_ekg_select")
                                selected_id_delete = ekg_options_delete[selected_label_delete]

                                if st.button("EKG-Test löschen"):
                                    import os
                                    ekg_file_path = os.path.join("data/ekg_data", f"{selected_id_delete}.txt")
                                    if os.path.exists(ekg_file_path):
                                        os.remove(ekg_file_path)

                                    db = TinyDB("data/tinydb_person_db.json")
                                    query = Query()
                                    user_entry = db.get(query.username == person.username)
                                    updated_ekgs = [t for t in user_entry.get("ekg_tests", []) if t["id"] != selected_id_delete]
                                    db.update({"ekg_tests": updated_ekgs}, query.username == person.username)

                                    st.success("✅ EKG-Test erfolgreich gelöscht.")
                                    st.rerun()
                            else:
                                st.info("Keine EKG-Daten vorhanden.")
            else:
                st.info("Kein passender Nutzer gefunden.")
                person = None

        elif admin_option == "Neue Person anlegen":
            with st.form("new_user_form"):
                col1, col2 = st.columns(2)
                with col1:
                    firstname = st.text_input("Vorname")
                    lastname = st.text_input("Nachname")
                    username = st.text_input("Benutzername")
                    password = st.text_input("Passwort")
                with col2:
                    import datetime
                    birth_year = st.number_input(
                        "Geburtsjahr",
                        min_value=1920,
                        max_value=datetime.date.today().year,
                        step=1
                    )
                    role = st.selectbox("Rolle", ["user", "admin"])
                    picture = st.file_uploader("Profilbild hochladen", type=["jpg", "png", "jpeg"])
                submitted = st.form_submit_button("Anlegen")

                if submitted:
                    from tinydb import TinyDB
                    import uuid
                    import os
                    db = TinyDB("data/tinydb_person_db.json")

                    if not all([firstname.strip(), lastname.strip(), username.strip(), password.strip()]) or birth_year is None:
                        st.error("❌ Bitte füllen Sie alle Felder aus.")
                    else:
                        existing_usernames = [user.get("username", "").lower() for user in db.all()]
                        if username.strip().lower() in existing_usernames:
                            st.error("❌ Dieser Benutzername ist bereits vergeben. Bitte wähle einen anderen.")
                        else:
                            existing_ids = {user["id"] for user in db.all() if "id" in user}
                            while True:
                                user_id = uuid.uuid4().hex[:8]
                                if user_id not in existing_ids:
                                    break
                            picture_path = f"data/profile_pictures/{user_id}.jpg"

                            if picture:
                                os.makedirs("data/profile_pictures", exist_ok=True)
                                with open(picture_path, "wb") as f:
                                    f.write(picture.read())
                            else:
                                picture_path = "data/profile_pictures/none.jpg"

                            db.insert({
                                "id": user_id,
                                "firstname": firstname,
                                "lastname": lastname,
                                "username": username,
                                "password": bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode(),
                                "date_of_birth": str(birth_year),
                                "role": role,
                                "picture_path": picture_path,
                                "ekg_tests": []
                            })
                            st.success("✅ Neue Person erfolgreich hinzugefügt.")
    elif st.session_state["role"] == "user":
        person = st.session_state["current_user"]
        if st.button("Logout", key="user_logout"):
            reset_session()
            st.rerun()

        if person:
            col1, col2 = st.columns([1, 2])

            # --- Linke Spalte: Personendaten, PDF-Export etc. ---
            with col1:
                st.markdown("### 🧍 Versuchsperson")
                st.image(person.picture_path, caption=person.get_full_name())
                st.markdown(f"**Name:** {person.get_full_name()}")
                st.markdown(f"**ID:** `{person.id}`")
                st.markdown(f"**Geburtsjahr:** {person.date_of_birth}")
                st.markdown(f"**Maximale Herzfrequenz (geschätzt):** {person.calc_max_heart_rate()} bpm")

                # PDF Export Option für User (direkt nach Personendaten)
                ekg_tests = person.ekg_tests
                ekg_options = {}
                if ekg_tests and len(ekg_tests) > 0:
                    ekg_options = {f"Test {i+1} am {t['date']}": t["id"] for i, t in enumerate(ekg_tests)}

                selected_label = st.session_state.get("ekg_select_user")

                if ekg_options:
                    if not selected_label or selected_label not in ekg_options:
                        selected_label = list(ekg_options.keys())[0]
                else:
                    selected_label = None

                if selected_label:
                    selected_id = ekg_options[selected_label]
                    selected_test = next(test for test in ekg_tests if test["id"] == selected_id)
                    user_data = [person]
                    ekg = EKGdata.load_by_id(selected_id, user_data)
                    ekg.detect_peaks_globally()
                    ekg.detect_rr_anomalies()
                    min_ms = int(ekg.df["Zeit in ms"].min())
                    max_ms = int(ekg.df["Zeit in ms"].max())
                    slider_key = "slider_user"
                    # CSV-Export des gewählten EKG-Zeitbereichs (direkt nach Auswahl des Zeitbereichs)
                    if ekg.df is not None and not ekg.df.empty:
                        # set_time_range falls Slider gesetzt, sonst unverändert
                        if slider_key in st.session_state:
                            time_range = st.session_state[slider_key]
                            ekg.set_time_range(time_range)
                        csv = ekg.df.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            label="📥 CSV des gewählten Zeitbereichs herunterladen",
                            data=csv,
                            file_name=f"{person.username}_{selected_test['date'].replace('.', '-')}_auswahl.csv",
                            mime="text/csv",
                            key="csv_user_download"
                        )
                    if st.button("📝 Analyse-Zusammenfassung als PDF erstellen", key="pdf_user_button"):
                        from fpdf import FPDF
                        import os

                        # Plotly-Figur des EKGs als PNG erzeugen
                        import plotly.io as pio
                        fig = ekg.plot_time_series()
                        png_bytes = fig.to_image(format="png")
                        export_dir = "exports"
                        os.makedirs(export_dir, exist_ok=True)
                        png_path = os.path.join(export_dir, f"{person.username}_ekg_snapshot.png")
                        with open(png_path, "wb") as f:
                            f.write(png_bytes)

                        class PDF(FPDF):
                            def header(self):
                                self.set_font("Arial", "B", 12)
                                self.cell(0, 10, "EKG-Analyse-Zusammenfassung", ln=True, align="C")
                                self.ln(10)

                        pdf = PDF()
                        pdf.add_page()

                        # Profilbild links oben
                        try:
                            pdf.image(person.picture_path, x=10, y=15, w=30)
                        except:
                            pass

                        # Zeilenumbruch nach Bild, damit kein Text auf dem Bild steht
                        pdf.ln(35)

                        # Alle Personendaten unter dem Bild
                        pdf.set_font("Arial", "B", 14)
                        pdf.cell(0, 10, f"Name: {person.get_full_name()}", ln=True)
                        pdf.set_font("Arial", "", 12)
                        pdf.cell(0, 10, f"ID: {person.id}", ln=True)
                        pdf.cell(0, 10, f"Geburtsjahr: {person.date_of_birth}", ln=True)

                        # Testdatum und Herzfrequenz
                        pdf.set_font("Arial", "", 12)
                        pdf.cell(0, 8, f"Testdatum: {selected_test['date']}", ln=1)
                        pdf.cell(0, 8, f"Maximale Herzfrequenz (geschätzt): {person.calc_max_heart_rate()} bpm", ln=1)
                        estimated_hr_val = round(ekg.estimate_hr()) if hasattr(ekg, "estimate_hr") else "-"
                        pdf.cell(0, 8, f"Geschätzte Herzfrequenz: {estimated_hr_val} bpm", ln=1)
                        pdf.cell(0, 8, f"Gesamtdauer der Messung: {ekg.get_duration_str()}", ln=1)

                        try:
                            start_ms = ekg.df["Zeit in ms"].min()
                            end_ms = ekg.df["Zeit in ms"].max()
                            range_duration_sec = (end_ms - start_ms) / 1000
                            r_min = int(range_duration_sec // 60)
                            r_sec = int(range_duration_sec % 60)
                            range_str = f"{r_min} Minuten und {r_sec} Sekunden"
                            pdf.cell(0, 8, f"Dauer des gewählten Zeitbereichs: {range_str}", ln=1)
                        except:
                            pdf.cell(0, 8, f"Dauer des gewählten Zeitbereichs: nicht verfügbar", ln=1)

                        pdf.cell(0, 8, "EKG-Zeitreihe auf der nächsten Seite", ln=1)

                        # Anzahl erkannter Peaks
                        num_peaks = len(ekg.peaks) if hasattr(ekg, "peaks") else "-"
                        pdf.cell(0, 8, f"Anzahl erkannter Peaks (Herzschläge): {num_peaks}", ln=1)

                        pdf.ln(5)

                        # Anomalien (sichtbar im gewählten Bereich)
                        visible_anomalies = ekg.get_visible_rr_anomalies()
                        pdf.set_font("Arial", "B", 12)
                        pdf.cell(0, 8, f"Anomalien: {len(visible_anomalies)} erkannt (im ausgewählten Bereich)", ln=1)
                        pdf.set_font("Arial", "", 10)

                        if visible_anomalies:
                            col_width = 60
                            items_per_row = 3
                            for i, a in enumerate(visible_anomalies):
                                art = "Ausreißer hoch" if a > 2000 else "Ausreißer tief" if a < 400 else "Ausreißer"
                                text = f"{i+1}. {a} ms ({art})"
                                pdf.cell(col_width, 8, text, ln=False)
                                if (i + 1) % items_per_row == 0:
                                    pdf.ln(8)
                            if len(visible_anomalies) % items_per_row != 0:
                                pdf.ln(8)
                        else:
                            pdf.cell(0, 8, "Keine Anomalien im gewählten Bereich", ln=1)

                        # Neue Seite für EKG-Bild
                        pdf.add_page()

                        page_width = pdf.w - 2 * pdf.l_margin
                        try:
                            pdf.image(png_path, x=pdf.l_margin, y=pdf.get_y(), w=page_width)
                            pdf.ln(90)
                        except:
                            pass

                        pdf_path = os.path.join(export_dir, f"{person.username}_analyse.pdf")
                        pdf.output(pdf_path)

                        with open(pdf_path, "rb") as f:
                            st.download_button("📄 PDF herunterladen", data=f, file_name=f"{person.username}_analyse.pdf", mime="application/pdf")
                else:
                    st.info("Keine EKG-Daten für diese Person vorhanden.")

            # --- Rechte Spalte: Analyseoptionen (Visualisierungsteil bleibt hier!) ---
            with col2:
                st.markdown("### ⚙️ Analyseoptionen")
                ekg_tests = person.ekg_tests
                ekg = None
                hr_fig = None
                if ekg_tests:
                    ekg_options = {f"Test {i+1} am {t['date']}": t["id"] for i, t in enumerate(ekg_tests)}
                    if ekg_options:
                        selected_label = st.selectbox("Wählen Sie einen EKG-Test", list(ekg_options.keys()), key="ekg_select_user")
                    else:
                        selected_label = None
                    if selected_label:
                        selected_id = ekg_options[selected_label]
                        selected_test = next(test for test in ekg_tests if test["id"] == selected_id)
                        user_data = [person]
                        ekg = EKGdata.load_by_id(selected_id, user_data)
                        min_ms = int(ekg.df["Zeit in ms"].min())
                        max_ms = int(ekg.df["Zeit in ms"].max())
                        default_end = min(min_ms + 10000, max_ms)

                        st.write("#### Analyse gesamter Messdaten")
                        st.write("Länge der Zeitreihe:", ekg.get_duration_str())
                        if ekg.time_was_corrected:
                            st.warning("Hinweis: In der ausgewählten EKG-Datei wurden fehlerhafte Zeitstempel erkannt. Diese wurden automatisch korrigiert. Die Ergebnisse können dennoch Ungenauigkeiten enthalten.")

                        st.markdown("### 📉 Visualisierung")
                        st.write("#### Zeitbereich für Analyse auswählen")
                        time_range = st.slider("Analyse-Zeitraum (ms)",
                            min_value=min_ms,
                            max_value=max_ms,
                            value=(min_ms, default_end),
                            step=100,
                            key="slider_user")
                        ekg.set_time_range(time_range)
                        st.write("#### Peak-Erkennung anpassen")
                        with st.container():
                            peak_col1, peak_col2 = st.columns([1, 4])
                            with peak_col1:
                                height_input = st.number_input(
                                    "Peak-Schwelle",
                                    min_value=0.0,
                                    max_value=2000.0,
                                    value=350.0,
                                    step=1.0,
                                    format="%.1f",
                                    key=f"height_input_{st.session_state['role']}_{selected_id}",
                                    help="Schwellwert für Ausschläge in der Peak-Erkennung (Standard: 350). Dieser Wert kann an 'raw' oder skalierte EKG-Dateien angepasst werden."
                                )
                        # Wichtig: detect_peaks_globally() muss vor detect_rr_anomalies() aufgerufen werden!
                        ekg.detect_peaks_globally(height=height_input)
                        if not ekg.peaks:
                            st.warning("⚠️ Es wurden keine Peaks erkannt. Bitte einen niedrigeren Wert für die Höhe eingeben.")
                        if ekg.peaks:
                            try:
                                ekg.detect_rr_anomalies()
                            except ValueError:
                                st.info("⚠️ Für diese Einstellungen konnten keine verwertbaren EKG-Daten erkannt werden. Bitte den Wert für die Peak-Erkennung anpassen.")
                        else:
                            st.info("Keine Peaks erkannt – Anomalie-Erkennung wird übersprungen.")
                        # Herzfrequenz erst nach Peak-Erkennung schätzen!
                        estimated_hr = ekg.estimate_hr()
                        ekg.plot_time_series()
                        # Graphen werden jetzt unterhalb der Columns angezeigt, daher hier nur vorbereiten
                        hr_fig = ekg.plot_hr_over_time()
                    else:
                        st.info("❕ Keine EKG-Daten für diese Person vorhanden.")
                else:
                    st.info("Keine EKG-Daten für diese Person verfügbar.")

            # --- Graphen unterhalb der Columns in voller Breite darstellen ---
            if ekg is not None:
                st.plotly_chart(ekg.fig, use_container_width=True, height=400, key="plot_user_fig")
                if hr_fig is not None:
                    st.plotly_chart(hr_fig, use_container_width=True, height=400, key="plot_user_hr")
