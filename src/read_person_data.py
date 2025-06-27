"""
Dieses Modul enthält Funktionen zur Verarbeitung und Abfrage von Personendaten aus TinyDB.

Funktionen:
- load_user_objects(): Lädt alle Benutzer:innen aus der Datenbank und erstellt Person-Objekte.
- get_person_object_from_list_by_name(): Gibt ein bestimmtes Person-Objekt anhand des Namens zurück.
"""

from tinydb import TinyDB, Query
import os
from .person import Person  # Relativer Modulimport

# -------------------- Personenbezogene Datenverarbeitung --------------------

# Lädt alle Benutzer:innen aus TinyDB und erstellt Person-Objekte
def load_user_objects():
    """
    Lädt alle Benutzer:innen aus der TinyDB-Datenbank 'tinydb_person_db.json',
    erstellt für jeden Eintrag ein Person-Objekt und gibt eine Liste dieser Objekte zurück.
    """
    db = TinyDB("data/tinydb_person_db.json")
    data = db.all()  # Zugriff auf _default-Tabelle

    person_list = []
    for person_dict in data:
        current_person = Person(
            person_dict["id"],
            person_dict["date_of_birth"],
            person_dict["firstname"],
            person_dict["lastname"],
            person_dict["picture_path"],
            person_dict["ekg_tests"],
            person_dict.get("gender", "unknown"),
            person_dict.get("role", "user"),
            person_dict.get("username", "")
        )
        person_list.append(current_person)

    return person_list

# Sucht ein bestimmtes Person-Objekt aus der Liste anhand des Namens
def get_person_object_from_list_by_name(firstname, lastname, users):
    for person in users:
        if (
            person.firstname and person.lastname and
            person.firstname.strip().lower() == firstname.strip().lower() and
            person.lastname.strip().lower() == lastname.strip().lower()
        ):
            return person
    return None