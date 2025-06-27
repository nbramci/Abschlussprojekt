from datetime import datetime

class Person:
    """
    Repräsentiert eine getestete Person inklusive persönlicher Daten und zugehöriger EKG-Tests.
    
    Attribute:
    - id (int): Eindeutige ID der Person
    - date_of_birth (str): Geburtsdatum im Format 'YYYY-MM-DD'
    - firstname (str): Vorname
    - lastname (str): Nachname
    - picture_path (str): Pfad zum Bild der Person
    - ekg_tests (list): Liste von EKG-Testdaten (z. B. Dictionaries)
    - gender (str): Geschlecht der Person ("male", "female" oder "unknown")
    - role (str): Rolle der Person in der App, z. B. "user" oder "admin"
    
    Methoden:
    - get_full_name(): Gibt den vollständigen Namen im Format 'Nachname, Vorname' zurück.
    - calc_max_heart_rate(): Berechnet die maximale Herzfrequenz auf Basis des Alters und Geschlechts.
    - load_by_id(): Lädt eine Person anhand der ID aus einer übergebenen Datenbank.
    """

    def __init__(self, id: int, date_of_birth: str, firstname: str, lastname: str, picture_path: str, ekg_tests, gender="unknown", role="user"):
        """
        Initialisiert eine neue Person mit den angegebenen Attributen.

        role (str): Die Benutzerrolle ("user" oder "admin"), Standard ist "user"
        """
        self.id = id
        self.date_of_birth = date_of_birth
        self.firstname = firstname
        self.lastname = lastname
        self.picture_path = picture_path
        self.ekg_tests = ekg_tests
        self.gender = gender
        self.role = role

    def get_full_name(self):
        """
        Gibt den vollständigen Namen der Person zurück.
        """
        return self.lastname + ", " + self.firstname

    def calc_age(self):
        """
        Berechnet das aktuelle Alter der Person auf Basis des Geburtsjahres.
        """
        try:
            birth_year = int(self.date_of_birth)
            current_year = datetime.now().year
            return current_year - birth_year
        except ValueError:
            return None

    def calc_max_heart_rate(self):
        """
        Berechnet die maximale Herzfrequenz basierend auf Alter und Geschlecht.
        """
        age = self.calc_age()
        if hasattr(self, "gender") and self.gender.lower() == "female":
            return 226 - age
        return 220 - age

    @classmethod
    def load_by_id(cls, id, db):
        """
        Sucht in der übergebenen Datenbank nach einer Person mit der angegebenen ID.
        Gibt das entsprechende Objekt zurück oder wirft einen Fehler, falls nicht gefunden.
        """
        for person in db:
            if person.id == id:
                return person
        raise ValueError(f"Person mit ID {id} nicht gefunden.")