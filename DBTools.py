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

def initialiseDB():
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
                         CONSTRAINT PK_Name PRIMARY KEY(MediaName))''')
        cursor.execute('''CREATE TABLE Tropes
                       (TropeName text NOT NULL,
                        TropeUrl text,
                        TropeTitle text,
                        CONSTRAINT PK_Trope PRIMARY KEY(TropeName))''')
        cursor.execute('''CREATE TABLE MediaTropes
                       (Media text NOT NULL, 
                        Trope text NOT NULL, 
                        Strength real,
                        Direction int,
                        CONSTRAINT PK_MediaTrope PRIMARY KEY(Media,Trope))''')
#                 CONSTRAINT FK_MediaName FOREIGN KEY (Media) References Media(MediaName)
#                 CONSTRAINT FK_TropeName FOREIGN KEY (Trope) References Tropes(TropeName))''')

        connection.commit()
        return connection

