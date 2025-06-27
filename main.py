"""
Hauptmodul der Streamlit-Anwendung zur Anzeige und Analyse von EKG-Daten.

Diese App ermöglicht die Auswahl von Versuchspersonen, zeigt deren Basisinformationen
sowie EKG-Daten und berechnet wichtige Kennwerte wie Herzfrequenz.
"""

import streamlit as st
import pandas as pd
from PIL import Image
from plotly import express as px
import numpy as np

from src.read_person_data import load_user_objects
from src.ekgdata import EKGdata
from tinydb import TinyDB, Query

st.set_page_config(page_title="EKG-Analyse")

st.title("Login")

def reset_session():
    st.session_state["is_logged_in"] = False
    st.session_state["current_user_name"] = ""
    st.session_state["current_user"] = None
    st.session_state["login_failed"] = False
    st.session_state["role"] = ""

if "is_logged_in" not in st.session_state:
    reset_session()

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
        if (user.get("username", "").strip().lower() == username.strip().lower() and
            user.get("password", "") == password):
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
    st.title("EKG-APP")
    if st.session_state["role"] == "admin":
        st.write("### Admin-Modus")
        all_users = load_user_objects()
        suchname = st.text_input("Benutzer suchen (Vor- oder Nachname)")
        matching_users = [
            p for p in all_users if suchname.lower() in p.firstname.lower() or suchname.lower() in p.lastname.lower()
        ]
        if matching_users:
            selected = st.selectbox("Nutzer auswählen", [f"{p.firstname} {p.lastname}" for p in matching_users])
            person = next(p for p in matching_users if f"{p.firstname} {p.lastname}" == selected)
        else:
            st.info("Kein passender Nutzer gefunden.")
            person = None
    else:
        person = st.session_state["current_user"]

    if person:
        st.write("# Versuchsperson auswählen")
        st.write("Aktuell ausgewählte Versuchsperson: ", f"{person.firstname} {person.lastname}")

        col1, col2 = st.columns([1, 2])
        with col1:
            st.image(person.picture_path, caption=person.get_full_name())
        with col2:
            st.markdown(f"**ID der Versuchsperson:** `{person.id}`")
            st.write(f"Geburtsjahr: {person.date_of_birth}")
            st.write(f"Maximale Herzfrequenz (geschätzt): {person.calc_max_heart_rate()} bpm")

        if st.button("Logout"):
            reset_session()
            st.rerun()

        # EKG-Auswahl und Analyse
        ekg_tests = person.ekg_tests
        if ekg_tests:
            ekg_options = {f"Test {i+1} am {t['date']}": t["id"] for i, t in enumerate(ekg_tests)}
            selected_label = st.selectbox("Wählen Sie einen EKG-Test", list(ekg_options.keys()))
            selected_id = ekg_options[selected_label]
            selected_test = next(test for test in ekg_tests if test["id"] == selected_id)
            user_data = [person]
            ekg = EKGdata.load_by_id(selected_id, user_data)

            min_ms = int(ekg.df.index.min())
            max_ms = int(ekg.df.index.max())
            default_end = min(min_ms + 10000, max_ms)

            st.write("### Zeitbereich für Analyse auswählen")
            time_range = st.slider("Analyse-Zeitraum (ms)",
                                   min_value=min_ms,
                                   max_value=max_ms,
                                   value=(min_ms, default_end),
                                   step=100)
            ekg.set_time_range(time_range)

            st.write("## Analyse gesamter Messdaten")
            st.write("Länge der Zeitreihe:", ekg.get_duration_str())
            ekg.find_peaks()
            if ekg.time_was_corrected:
                st.warning("Hinweis: In der ausgewählten EKG-Datei wurden fehlerhafte Zeitstempel erkannt. Diese wurden automatisch korrigiert. Die Ergebnisse können dennoch Ungenauigkeiten enthalten.")
            estimated_hr = ekg.estimate_hr()
            ekg.plot_time_series()

            st.plotly_chart(ekg.fig, use_container_width=True)
            st.write(f"Geschätzte Herzfrequenz aus dem EKG: {round(estimated_hr)} bpm")

            st.write("## Herzfrequenz-Verlauf")
            hr_fig = ekg.plot_hr_over_time()
            st.plotly_chart(hr_fig, use_container_width=True)
        else:
            st.info("Keine EKG-Daten für diese Person verfügbar.")
