import pymysql
import metaml


class parser:
    def __init__(self, domain, dimension, application_area, business_problem, customer_profile):
        self.domain = domain
        self.dimension = dimension
        self.application_area = application_area
        self.business_problem = business_problem
        self.customer_profile = customer_profile
        self.context = ['0', '0', '0', '0', '0']

    def get_domain(self, connection: 'pymysql.Connection'):
        query = "Select * from domains where Name = '" + self.domain + "'"
        with connection.cursor() as cursor:
            print(query)
            cursor.execute(query)
            self.context[0] = str(cursor.fetchall()[0][0])

    def get_dimension(self, connection: 'pymysql.Connection'):
        query = "Select * from dimension where Name = '" + self.dimension + "'"
        with connection.cursor() as cursor:
            print(query)
            cursor.execute(query)
            self.context[1] = str(cursor.fetchall()[0][0])

    def get_application_area(self, connection: 'pymysql.Connection'):
        query = "Select * from application_area where Name = '" + self.application_area + "'"
        with connection.cursor() as cursor:
            print(query)
            cursor.execute(query)
            self.context[2] = str(cursor.fetchall()[0][0])

    def get_business_problem(self, connection: 'pymysql.Connection'):
        query = "Select * from business_problem where Name = '" + self.business_problem + "'"
        with connection.cursor() as cursor:
            print(query)
            cursor.execute(query)
            self.context[3] = str(cursor.fetchall()[0][0])

    def get_customer_profile(self, connection: 'pymysql.Connection'):
        query = "Select * from customer_profile where Name = '" + self.customer_profile + "'"
        with connection.cursor() as cursor:
            print(query)
            cursor.execute(query)
            self.context[4] = str(cursor.fetchall()[0][0])


    def process(self):
        with pymysql.connect(host=metaml.db_host,
                             port=metaml.db_port,
                             user=metaml.db_user,
                             database=metaml.database,
                             password=metaml.db_password) as db_connection:

            parser.get_domain(self, connection=db_connection)
            parser.get_dimension(self, connection=db_connection)
            parser.get_application_area(self, connection=db_connection)
            parser.get_business_problem(self, connection=db_connection)
            parser.get_customer_profile(self, connection=db_connection)

        return self.context
