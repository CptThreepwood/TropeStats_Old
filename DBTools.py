import sqlite3

def add_media(dbconnection, mediaKey, mediaUrl, mediaTitle):
    try:
        dbconnection.execute("INSERT INTO Media VALUES (?, ?, ?)", (mediaKey, mediaUrl, mediaTitle))
    except sqlite3.IntegrityError:
        print "Attempted to add media page ", mediaKey, " twice: ", mediaUrl
    return

def add_trope(dbconnection, tropeKey, tropeUrl, tropeTitle):
    try:
        dbconnection.execute("INSERT INTO Tropes VALUES (?, ?, ?)", (tropeKey, tropeUrl, tropeTitle))
    except sqlite3.IntegrityError:
        print "Attempted to add media page ", tropeKey, " twice: ", tropeUrl
    return

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

def load_media(dbconnection):
    dbcursor = dbconnection.cursor()
    dbcursor.execute("SELECT MediaName FROM Media")
    all_media = dbcursor.fetchall()
    return all_media

def load_tropes(dbconnection):
    dbcursor = dbconnection.cursor()
    dbcursor.execute("SELECT TropeName FROM Tropes")
    all_tropes = dbcursor.fetchall()
    return all_tropes


