#!/bin/bash
sqlite3 ~/alfredo-core/alfredo_memory.db "ALTER TABLE routines ADD COLUMN days_of_week VARCHAR DEFAULT '0,1,2,3,4,5,6';"
