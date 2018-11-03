#!/usr/bin/env python3

import argparse
import configparser
import copy
import os
import pymysql

mysql_internal = ['information_schema', 'mysql']

# Not used, but could be in the future.
stat_hdrs = ['Name', 'Engine', 'Version', 'Row_format', 'Rows', 'Avg_row_length', 'Data_length',
             'Max_data_length', 'Index_length', 'Data_free', 'Auto_increment', 'Create_time',
             'Update_time', 'Check_time', 'Collation', 'Checksum', 'Create_options', 'Comment']
tblinfo_hdrs = ['Field', 'Type', 'Null', 'Key', 'Default', 'Extra']

def get_info(db, internal = False):
    dbs = {}
    if os.path.isfile(os.path.expanduser('~/.my.cnf')):
        _cfg = configparser.ConfigParser(allow_no_value = True)
        _cfg.read(os.path.expanduser('~/.my.cnf'))
        _cfg = dict(_cfg['client'])
        _cfg['ssl'] = {}
        if 'host' not in _cfg:
            _cfg['host'] = 'localhost'
        conn = pymysql.connect(**_cfg, cursorclass = pymysql.cursors.DictCursor)
    else:
        raise RuntimeError('Need mysql creds at ~/.my.cnf')
    cur = conn.cursor()
    if not db:
        cur.execute("SHOW DATABASES")
        db = [row['Database'] for row in cur.fetchall()]
        if not internal:
            for d in mysql_internal:
                try:
                    db.remove(d)
                except ValueError:  # Not in the list; our user probably doesn't have access
                    pass
    else:
        db = [db]
    for d in db:
        dbs[d] = {}
        cur.execute("SHOW TABLES FROM `{0}`".format(d))
        for tbl in [t['Tables_in_{0}'.format(d)] for t in cur.fetchall()]:
            dbs[d][tbl] = {}
            # Status
            cur.execute("SHOW TABLE STATUS FROM `{0}` WHERE Name = %s".format(d), (tbl, ))
            dbs[d][tbl]['_STATUS'] = copy.deepcopy(cur.fetchone())
            # Columns
            dbs[d][tbl]['_COLUMNS'] = {}
            #cur.execute("DESCRIBE {0}.{1}".format(d, tbl))
            cur.execute("SHOW COLUMNS IN `{0}` FROM `{1}`".format(tbl, d))
            for row in cur.fetchall():
                colNm = row['Field']
                dbs[d][tbl]['_COLUMNS'][colNm] = {}
                for k in [x for x in tblinfo_hdrs if x is not 'Field']:
                    dbs[d][tbl]['_COLUMNS'][colNm][k] = row[k]
    cur.close()
    conn.close()
    return(dbs)

def parseArgs():
    args = argparse.ArgumentParser()
    args.add_argument('-i', '--internal',
                      dest = 'internal',
                      action = 'store_true',
                      help = ('If specified, include the MySQL internal databases '
                              '(mysql, information_schema, etc.); only used if -d is not specified'))
    args.add_argument('-d', '--database',
                      dest = 'db',
                      default = None,
                      help = 'If specified, only list table info for this DB')
    return(args)

def main():
    args = vars(parseArgs().parse_args())
    dbs = get_info(args['db'], internal = args['internal'])
    #import json
    #print(json.dumps(dbs, indent = 4, sort_keys = True, default = str))
    import pprint
    pprint.pprint(dbs)

if __name__ == '__main__':
    main()
