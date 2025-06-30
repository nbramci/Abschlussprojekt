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
                st.session_state["is_logged_in"] = True
                st.session_state["current_user_name"] = matched_user["username"]
                all_users = load_user_objects()
                st.session_state["current_user"] = next((p for p in all_users if p.username == matched_user["username"]), None)
                st.session_state["role"] = matched_user.get("role", "user")
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
        admin_option = st.radio("Aktion auswählen", ["Benutzer suchen", "Neue Person anlegen"])

        if admin_option == "Benutzer suchen":
            all_users = load_user_objects()
            suchname = st.text_input("Benutzer suchen (Vor- oder Nachname)")
            matching_users = [
                p for p in all_users if suchname.lower() in p.firstname.lower() or suchname.lower() in p.lastname.lower()
            ]
            if matching_users:
                selected = st.selectbox("Nutzer auswählen", [f"{p.firstname} {p.lastname}" for p in matching_users])
                person = next(p for p in matching_users if f"{p.firstname} {p.lastname}" == selected)

                tabs = st.tabs(["👤 Übersicht & Analyse", "⚙️ Bearbeiten / Löschen"])

                with tabs[0]:
                    col1, col2 = st.columns([1, 2])

                    with col1:
                        st.markdown("### 🧍 Versuchsperson")
                        st.image(person.picture_path, caption=person.get_full_name())
                        st.markdown(f"**Name:** {person.get_full_name()}")
                        st.markdown(f"**ID:** `{person.id}`")
                        st.markdown(f"**Geburtsjahr:** {person.date_of_birth}")
                        st.markdown(f"**Maximale Herzfrequenz (geschätzt):** {person.calc_max_heart_rate()} bpm")

                    with col2:
                        st.markdown("### ⚙️ Analyseoptionen")
                        ekg_tests = person.ekg_tests
                        if ekg_tests:
                            ekg_options = {f"Test {i+1} am {t['date']}": t["id"] for i, t in enumerate(ekg_tests)}
                            selected_label = st.selectbox("Wählen Sie einen EKG-Test", list(ekg_options.keys()), key="ekg_select_admin")
                            selected_id = ekg_options[selected_label]
                            selected_test = next(test for test in ekg_tests if test["id"] == selected_id)
                            user_data = [person]
                            ekg = EKGdata.load_by_id(selected_id, user_data)
                            ekg.detect_peaks_globally()

                            min_ms = int(ekg.df.index.min())
                            max_ms = int(ekg.df.index.max())
                            default_end = min(min_ms + 10000, max_ms)

                            st.write("#### Zeitbereich für Analyse auswählen")
                            time_range = st.slider("Analyse-Zeitraum (ms)",
                                                   min_value=min_ms,
                                                   max_value=max_ms,
                                                   value=(min_ms, default_end),
                                                   step=100,
                                                   key="slider_admin")
                            ekg.set_time_range(time_range)

                            st.write("#### Analyse gesamter Messdaten")
                            st.write("Länge der Zeitreihe:", ekg.get_duration_str())
                            if ekg.time_was_corrected:
                                st.warning("Hinweis: In der ausgewählten EKG-Datei wurden fehlerhafte Zeitstempel erkannt. Diese wurden automatisch korrigiert. Die Ergebnisse können dennoch Ungenauigkeiten enthalten.")
                            estimated_hr = ekg.estimate_hr()
                        else:
                            st.info("Keine EKG-Daten für diese Person verfügbar.")

                        if ekg_tests:
                            st.markdown("### 📉 Visualisierung")
                            st.write("#### EKG-Zeitreihe")
                            ekg.plot_time_series()
                            st.plotly_chart(ekg.fig, use_container_width=True, height=250, key="plot_admin_fig")

                            st.write(f"Geschätzte Herzfrequenz aus dem EKG: {round(estimated_hr)} bpm")

                            st.write("#### Herzfrequenz-Verlauf")
                            hr_fig = ekg.plot_hr_over_time()
                            st.plotly_chart(hr_fig, use_container_width=True, height=250, key="plot_admin_hr")

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

            with col1:
                st.markdown("### 🧍 Versuchsperson")
                st.image(person.picture_path, caption=person.get_full_name())
                st.markdown(f"**Name:** {person.get_full_name()}")
                st.markdown(f"**ID:** `{person.id}`")
                st.markdown(f"**Geburtsjahr:** {person.date_of_birth}")
                st.markdown(f"**Maximale Herzfrequenz (geschätzt):** {person.calc_max_heart_rate()} bpm")

            with col2:
                st.markdown("### ⚙️ Analyseoptionen")
                ekg_tests = person.ekg_tests
                if ekg_tests:
                    ekg_options = {f"Test {i+1} am {t['date']}": t["id"] for i, t in enumerate(ekg_tests)}
                    selected_label = st.selectbox("Wählen Sie einen EKG-Test", list(ekg_options.keys()), key="ekg_select_user")
                    selected_id = ekg_options[selected_label]
                    selected_test = next(test for test in ekg_tests if test["id"] == selected_id)
                    user_data = [person]
                    ekg = EKGdata.load_by_id(selected_id, user_data)
                    ekg.detect_peaks_globally()

                    min_ms = int(ekg.df.index.min())
                    max_ms = int(ekg.df.index.max())
                    default_end = min(min_ms + 10000, max_ms)

                    st.write("#### Zeitbereich für Analyse auswählen")
                    time_range = st.slider("Analyse-Zeitraum (ms)",
                                           min_value=min_ms,
                                           max_value=max_ms,
                                           value=(min_ms, default_end),
                                           step=100,
                                           key="slider_user")
                    ekg.set_time_range(time_range)

                    st.write("#### Analyse gesamter Messdaten")
                    st.write("Länge der Zeitreihe:", ekg.get_duration_str())
                    if ekg.time_was_corrected:
                        st.warning("Hinweis: In der ausgewählten EKG-Datei wurden fehlerhafte Zeitstempel erkannt. Diese wurden automatisch korrigiert.")
                    estimated_hr = ekg.estimate_hr()
                else:
                    st.info("Keine EKG-Daten für diese Person verfügbar.")

                if ekg_tests:
                    st.markdown("### 📉 Visualisierung")
                    st.write("#### EKG-Zeitreihe")
                    ekg.plot_time_series()
                    st.plotly_chart(ekg.fig, use_container_width=True, height=250, key="plot_user_fig")

                    st.write(f"Geschätzte Herzfrequenz aus dem EKG: {round(estimated_hr)} bpm")

                    st.write("#### Herzfrequenz-Verlauf")
                    hr_fig = ekg.plot_hr_over_time()
                    st.plotly_chart(hr_fig, use_container_width=True, height=250, key="plot_user_hr")

