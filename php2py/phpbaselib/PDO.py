from typing import Optional, Any

from php2py.engine.exceptions import PDOException
from php2py.phpbaselib.phptypes import PhpArray


class PDO():
    # TODO: Check what integers are actually used
    FETCH_BOTH = 1
    FETCH_OBJ = 2
    ATTR_DEFAULT_FETCH_MODE = "fetch_mode"

    ERRMODE_WARNING = 1
    ERRMODE_EXCEPTION = 2
    ATTR_ERRMODE = "error_mode"

    def __init__(self,
                 dsn: str,
                 username: Optional[str] = None,
                 password: Optional[str] = None,
                 options: Optional[PhpArray] = None) -> None:

        self.dsn = dsn
        self.username = username
        self.password = password
        self.options = {
            "fetch_mode": self.FETCH_BOTH,
            "error_mode": self.ERRMODE_WARNING,
        }
        if options is not None:
            for k, v in options.items():
                self.options[k] = v

        connection_type, connection_options = dsn.split(":", maxsplit=1)
        if connection_type == "mysql":
            self.connection = MysqlConnection(self, connection_options)
        else:
            raise PDOException("{} databases aren't supported yet".format(connection_type))

    def prepare(self, sql: str) -> "Query":
        return Query(self, self.connection, sql)

    def beginTransaction(self) -> bool:
        return self.connection.begin_transaction()

    def commit(self) -> bool:
        return self.connection.commit()

    def inTransaction(self) -> bool:
        return self.connection.in_transaction()

    def errorCode(self) -> str:
        if self.connection is None:
            return None
        else:
            return self.connection.error_code()

    def errorInfo(self) -> PhpArray:
        if self.connection is None:
            return None
        return self.connection.error_info()

    def exec(self, sql: str) -> int:
        return self.connection.exec(sql)

    def getAttribute(self, attrib: str) -> Any:
        # TODO: Should probably copy the ints that php uses
        try:
            return self.options[attrib]
        except:
            return None

    @staticmethod
    def getAvailableDrivers():
        """ Should see what databases have been installed

        """
        return PhpArray("mysql")


class Query():
    def __init__(self, pdo: PDO, connection: "DBConnection", sql: str) -> None:
        self.pdo = pdo
        self.connection = connection
        self.sql = sql

    def execute(self):
        self.cursor = self.connection.execute(self.sql)

    def fetchall(self):
        pass

    def fetch(self):
        return next(iter(self.cursor))


class Cursor():
    def __init__(self, connection: PDO) -> None:
        self.data = []

    def __iter__(self):
        return iter(self.data)


class DBConnection:
    def __init__(self, pdo: PDO, connection_options: str) -> None:
        raise NotImplementedError()

    def execute(self, sql: str) -> Cursor:
        raise NotImplementedError()

    def begin_transaction(self) -> bool:
        """ Return True if transactions are supported and was successfully started

        """
        raise PDOException("Database driver doesn't support transactions")

    def commit(self) -> bool:
        """ Commits a database transaction.

        Returns True if successful and false otherwise

        """
        raise PDOException("Database driver doesn't support transactions")

    def in_transaction(self) -> bool:
        """ True if within a db transaction, false otherwise

        """
        raise PDOException("Database driver doesn't support transactions")

    def error_code(self) -> str:
        raise NotImplementedError("Error codes (sql status) aren't implemented yet")

    def error_info(self) -> str:
        return PhpArray(self.error_code, self.driver_error_code(), self.driver_error_message())

    def driver_error_code(self) -> str:
        return "No driver error codes"

    def driver_error_message(self) -> str:
        return "No driver error messages"

    def exec(self, sql: str) -> int:
        """ Execute the sql sql and return the number of rows effected

        """
        raise NotImplementedError("Who knows how to execute this query? Not me!")


class MysqlConnection(DBConnection):
    def __init__(self, pdo: PDO, connection_options: str) -> None:
        self.connection_options = connection_options

    def begin_transaction(self) -> bool:
        raise NotImplementedError("Transactions aren't implemented yet")

    def commit(self) -> bool:
        raise NotImplementedError("Transactions aren't implemented yet")

    def in_transaction(self) -> bool:
        raise NotImplementedError("Transactions aren't implemented yet")
