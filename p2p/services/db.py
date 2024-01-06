import mysql.connector

mydb = mysql.connector.connect(
    host="metaml0.mysql.database.azure.com",
    user="metamladmin@metaml0",
    password="Password%",
    database="Meta_ML"
)

mycursor = mydb.cursor()

sql = "INSERT INTO `business_problem` (`Index`, `Name`) VALUES (31661075511, 'ASD Research')"
sql1 ="DELETE from dimension where Name = 'Blood Oxygen Level'"
mycursor.execute(sql)

mydb.commit()

print(mycursor.rowcount, "record inserted.")
