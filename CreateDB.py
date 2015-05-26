import sqlite3

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
connection.close()

