#!/bin/bash

# Run as the root user on the old clarity server before upgrade

yum --enablerepo=* install ClarityLIMS-UpgradePreValidation
bash /opt/gls/ClarityUpgradeValidation/bin/validate.sh
yum remove ClarityLIMS-UpgradePreValidation


/opt/gls/clarity/bin/run_clarity.sh stop

pg_dump -U <database_user> -b -O -Ft clarityDB -f ~glsjboss/backups/database/clarity-old_version-`date +%Y%m%d%H%M`.tar

cd /
rpm -qa | grep "BaseSpace\|Clarity" > clarityrpms.txt
tar cfJ /opt/backups.tar.xz \
    /opt/gls/clarity/users/glsftp \
    /opt/gls/clarity/customextensions \
    /opt/gls/clarity/glscontents \
    /etc/httpd/conf.d \
    /etc/httpd/sslcertificate \
    /var/lib/pgsql/9.6/data/pg_hba.conf \
    /var/lib/pgsql/9.6/data/postgresql.conf \
    clarityrpms.txt \
    DATABASE_FILE_TODELOO
