import sys
import yaml
import redis
from pymysqlreplication import BinLogStreamReader
from pymysqlreplication.row_event import (
    DeleteRowsEvent,
    UpdateRowsEvent,
    WriteRowsEvent
)


def load_config(conf_path):
    with open(conf_path, 'r') as fp:
        try:
            return yaml.load(fp)
        except:
            return None


class SyncCache:

    def __init__(self, config):
        self.config = config
        if not config:
            raise Exception('can not load config')
        self.config = config

        # reduce var path length
        self.MYSQL_SETTINGS = config['MYSQL_SETTINGS']
        self.REDIS_SETTINGS = config['REDIS_SETTINGS']
        self.SELF = config['SELF']

        # init redis client
        self.redis_client = redis.StrictRedis(
            host=self.REDIS_SETTINGS['host'],
            port=self.REDIS_SETTINGS['port'],
            db=self.REDIS_SETTINGS['db'],
            password=self.REDIS_SETTINGS['password'],
            decode_responses=True
        )

    def transfer(self):
        """
        sync mysql binlog data to redis
        :return:
        """
        log_file, log_pos = self._get_log_pos()
        log_pos = int(log_pos) if log_pos else log_pos
        stream = BinLogStreamReader(
            connection_settings=self.MYSQL_SETTINGS,
            server_id=int(self.SELF['server_id']),
            only_events=[DeleteRowsEvent, WriteRowsEvent, UpdateRowsEvent],
            resume_stream=True,
            log_file=log_file,
            log_pos=log_pos,
            blocking=True
        )
        for binlog_event in stream:
            prefix = f'{binlog_event.schema}:{binlog_event.table}:'
            self._set_log_pos(stream.log_file, stream.log_pos)
            for row in binlog_event.rows:
                if isinstance(binlog_event, DeleteRowsEvent):
                    self._delete_handler(prefix=prefix, row=row)
                if isinstance(binlog_event, UpdateRowsEvent):
                    self._update_handler(prefix=prefix, row=row)
                if isinstance(binlog_event, WriteRowsEvent):
                    self._write_handler(prefix=prefix, row=row)

        stream.close()

    def _delete_handler(self, prefix, row):
        """
        process delete event
        :param prefix:      schema:table
        :param row:         row data
        :return:
        """
        print(f'process delete event，data {row}')
        val = row["values"]
        self.redis_client.delete(f'{prefix}{val["id"]}')

    def _update_handler(self, prefix, row):
        """
        process update event
        :param prefix:      schema:table
        :param row:         row data
        :return:
        """
        print(f'process update event，data {row}')
        val = row['after_values']
        self.redis_client.hmset(f"{prefix}{val['id']}", val)

    def _write_handler(self, prefix, row):
        """
        process add event
        :param prefix:      schema:table
        :param row:         row data
        :return:
        """
        print(f'process add event，data {row}')
        val = row["values"]
        self.redis_client.hmset(f"{prefix}{val['id']}", val)

    def _set_log_pos(self, log_file, log_pos):
        """
        set synced binlog position to redis
        :param log_file:  binlog filename
        :param log_pos:   last sync binlog position
        :return:
        """
        key = f"{self.SELF['log_pos_prefix']}{self.SELF['server_id']}"
        self.redis_client.hmset(key, {'log_pos': log_pos, 'log_file': log_file})

    def _get_log_pos(self):
        """
        get mysql binlog position from redis
        :return:
        """
        key = f"{self.SELF['log_pos_prefix']}{self.SELF['server_id']}"
        ret = self.redis_client.hgetall(key)
        return ret.get('log_file'), ret.get('log_pos')


def main():
    if len(sys.argv) == 1:
        print('You should passed config path')
        exit()
    conf_path = sys.argv[1]
    conf = load_config(conf_path)
    sync_ins = SyncCache(conf)
    print('=' * 16, 'start sync', '=' * 16)
    sync_ins.transfer()


if __name__ == '__main__':
    main()
