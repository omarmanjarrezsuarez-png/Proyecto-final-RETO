import os
import sys
import mysql.connector
from mysql.connector import errorcode

SQL_FILE_PATH = os.environ.get("SQL_FILE", "./retos_habitos.sql")

# Lee variables de entorno (útil en Railway)
DB_HOST = "mysql.railway.internal"
DB_PORT = 3306
DB_USER = "root"
DB_PASSWORD = "mQXcacDjYZKSpEvqxzOoNSILXSnGsvXY"

def read_sql_file(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Archivo SQL no encontrado: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def run_sql_script(connection, sql_text):
    """
    Ejecuta un script SQL que contiene múltiples sentencias.
    Usa cursor.execute(..., multi=True) y hace commit al final.
    """
    cursor = connection.cursor()
    try:
        print("Ejecutando script SQL con multi=True...")
        # mysql-connector permite ejecutar múltiples sentencias con multi=True
        for result in cursor.execute(sql_text, multi=True):
            # result es un MySQLCursor / iterator de resultados de cada sentencia
            # Podemos imprimir info mínima de cada sentencia
            if result.with_rows:
                # Solo contamos filas si la sentencia devuelve filas (e.g. SELECT)
                rows = result.fetchall()
                print(f"-> Sentencia: {result.statement[:60]!r} ... devuelto {len(rows)} filas")
            else:
                print(f"-> Sentencia ejecutada: {result.statement[:60]!r}  (OK)")

        connection.commit()
        print("Commit realizado. Migración completada con éxito 💙")

    except mysql.connector.Error as err:
        print("Error durante la ejecución del script SQL:", err)
        connection.rollback()
        print("Rolled back.")
        raise
    finally:
        cursor.close()

def main():
    try:
        sql_text = read_sql_file(SQL_FILE_PATH)
    except Exception as e:
        print("No se pudo leer el archivo SQL:", e)
        sys.exit(1)

    print(f"Conectando a MySQL en {DB_HOST}:{DB_PORT} como {DB_USER} ...")
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            autocommit=False,  # manejamos commit manualmente
            connection_timeout=30,
        )
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Credenciales inválidas — revisa DB_USER/DB_PASSWORD.")
        elif err.errno == errorcode.ER_BAD_HOST_ERROR:
            print("No se pudo conectar al host de la base de datos.")
        else:
            print("Error al conectar a MySQL:", err)
        sys.exit(1)

    try:
        run_sql_script(conn, sql_text)
    except Exception as e:
        print("Migración fallida:", e)
        sys.exit(1)
    finally:
        if conn.is_connected():
            conn.close()
            print("Conexión cerrada.")

if __name__ == "__main__":
    main()
