# Modul zur Repräsentation von Personen mit persönlichen Daten und EKG-Tests
from datetime import datetime

class Person:
    # Repräsentiert eine Person mit persönlichen Daten und EKG-Tests.

    def __init__(self, id: int, date_of_birth: str, firstname: str, lastname: str, picture_path: str, ekg_tests, gender="unknown", role="user", username="", password=""):
        # Initialisiert die Person mit den angegebenen Attributen.
        self.id = id
        self.date_of_birth = date_of_birth
        self.firstname = firstname
        self.lastname = lastname
        self.picture_path = picture_path
        self.ekg_tests = ekg_tests
        self.gender = gender
        self.role = role
        self.username = username
        self.password = password

    def get_full_name(self):
        # Gibt den vollständigen Namen zurück.
        return self.lastname + ", " + self.firstname

    def calc_age(self):
        # Berechnet das Alter anhand des Geburtsjahres.
        try:
            birth_year = int(self.date_of_birth)
            current_year = datetime.now().year
            return current_year - birth_year
        except ValueError:
            return None

    def calc_max_heart_rate(self):
        # Berechnet die maximale Herzfrequenz.
        age = self.calc_age()
        if hasattr(self, "gender") and self.gender.lower() == "female":
            return 226 - age
        return 220 - age

    @classmethod
    def load_by_id(cls, id, db):
        # Lädt eine Person anhand der ID aus der Datenbank.
        for person in db:
            if person.id == id:
                return person
        raise ValueError(f"Person mit ID {id} nicht gefunden.")