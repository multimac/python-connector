import sys
sys.path.append('../Classes')
#sys.path.append('../../python-connector')

from blazingdb import BlazingPyConnector, BlazingETL
import psycopg2 as postgres

#from PostgresHandler import PostgresHandler
#from LocalBlazingHandler import LocalBlazingHandler
#from PostgresComparisonTestSet import PostgresComparisonTestSet
import datetime
from decimal import Decimal

# Blazing Connection
bl = BlazingPyConnector('localhost','test@blazingdb.com','tester','test')
print "Connection"
# Postgresql Connection
pg = postgres.connect(host='localhost',dbname='tests',user='postgres',password='postgres')
migrator = BlazingETL(pg, bl)
migrator.migrate(
    create_tables=False,                                            # Specify if it's needed to create the tables in the migration
    files_local_path='/home/second/data/',                              # Specify where will the migration data files stored
    blazing_files_destination_path='/opt/blazing/disk1/blazing/blazing-uploads/2/',     # Specify in case it's wanted to copy the data to BlazingDB uploads folder
    chunk_size=50,                                              # Specify the size of the chunks of data to migrate
    export_data_from_origin=True,                                  # Turn to False in case you already have the and only need to load them into BlazingDb
    copy_data_to_blazing=False,                                     # Turn to True in case you want to copy the data to BlazingDB uploads folder
    load_data_into_blazing=True,                                    # Turn to False in case you want to migrate only the structure and not the data
    file_extension='.dat',                                          # Specify the data files extension
    by_stream=True                                                 # Change to false if you need the migration files generated
)

"""
ph = PostgresHandler("host=127.0.0.1 port=5432 dbname=tpch50mbx2 user=wmalpica password=blazingIsBetter")

schema="skipData"
db = "tpch50mbx2"

bh = LocalBlazingHandler("127.0.0.1", 8890, schema, db)

comp = PostgresComparisonTestSet(bh, ph)

qStr = "select c_custkey, c_name from customer order by 1, 2"
comp.runAndValidateQuery(qStr, showVerboseFails=True, orderless=False, precision=0.01)
"""
