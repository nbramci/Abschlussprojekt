from tinydb import TinyDB, Query
from tinydb.storages import JSONStorage
from tinydb.middlewares import CachingMiddleware

# Initialisierung der TinyDB-Datenbank und Zugriff auf die Standard-Tabelle (_default)
db = TinyDB("data/tinydb_person_db.json", storage=CachingMiddleware(JSONStorage))
personen_table = db  # Verwende Standard-Tabelle (_default)

# Zugriff auf die Datenbankabfrage-API
PersonQuery = Query()

# Funktion: Alle Personen abrufen
def get_all_persons():
    return personen_table.all()

# Funktion: Eine bestimmte Person suchen
def find_person_by_id(person_id):
    return personen_table.search(PersonQuery.id == person_id)

# Funktion: Neue Person einfügen
def insert_person(person_data):
    personen_table.insert(person_data)

# Funktion: Eine Person aktualisieren
def update_person(person_id, updated_data):
    personen_table.update(updated_data, PersonQuery.id == person_id)

# Funktion: Eine Person löschen
def delete_person(person_id):
    personen_table.remove(PersonQuery.id == person_id)