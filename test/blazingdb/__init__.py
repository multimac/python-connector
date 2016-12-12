# coding=utf-8
import requests
import json
import psycopg2 as pg
import threading
import shutil
import sys
from socket import *
import glob, os
import linecache
import math

class BlazingImporter:
    """ Data Importer """

    def __init__(self, bl_connection):
        self.connection = bl_connection
        self.id_connection = self.connection.connect()

    def small_load_datastream(self, query):
        """small load data stream"""
        print query
        try:
            result = self.connection.run(query, self.id_connection)
            #print result.status
            #print result.rows
        except Exception as e:
            print('Error: %s' % e)

    def get_columns(self, file):
        """ Get Columns and Format Them """
        # Get columns
        columns = linecache.getline(file, 1)
        columns = columns.replace("\n","")
        # Get datatypes
        datatypes = linecache.getline(file, 2)
        datatypes = datatypes.replace("\n","")
        # Columns and Datetypes Arrays
        columns_arr = columns.split("|")
        datatypes_arr = datatypes.split("|")
        # Columns with Datatype Converted
        columns_desc = []
        # Loop by Datatypes
        for i in range(len(datatypes_arr)):
            type = datatypes_arr[i]
            column = columns_arr[i]
            # Convert DataTypes
            blazing_type = 'datatype'
            types = {
                'integer':'long',
                'character varying':'string',
                'character':'string',
                'varchar':'string',
                'text':'string',
                'time with time zone':'string',
                'time without time zone':'string',
                'timestamp with time zone':'string',
                'timestamp without time zone':'string',
                '"char"':'string',
                'money':'double',
                'real':'double',
                'numeric':'double',
                'float':'double',
                'double precision':'double',
                'bigint':'long',
                'smallint':'long',
                'bit':'long'
            }
            type_without_size = [] 
            type_without_size = type.split("(")
            try:
                if(len(type_without_size)>=2):
                    type_without_size[1] = "(" + type_without_size[1]
                    blazing_type = types[type_without_size[0].lower()]
                    blazing_type = blazing_type + type_without_size[1]
                else:
                    blazing_type = types[type.lower()]

            except Exception as e:
                        print "The column datatype cannot be converted to a BlazingDB supported datatype"
            # Make the describe table line
            columns_desc.append(column + ' ' + blazing_type)
        # Join columns array by table
        columns = ', '.join(columns_desc)
        return columns
    
    def load_data(self, file, table):
        """ Load Data """
        with open(file, "r") as infile:
            data = infile.read()
            lines = data.splitlines()
            for line_number in range(len(lines)):
                if(line_number>1):
                    query = "load data stream '" + lines[line_number] + "' into table " + table + " fields terminated by '|' enclosed by '\"' lines terminated by '\\n'"
                    print query
                    # Load in Thread
                    thread = threading.Thread(target=self.small_load_datastream, args=(query,))
                    thread.start()
                    thread.join()

    def file_import(self, **kwargs):
        """ File Importer To BlazingDB """
        files_path = kwargs.get('files_path', '/home/second/datasets/');
        columns = kwargs.get('columns', '');
        table = kwargs.get('table', '');
        find_files_in_path = kwargs.get('find_files', True);
        file_ext = kwargs.get('files_extension', '.dat');

        if(find_files_in_path==True):
            # Find Files in Path
            os.chdir(files_path)
            for file in glob.glob("*"+file_ext):
                print(file)
                print(os.path.join(files_path, file))

                # Get Table
                if(table==''):
                    table = file.replace(file_ext,"")
                    print table
                
                columns = self.get_columns(file)
                print columns

                # Create table
                query = 'create table ' + table + ' (' + columns + ')'
                print query
                try:
                    print "blazing create table"
                    #self.connection.run(query,self.id_connection)
                except Exception as e:
                    print e
                
                # Load Data into the table
                self.load_data(file, table)
                
        else:
            # Check if the file exist
            if(os.path.isfile(files_path)):
                print("File not found")
            else:
                print(file)
                print "An only file"
                if(table==''):
                    table = file.replace(file_ext,"")
                    print table

                columns = self.get_columns(file)
                print columns

                # Create table
                query = 'create table ' + table + ' (' + columns + ')'
                print query
                try:
                    print "blazing load"
                    #self.connection.run(query,self.id_connection)
                except Exception as e:
                    print e
                
                # Load Data into the table
                self.load_data(file, table)

class BlazingETL:

    """ Migration Tool """

    def __init__(self, from_connection_obj, to_connection_obj):
        self.from_conn = from_connection_obj
        self.to_conn = to_connection_obj

    def write_chunk_complete(self, cursor, path, table, file_ext):
        to_open = path+table+file_ext
        print to_open
        file = open(to_open, 'w')
        try:
            for row in cursor.fetchall():
                file.write('|'.join(str(r) for r in row)+'\n')
        except Exception as e:
            print e
        file.close()

    def write_chunk_part(self, cursor, path, table, file_ext, chunk_size, iterator):
        to_open = path+table+'_'+str(iterator)+file_ext
        print to_open
        file = open(to_open, 'w')
        try:
            for row in cursor.fetchmany(chunk_size):
                #print row
                file.write('|'.join(str(r) for r in row)+'\n')
        except Exception as e:
            print e
        file.close()

    def copy_chunks(self, from_path, file, to_path):
        print "copy chunks"
        try:
            shutil.copyfile(from_path + file, to_path + file)
        except shutil.Error as e:
            print('Error: %s' % e)
        except IOError as e:
            print('Error: %s' % e.strerror)
        except Exception as e:
            print 'Error' + str(e)

    def load_datastream(self, cursor, table, destination, connection_id, iterations, chunk_size, large_file):
        print "load data stream"
        #log = "log.txt"
        #file = open(log, 'w')
        #file.write("************* load data stream starts ************\n")
        rows = []
        if(large_file==False):
            try:
                for row in cursor.fetchall():
                    #print row
                    rows.append('|'.join(str(r) for r in row))
                to_send = '\n'.join(rows)
                query = "load data stream '" + to_send + "' into table " + table + " fields terminated by '|' enclosed by '\"' lines terminated by '\n'"
                result = destination.run(query, connection_id)
                print result.status
                print result.rows
            except Exception as e:
                print('Error: %s' % e)
        if(large_file==True):
            #file.write("******* Large File True, Iterations "+str(int(iterations))+", Chunk Size "+str(chunk_size)+" *********\n")
            for lap in range(int(iterations)):
                #file.write("\n******* Iteration N° "+str(lap)+" *********\n")
            
                try:
                    for row in cursor.fetchmany(chunk_size):
                        rows.append('|'.join(str(r) for r in row))
                    to_send = '\n'.join(rows)
                    query = "load data stream '" + str(to_send) + "' into table " + str(table) + " fields terminated by '|' enclosed by '\"' lines terminated by '\n'"
                    file.write(query)
                    result = destination.run(query, connection_id)
                    #file.write("*** Result Status *** "+str(result.status))
                    #file.write("*** Result Rows *** "+str(result.rows))
                    print result.status
                    print result.rows
                except Exception as e:
                    #file.write("*** Error *** %s" % e)
                    print('Error: %s' % e)
            

    def migrate(self, **kwargs):
        """ Supported Migration from Redshift and Postgresql to BlazingDB """

        create_tables = kwargs.get('create_tables', True);
        files_path = kwargs.get('files_local_path', '/home/second/datasets/');
        blazing_path = kwargs.get('blazing_files_destination_path', '/opt/blazing/disk1/blazing/blazing-uploads/2/');
        chunk_size = kwargs.get('chunk_size', 100000);
        write_data_chunks = kwargs.get('export_data_from_origin', True);
        copy_data_to_destination = kwargs.get('copy_data_to_blazing', False);
        load_data_into_blazing = kwargs.get('load_data_into_blazing', True);
        file_extension = kwargs.get('file_extension', '.dat');
        by_stream = kwargs.get('by_stream', True);

        bl_con = self.to_conn.connect()

        query = "select distinct mytables.table_name from INFORMATION_SCHEMA.COLUMNS as i_columns left join information_schema.tables mytables on i_columns.table_name = mytables.table_name where mytables.table_schema = 'public' and mytables.table_type = 'BASE TABLE';"
        cursor = self.from_conn.cursor()
        result = cursor.execute(query)
        status = cursor.statusmessage
        try:
            tables = []
            for row in cursor.fetchall():
                tables.append(row[0]) # tables name
        except:
            print "No results returned"

        # Get table names
        tables_names = set(tables)

        # Loop by tables
        for table in tables_names:

            query = "select column_name, data_type, character_maximum_length from INFORMATION_SCHEMA.COLUMNS as i_columns left join information_schema.tables mytables on i_columns.table_name = mytables.table_name where mytables.table_schema = 'public' and mytables.table_type = 'BASE TABLE' and mytables.table_name = '" + table + "';"
            cursor = self.from_conn.cursor()
            result = cursor.execute(query)
            status = cursor.statusmessage

            try:
                columns = []
                for col in cursor.fetchall():

                    # Convert DataTypes and Save String
                    blazing_type = 'datatype'
                    types = {
                        'integer':'long',
                        'character varying':'string('+str(col[2])+')',
                        'character':'string('+str(col[2])+')',
                        'text':'string('+str(col[2])+')',
                        'time with time zone':'string('+str(col[2])+')',
                        'time without time zone':'string('+str(col[2])+')',
                        'timestamp with time zone':'string('+str(col[2])+')',
                        'timestamp without time zone':'string('+str(col[2])+')',
                        '"char"':'string('+str(col[2])+')',
                        'money':'double',
                        'real':'double',
                        'numeric':'double',
                        'double precision':'double',
                        'bigint':'long',
                        'smallint':'long',
                        'bit':'long',
                        'date':'date'
                    }
                    blazing_type = types[col[1]]

                    # Make the describe table line
                    columns.append(col[0] + ' ' + blazing_type)

                # join columns array by table
                columns_desc = ', '.join(columns)

                # Create Tables on Blazing
                if(create_tables==True):
                    query = "create table " + table + " (" + columns_desc + ")"
                    result = self.to_conn.run(query,bl_con)
                    print result.status
                    print result.rows

                # Get data in chunks by table ans save in files
                # Get table content
                query = "select * from "+table
                cursor = self.from_conn.cursor()
                result = cursor.execute(query)
                num_rows = cursor.statusmessage[7:]
                iterations = 0
                                
                if(int(num_rows) <= int(chunk_size)):

                    """ MultiThread """
                    if(by_stream==True):
                        # Load data into Blazing
                        thread = threading.Thread(target=self.load_datastream, args=(cursor, table, self.to_conn, bl_con, iterations, chunk_size, False))
                        thread.start()
                        thread.join()

                    if(by_stream==False):

                        if(write_data_chunks==True):
                            thread = threading.Thread(target=self.write_chunk_complete, args=(cursor, files_path, table, file_extension))
                            thread.start()
                            thread.join()

                        if(copy_data_to_destination==True):
                            thread2 = threading.Thread(target=self.copy_chunks, args=(files_path, table + file_extension, blazing_path))
                            thread2.start()
                            thread2.join()

                        # Load Data Infile Blazing
                        if(load_data_into_blazing==True):
                            if(copy_data_to_destination==True):
                                result = self.to_conn.run("load data infile " + table + file_extension + " into table " + table + " fields terminated by '|' enclosed by '\"' lines terminated by '\n'",bl_con)
                            else:
                                result = self.to_conn.run("load data infile '" + files_path + table + file_extension + "' into table " + table + " fields terminated by '|' enclosed by '\"' lines terminated by '\n'",bl_con)
                            print result.status

                else:
                    # Chunks Division
                    iterations = math.ceil(int(num_rows) / chunk_size)

                    """ MultiThread """
                    if(by_stream==True):
                        # Load data into Blazing
                        thread = threading.Thread(target=self.load_datastream, args=(cursor, table, self.to_conn, bl_con, iterations, chunk_size, True))
                        thread.start()
                        thread.join()

                    for i in range(int(iterations)):

                        if(by_stream==False):
                            
                            if(write_data_chunks==True):
                                thread = threading.Thread(target=self.write_chunk_part, args=(cursor, files_path, table, file_extension, chunk_size, i))
                                thread.start()
                                thread.join()

                            if(copy_data_to_destination==True):
                                thread2 = threading.Thread(target=self.copy_chunks, args=(files_path, table+'_'+str(i)+file_extension, blazing_path))
                                thread2.start()
                                thread2.join()

                            # Load Data Infile Blazing
                            if(load_data_into_blazing==True):
                                if(copy_data_to_destination==True):
                                    result = self.to_conn.run("load data infile " + table+"_"+str(i)+file_extension + " into table " + table + " fields terminated by '|' enclosed by '\"' lines terminated by '\n'",bl_con)
                                else:
                                    result = self.to_conn.run("load data infile '" + files_path + table +"_"+str(i)+ file_extension + "' into table " + table + " fields terminated by '|' enclosed by '\"' lines terminated by '\n'",bl_con)
                                print result.status

            # Print Exception
            except Exception as e:
                print e

        # Close ** From DB ** Connection
        self.from_conn.close()

class BlazingResult(object):
    def __init__(self, j):
        self.__dict__ = json.loads(j)

    def results_clean(self,j):
        self.__dict__ = json.loads(j)

class BlazingPyConnector:

    def __init__(self, host, username, password, database, **kwargs):
        self.host = host
        self.port = kwargs.get('port', '8089')
        self.username = username
        self.password = password
        self.database = database
        self.protocol = 'https' if (kwargs.get('https', True) == True) else 'http'
        self.context = kwargs.get('context', '/')
        self.baseurl = self.protocol+'://'+self.host+':'+self.port+self.context
        print "Base URL: " + self.baseurl

    def connect(self):
        connection = False
        try:
            r = requests.post(self.baseurl+'/blazing-jdbc/register', data={'username':self.username, 'password':self.password, 'database':self.database}, verify=False)
            connection = r.content
            if(connection != 'fail'):
                try:
                    r = requests.post(self.baseurl+'/blazing-jdbc/query', data={'username':self.username, 'token':connection, 'query':'use database '+self.database}, verify=False)
                except:
                    print "The database does not exist"
                    raise
            else:
                print "Your username or password is incorrect"
        except:
            print "The host you entered is unreachable or your credentials are incorrect"
            raise

        return connection

    def run(self, query, connection):
        if(connection != False and connection != 'fail'):
            r = requests.post(self.baseurl+'/blazing-jdbc/query', data={'username':self.username, 'token':connection, 'query':query}, verify=False)
            result_key = r.content
            r = requests.post(self.baseurl+'/blazing-jdbc/get-results', data={'username':self.username, 'token':connection, 'resultSetToken':result_key}, verify=False)
            print r.content
            result = BlazingResult(r.content)
        else:
            result = BlazingResult('{"status":"fail","rows":"Username or Password incorrect"}')

        return result