"""
Database related functions
"""
import settings
import sqlite3
import os.path
import logging

class DataHandler(object):
    """ Class to handle persistent data """

    def __init__(self):
        """ Connect to DB or create it if no DB is found """
        # Connect to DB
        if os.path.isfile(settings.DB_LOCATION):
            self.connection = sqlite3.connect(settings.DB_LOCATION)
        # Create DB
        else:
            self.connection = sqlite3.connect(settings.DB_LOCATION)
            cursor = self.connection.cursor()

            # Build Tables
            cursor.execute('''CREATE TABLE Media
                            (MediaName text NOT NULL,
                             MediaUrl text,
                             MediaTitle text,
                             LastVisited text,
                             CONSTRAINT PK_Name PRIMARY KEY(MediaName))''')
            cursor.execute('''CREATE TABLE Tropes
                           (TropeName text NOT NULL,
                            TropeUrl text,
                            TropeTitle text,
                            LastVisited text,
                            CONSTRAINT PK_Trope PRIMARY KEY(TropeName))''')
            cursor.execute('''CREATE TABLE MediaTropes
                           (Media text NOT NULL,
                            Trope text NOT NULL,
                            Strength real,
                            Direction int,
                            CONSTRAINT PK_MediaTrope PRIMARY KEY(Media,Trope))''')
            cursor.execute('''CREATE TABLE UrlChecklist
                            (Url text NOT NULL,
                             Redirect text,
                             Visited int,
                             CONSTRAINT PK_Url PRIMARY KEY(Url))''')
            cursor.execute('''CREATE TABLE ParentIndicies
                           (Child text NOT NULL,
                            Parent text NOT NULL,
                            CONSTRAINT PK_MediaTrope PRIMARY KEY(Child,Parent))''')
            self.connection.commit()

    def add_media(self, media_key, media_url, media_title):
        """
        Add Media to Media List
        Doesn't commit straight away - Media should only be in here if it's
        finished parsing
        """
        try:
            self.connection.execute(
                "INSERT INTO Media VALUES (?, ?, ?, date('now'))",
                (media_key, media_url, media_title))

        except sqlite3.IntegrityError:
            logging.error("Attempted to add media page %s twice: %s", media_key, media_url)
        return

    def add_trope(self, trope_key, trope_url, trope_title):
        """
        Add Trope to Trope List
        Doesn't commit straight away - Media should only be in here if it's
        finished parsing
        """
        try:
            self.connection.execute(
                "INSERT INTO Tropes VALUES (?, ?, ?, date('now'))",
                (trope_key, trope_url, trope_title))
        except sqlite3.IntegrityError:
            logging.error("Attempted to add media page %s twice: %s", trope_key, trope_url)
        return

    def add_relation(self, media_key, trope_key, strength, direction):
        """
        Add link between Media and Trope
        Direction shows if the link is bidirectional (0) or directed (-1
        Trope->Media, +1 Media->Trope) Doesn't commit straight away - Media
        should only be in here if it's finished parsing
        """
        dbcursor = self.connection.cursor()
        dbcursor.execute("SELECT * FROM MediaTropes WHERE Media=? AND Trope=?",
                         (media_key, trope_key))
        result = dbcursor.fetchone()
        if result:
            if result[3] != direction:
                dbcursor.execute(
                    "UPDATE MediaTropes SET Direction=0 WHERE Media=? AND Trope=?",
                    (media_key, trope_key))
        else:
            try:
                dbcursor.execute(
                    "INSERT INTO MediaTropes VALUES (?, ?, ?, ?)",
                    (media_key, trope_key, strength, direction))
            except sqlite3.IntegrityError:
                logging.error("Tried to add a relation that already exists but could not SELECT")
                logging.error("%s\t%s", media_key, trope_key)
        return


    def add_index(self, child, parent):
        """ Adds an index """
        try:
            self.connection.execute("INSERT INTO ParentIndicies VALUES (?, ?)", (child, parent))
        except sqlite3.IntegrityError:
            logging.error("Index %s already stored for %s", parent, child)
        return

    def add_url(self, url, redirect=None):
        """
        Save a new url we've Commited straight away
        No issue if calling script crashes mid-parse
        """
        if not redirect:
            redirect = url
        try:
            self.connection.execute("""
                INSERT INTO UrlChecklist VALUES (?, ?, 0)""", (url, redirect))
        except sqlite3.IntegrityError:
            logging.error("Tried to add a url that already exists: %s", url)
        return

    def checked_url(self, url):
        """
        Save that we've checked a given Url
        Commit immediately - maybe unintuitive
        Update based on Redirect as we may need to change several entries
        """
        logging.info("Finished %s", url)
        try:
            self.connection.execute("""
                UPDATE UrlChecklist
                SET Visited=1
                WHERE Redirect=?""", (url,))
        except KeyboardInterrupt:
            logging.error("Url update failed")
        return

    def commit_page(self, url):
        """ Commits a page """
        self.connection.commit()
        self.checked_url(url)
        return

    def get_urls(self):
        """
        Return a list of unvisited Urls to visit and a list of visited Urls to avoid
        Visited Urls should include both urls and any redirects
        """
        dbcursor = self.connection.cursor()
        dbcursor.execute("SELECT Url FROM UrlChecklist WHERE Visited=0")
        new_urls = dbcursor.fetchall()
        dbcursor.execute("SELECT Url FROM UrlChecklist WHERE Visited=1")
        old_urls = dbcursor.fetchall()
        dbcursor.execute("""
            SELECT Redirect
            FROM UrlChecklist
            WHERE Url != Redirect""")
        old_urls += dbcursor.fetchall()
        return new_urls, old_urls

    def get_redirects(self):
        """
        Return a list of tuples (url, redirect) - Useful to avoid testing a url
        we already know redirects to something else
        """
        dbcursor = self.connection.cursor()
        dbcursor.execute("SELECT Url, Redirect FROM UrlChecklist")
        redirects = dbcursor.fetchall()
        return redirects

    def get_media(self):
        """ Get a list of all media """
        dbcursor = self.connection.cursor()
        dbcursor.execute("""
            SELECT MediaName
            FROM Media
            """)
        all_media = [elem[0] for elem in dbcursor.fetchall()]
        return all_media

    def get_oldmedia(self):
        """ Get a list of media or tropes that is at least a week old """
        dbcursor = self.connection.cursor()
        # Find all media for which the last visit less than 7 days from now
        dbcursor.execute("""
            SELECT MediaName
            FROM Media
            WHERE date(LastVisited) BETWEEN date('now', '-7 days')
            AND date('now')
            """)
        all_media = dbcursor.fetchall()
        return all_media

    def get_tropes(self):
        """ Get a list of all tropes """
        dbcursor = self.connection.cursor()
        dbcursor.execute("""
            SELECT TropeName
            FROM Tropes
            """)
        all_tropes = [elem[0] for elem in dbcursor.fetchall()]
        return all_tropes

    def get_oldtropes(self):
        """ Returns old tropes """
        dbcursor = self.connection.cursor()
        # Find all tropes for which the last visit less than 7 days from now
        dbcursor.execute("""
            SELECT TropeName
            FROM Tropes
            WHERE date(LastVisited) BETWEEN date('now', '-7 days')
            AND date('now')
            """)
        all_tropes = dbcursor.fetchall()
        return all_tropes

    def get_relations(self):
        """ Get a list of all media-trope relationships """
        dbcursor = self.connection.cursor()
        dbcursor.execute("""
            SELECT *
            FROM MediaTropes
            """)
        all_relations = dbcursor.fetchall()
        return all_relations

    def execute_query(self, query):
        """ Execute an SQL query.  Pass this SANITISED strings only """
        sql_blacklist = ['drop', 'delete']
        if any(word.casefold() in query.casefold() for word in sql_blacklist):
            print("No queries with {0} will be executed".format([word for word in sql_blacklist if word.casefold() in query.casefold()][0]))
            return
        dbcursor = self.connection.cursor()
        dbcursor.execute(query)
        result = dbcursor.fetchall()
        return result

