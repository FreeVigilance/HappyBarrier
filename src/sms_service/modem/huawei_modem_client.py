import logging
import sqlite3
from typing import List

from huawei_lte_api.Client import Client
from huawei_lte_api.Connection import Connection
from huawei_lte_api.enums.client import ResponseEnum
from huawei_lte_api.enums.sms import BoxTypeEnum

logger = logging.getLogger(__name__)


class HuaweiModemClient:
    def __init__(self, url: str, db_path: str = "sms_storage.sqlite3", username: str = None, password: str = None):
        self.url = url
        self.username = username
        self.password = password
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the local SQLite database to store sent messages."""

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sms_messages (
                id INTEGER PRIMARY KEY,
                phone TEXT,
                content TEXT,
                date_time REAL,
                modem_index INTEGER UNIQUE,
                message_type TEXT CHECK( message_type IN ('incoming','outgoing') ) NOT NULL
            )
        """
        )
        conn.commit()
        conn.close()
        logger.debug("SQLite database initialized.")

    def send_sms(self, phone_number: str, message: str) -> bool:
        """Send an SMS to a phone number."""

        logger.debug("Sending SMS to %s: '%s'", phone_number, message)

        with Connection(self.url, username=self.username, password=self.password) as connection:
            client = Client(connection)
            result = client.sms.send_sms([phone_number], message)
            success = result == ResponseEnum.OK.value
            if success:
                logger.debug("SMS successfully sent to %s", phone_number)
            else:
                logger.error("Failed to send SMS to %s", phone_number)
            return success

    def _save_messages(self, messages: List[dict]):
        """Internal method to save messages to the database."""

        from datetime import datetime

        logger.debug("Saving %d messages to the database...", len(messages))
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for msg in messages:
            try:
                timestamp = datetime.strptime(msg["Date"], "%Y-%m-%d %H:%M:%S").timestamp()
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO sms_messages (phone, content, date_time, modem_index, message_type)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (msg["Phone"], msg["Content"], timestamp, msg["Index"], msg["message_type"]),
                )
                logger.debug("Saved message from phone %s", msg["Phone"])
            except sqlite3.IntegrityError as e:
                logger.error("Error while saving message: '%s'. %s", msg, e.sqlite_errorname)
                continue

        conn.commit()
        conn.close()
        logger.debug("All messages saved to the database.")

    def _read_sms(self) -> List[dict]:
        """Read incoming and outgoing SMS messages and store them."""

        logger.debug("Reading incoming and outgoing SMS messages from modem...")
        new_messages = []

        with Connection(self.url, username=self.username, password=self.password) as connection:
            client = Client(connection)

            for msg in client.sms.get_messages(box_type=BoxTypeEnum.LOCAL_INBOX):
                logger.debug("Read incoming SMS from %s", msg.phone)
                new_messages.append({**msg.to_dict(), "message_type": "incoming"})

            for msg in client.sms.get_messages(box_type=BoxTypeEnum.LOCAL_SENT):
                logger.debug("Read outgoing SMS to %s", msg.phone)
                new_messages.append({**msg.to_dict(), "message_type": "outgoing"})

        self._save_messages(new_messages)
        logger.debug("Finished reading and saving %d new SMS messages.", len(new_messages))
        return new_messages

    def get_all_stored_sms(self) -> List[dict]:
        """Get all stored SMS from the local database."""

        logger.debug("Fetching all stored SMS messages from the database...")
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT phone, content, date_time, message_type FROM sms_messages")
        rows = cursor.fetchall()
        conn.close()

        logger.debug("Fetched %d SMS messages.", len(rows))
        return [{"phone": row[0], "content": row[1], "date_time": row[2], "message_type": row[3]} for row in rows]

    def get_reply_from_phone_since(self, phone: str, since_timestamp: float) -> str | None:
        """Returns the first incoming message from a given phone number that was received after the given timestamp."""

        self._read_sms()  # Sync modem messages to local DB

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT content FROM sms_messages
            WHERE phone = ?
              AND message_type = 'incoming'
              AND date_time >= ?
            ORDER BY date_time ASC
            LIMIT 1
        """,
            (phone, since_timestamp),
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            logger.info("Found reply from %s: %s", phone, row[0])
            return row[0]

        return None
