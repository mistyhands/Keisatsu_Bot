from typing import List, Tuple
import psycopg2 as psql

class Data():
    def __init__(self):
        self.connection = psql.connect("dbname=vcj user=misty")
        self.cursor = self.connection.cursor()
        self.connection.autocommit = True

    def exists_sunboard(self, message_id: int) -> bool:
        self.cursor.execute("SELECT message_id FROM sunboard WHERE message_id = %s", (message_id))
        result = self.cursor.fetchall()
        return (message_id,) in result

    def insert_sunboard(self, message_id: int) -> bool:
        try:
            self.cursor.execute("INSERT INTO sunboard(message_id) VALUES(%s)", (message_id))
        except psql.IntegrityError:
            return False
        return True

    
    def is_reddit_post_posted(self, post_id: str) -> bool:
        self.cursor.execute("SELECT post_id FROM reddit WHERE post_id = %s", (post_id))
        result = self.cursor.fetchall()
        return (post_id,) in result

    def insert_reddit_post(self, post_id: str, message_id: int) -> bool:
        try:
            self.cursor.execute("INSERT INTO reddit(post_id, message_id) VALUES(%s, %s)", (post_id, message_id))
        except psql.IntegrityError:
            return False
        return True

    def get_recently_posted(self) -> List[Tuple[str, int]]:
        self.cursor.execute("SELECT post_id, message_id FROM reddit")
        return self.cursor.fetchmany(25)
