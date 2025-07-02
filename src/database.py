# Modul zur Verwaltung von Personendaten in einer TinyDB-Datenbank
from tinydb import TinyDB, Query
from tinydb.storages import JSONStorage
from tinydb.middlewares import CachingMiddleware

# Initialisierung der TinyDB-Datenbank und Zugriff auf die Standard-Tabelle (_default)
db = TinyDB("data/tinydb_person_db.json", storage=CachingMiddleware(JSONStorage))
personen_table = db  # Verwende Standard-Tabelle (_default)

# Zugriff auf die Datenbankabfrage-API
PersonQuery = Query()

def get_all_persons():
    # Gibt alle Personen aus der Datenbank zurück.
    return personen_table.all()

def find_person_by_id(person_id):
    # Sucht eine Person anhand der ID.
    return personen_table.search(PersonQuery.id == person_id)

def insert_person(person_data):
    # Fügt eine neue Person in die Datenbank ein.
    personen_table.insert(person_data)

def update_person(person_id, updated_data):
    # Aktualisiert die Daten einer Person anhand der ID.
    existing = personen_table.get(PersonQuery.id == person_id)
    if not existing:
        return

    # Fehlende Felder aus bestehendem Datensatz ergänzen (z. B. Passwort)
    for key, value in existing.items():
        if key not in updated_data:
            updated_data[key] = value

    personen_table.update(updated_data, PersonQuery.id == person_id)

def delete_person(person_id):
    # Löscht eine Person anhand der ID aus der Datenbank.
    personen_table.remove(PersonQuery.id == person_id)

def find_person_by_username(username):
    # Sucht eine Person anhand des Benutzernamens.
    return personen_table.get(PersonQuery.username == username)

def insert_new_user(user_data):
    # Fügt einen neuen Benutzer in die Datenbank ein.
    return personen_table.insert(user_data)