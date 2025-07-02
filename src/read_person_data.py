# Modul zum Laden von Personen aus der TinyDB-Datenbank und zur Erstellung von Person-Objekten
from tinydb import TinyDB, Query
import os
from .person import Person  # Relativer Modulimport

def load_user_objects():
    # Lädt alle Personen aus der Datenbank und erstellt Person-Objekte.
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
            person_dict.get("username", ""),
            person_dict.get("password", "")
        )
        person_list.append(current_person)

    return person_list

def get_person_object_from_list_by_name(firstname, lastname, users):
    # Gibt ein Person-Objekt anhand von Vor- und Nachname zurück.
    for person in users:
        if (
            person.firstname and person.lastname and
            person.firstname.strip().lower() == firstname.strip().lower() and
            person.lastname.strip().lower() == lastname.strip().lower()
        ):
            return person
    return None