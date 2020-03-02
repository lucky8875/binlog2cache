# binlog2cache

监听Mysql binlog日志并实时将变更同步至缓存(redis)

> 为什么需要binlog2cache

存储在yysql中并且在redis中缓存的数据是易变的，这回引起脏数据。因此应该实时将数据库中最新的数据通过`binlog2cache`同步至redis缓存

## 使用方式

1. clone项目并安装依赖

```shell script
git clone https://github.com/jiangyx3915/binlog2cache.git
pip install -r requirements.txt
```

2. 修改config.py文件中的连接配置
3. 运行文件开始同步

```shell script
python binlog2cache.py
```

4. 查看redis修改

```shell script
redis-cli monitor
```

## 案例描述

MySQL Data

```text
+-------+-------------+------+-----+---------+----------------+
| Field | Type        | Null | Key | Default | Extra          |
+-------+-------------+------+-----+---------+----------------+
| id    | int(11)     | NO   | PRI | NULL    | auto_increment |
| name  | varchar(255)| YES  |     | NULL    |                |
| age   | int(11)     | YES  |     | NULL    |                |
+-------+-------------+------+-----+---------+----------------+
```

Redis Cache Data

```text
以hash结构进行存储
生成的键为 db:table:id 定位一行数据

db:table:id
    id:   xxx
    name: xxx
    age:  xxx    
```

## 注意事项

使用 `binlog2cache` 必须开启MySQL中的 `binlog` 并且设置 `binlog-format`，配置如下

```text
[mysqld]
server-id = 1
log_bin = /var/log/mysql/mysql-bin.log
expire_logs_days = 10
max_binlog_size = 1000M
binlog-format = row
```

> max_binlog_size：bin log日志每达到设定大小后，会使用新的bin log日志。如mysql-bin.000002达到500M后，创建并使用mysql-bin.000003文件作为日志记录。
> expire_logs_days：保留指定日期范围内的bin log历史日志，超出时间则会清除