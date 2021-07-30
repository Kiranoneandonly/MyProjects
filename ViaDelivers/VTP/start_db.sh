#!/bin/bash
PROCESS_NUM=$(ps -ef | grep "postgres -D" | grep -v "grep" | wc -l)
if [[ $PROCESS_NUM -ge 1 ]];
    then
        echo "db is running"
    else
        pg_ctl -D /usr/local/var/postgres -l /usr/local/var/postgres/server.log start
    fi


