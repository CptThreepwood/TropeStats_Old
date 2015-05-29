import sqlite3
import os.path

# Add Media to Media List
# Doesn't commit straight away - Media should only be in here if it's finished parsing
def add_media(dbconnection, mediaKey, mediaUrl, mediaTitle):
    try:
        dbconnection.execute("INSERT INTO Media VALUES (?, ?, ?, date('now'))", (mediaKey, mediaUrl, mediaTitle))
    except sqlite3.IntegrityError:
        print "Attempted to add media page ", mediaKey, " twice: ", mediaUrl
    return

# Add Trope to Trope List
# Doesn't commit straight away - Media should only be in here if it's finished parsing
def add_trope(dbconnection, tropeKey, tropeUrl, tropeTitle):
    try:
        dbconnection.execute("INSERT INTO Tropes VALUES (?, ?, ?, date('now'))", (tropeKey, tropeUrl, tropeTitle))
    except sqlite3.IntegrityError:
        print "Attempted to add media page ", tropeKey, " twice: ", tropeUrl
    return

# Add link between Media and Trope
# Direction shows if the link is bidirectional (0) or directed (-1 Trope->Media, +1 Media->Trope)
# Doesn't commit straight away - Media should only be in here if it's finished parsing
def add_relation(dbconnection, mediaKey, tropeKey, strength, direction):
    dbcursor = dbconnection.cursor()
    dbcursor.execute("SELECT * FROM MediaTropes WHERE Media=? AND Trope=?", (mediaKey, tropeKey))
    result = dbcursor.fetchone()
    if result:
        if result[3] != direction:
            dbcursor.execute("UPDATE MediaTropes SET Direction=0 WHERE Media=? AND Trope=?", (mediaKey, tropeKey))
    else:
        try:
            dbcursor.execute("INSERT INTO MediaTropes VALUES (?, ?, ?, ?)", (mediaKey, tropeKey, strength, direction))
        except sqlite3.IntegrityError:
            print "Tried to add a relation that already exists but SELECT didn't find.  What is going on?"
            print pageKey, '\t', tropeKey
    return

# Save a new url we've found
# Commited straight away, no issue if calling script crashes mid-parse
def add_url(dbconnection, url, redirect = None):
    if not redirect:
        redirect = url
    try:
        with dbconnection:
            dbconnection.execute("INSERT INTO UrlChecklist VALUES (?, ?, 0)", (url, redirect))
    except sqlite3.IntegrityError:
        print "Tried to add a url that already exists"
        print url
    return

# Save that we've checked a given Url
# Wait until the calling script wants to commit
# Update based on Redirect as we may need to change several entries
def checked_url(dbconnection, url)
    try:
            dbconnection.execute("UPDATE UrlChecklist SET Visited=1 WHERE Redirect=?", (url))
    return

# Return a list of unvisited Urls to visit and a list of visited Urls to avoid
# Visited Urls should include both urls and any redirects
def get_urls(dbconnection):
    dbcursor = dbconnection.cursor()
    dbcursor.execute("SELECT Url FROM UrlChecklist WHERE Visited=0")
    newUrls = dbcursor.fetchall()
    dbcursor.execute("SELECT Url FROM UrlChecklist WHERE Visited=1")
    oldUrls = dbcursor.fetchall()
    dbcursor.execute("SELECT Redirect FROM UrlChecklist WHERE Url != Redirect")
    oldUrls += dbcursor.fetchall()
    return newUrls, oldUrls

# Return a list of tuples (url, redirect)
# Useful to avoid testing a url we already know redirects to something else
def get_redirects(dbconnection):
    dbcursor = dbconnection.cursor()
    dbcursor.execute("SELECT Url, Redirect FROM UrlChecklist")
    redirects = dbcursor.fetchall()
    return redirects

# Get a list of media or tropes that is at least a week old
def get_oldmedia(dbconnection):
    dbcursor = dbconnection.cursor()
    # Find all media for which the last visit less than 7 days from now
    dbcursor.execute("SELECT MediaName FROM Media WHERE date(LastVisited) BETWEEN date('now', '-7 days') AND date('now')")
    all_media = dbcursor.fetchall()
    return all_media

def get_oldtropes(dbconnection):
    dbcursor = dbconnection.cursor()
    # Find all tropes for which the last visit less than 7 days from now
    dbcursor.execute("SELECT TropeName FROM Tropes WHERE date(LastVisited) BETWEEN date('now', '-7 days') AND date('now')")
    all_tropes = dbcursor.fetchall()
    return all_tropes

# Connect to DB or create it if no DB is found
def initialise_db():
    # Connect to DB
    if os.path.isfile('TropeStats.db'):
        connection = sqlite3.connect('TropeStats.db')
        return connection
    # Create DB
    else:
        connection = sqlite3.connect('TropeStats.db')
        cursor = connection.cursor()

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

        connection.commit()
        return connection

